import uuid
import re
import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.database.models import Document, DocumentPage, TextBlock, ExtractedFact, ActionCard, ProcessingJob
from backend.modules.storage.service import storage_service
from backend.modules.uploads.security import validate_upload_bytes
from backend.modules.image_quality.service import assess_image_quality
from backend.modules.pdf.service import extract_pdf_data, render_pdf_page_to_png
from backend.modules.ocr.service import segment_text_into_blocks, extract_text_blocks_from_image, ExtractedBlock
from backend.modules.extraction.fact_service import extract_facts_from_blocks
from backend.modules.answers.service import generate_action_cards_for_document

logger = logging.getLogger("noticesaathi.pipeline")

def create_document_record(
    db: Session,
    owner_id: str,
    file_bytes: bytes,
    original_filename: str,
    declared_media_type: str = "application/pdf"
) -> Document:
    # 1. Upload security checks (Magic bytes, extension, size, checksum, safe key)
    validated = validate_upload_bytes(file_bytes, original_filename, declared_media_type)

    # 2. Store original privately
    storage_key = validated["storage_key"]
    storage_service.save_original(storage_key, file_bytes)

    # 3. Create database entry in UPLOADED state
    doc = Document(
        owner_id=owner_id,
        storage_key=storage_key,
        checksum=validated["checksum"],
        original_filename=original_filename,
        media_type=validated["verified_media_type"],
        state="UPLOADED",
        page_count=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Create background job record
    job = ProcessingJob(
        document_id=doc.document_id,
        job_type="DOCUMENT_INGEST",
        state="QUEUED"
    )
    db.add(job)
    db.commit()

    return doc

def process_document_pipeline(db: Session, document_id: str) -> Document:
    """
    Executes the multi-stage document processing pipeline with real OCR:
    1. Check document state (prevents stale jobs from resurrecting deleted docs)
    2. Read original bytes
    3. Extract real text blocks (Native PDF or Real OCR for images/scans)
    4. Assess Image Quality (combining heuristics with OCR word readability)
    5. Extract structured facts
    6. Generate Action Cards with Proof
    7. Transition to READY or NEEDS_RECAPTURE
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prevent stale background workers from resurrecting a deleted document
    if doc.state in ["DELETED", "DELETION_REQUESTED"] or doc.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Cannot process document marked for deletion.")

    doc.state = "PROCESSING"
    db.commit()

    file_bytes = storage_service.read_original(doc.storage_key)

    # Check if image
    if doc.media_type in ["image/jpeg", "image/png"]:
        logger.info(f"Processing image document {doc.document_id} ({doc.original_filename})")
        # Run real OCR on image bytes
        real_ocr_blocks: List[ExtractedBlock] = extract_text_blocks_from_image(file_bytes, page_index=1)
        combined_text = " ".join(b.text_original for b in real_ocr_blocks)

        # Log raw extracted text for page 1
        logger.info(f"Page 1/1 OCR extraction complete: {len(real_ocr_blocks)} blocks extracted.")
        for idx, b in enumerate(real_ocr_blocks):
            logger.info(f"Page 1 Block [{idx+1}]: '{b.text_original}' (conf: {b.confidence}, bbox: {b.bbox})")

        # Audit captured content features
        has_tables = any(re.search(r'\d+[\d,]*\.\d{2}', b.text_original) for b in real_ocr_blocks)
        has_dates = any(re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}', b.text_original) for b in real_ocr_blocks)
        has_address = any(re.search(r'\b\d{6}\b|flat|plot|road|street|residency', b.text_original, re.I) for b in real_ocr_blocks)
        has_instructions = any(re.search(r'visit:|citizen app|payment|scan to pay', b.text_original, re.I) for b in real_ocr_blocks)
        has_small_print = any(re.search(r'assistance|helpline|0866|mon\s*-\s*sat', b.text_original, re.I) for b in real_ocr_blocks)
        logger.info(f"Page 1 Feature Audit: tables/amounts={has_tables}, dates={has_dates}, address={has_address}, instructions={has_instructions}, small_print={has_small_print}")

        # Assess image quality considering OCR text output
        quality = assess_image_quality(file_bytes, extracted_text_sample=combined_text)

        # Save Page record
        page = DocumentPage(
            document_id=doc.document_id,
            page_index=1,
            derived_image_key=doc.storage_key,
            width=quality.metrics.get("width", 800),
            height=quality.metrics.get("height", 1000),
            quality_state=quality.quality_state,
            quality_metrics=quality.metrics
        )
        db.add(page)
        db.commit()
        db.refresh(page)

        # If quality gate fails (and no readable words could be found), mark NEEDS_RECAPTURE
        if not quality.is_readable:
            doc.state = "NEEDS_RECAPTURE"
            doc.page_count = 1
            db.commit()
            return doc

        for b in real_ocr_blocks:
            tb = TextBlock(
                block_id=b.block_id,
                page_id=page.page_id,
                page_number=page.page_index,
                document_id=doc.document_id,
                text_original=b.text_original,
                text_normalized=b.text_normalized,
                bbox=b.bbox,
                confidence=b.confidence,
                extraction_version=b.engine
            )
            db.add(tb)
        db.commit()
        doc.page_count = 1

    elif doc.media_type == "application/pdf":
        extracted_pages = extract_pdf_data(file_bytes)
        doc.page_count = len(extracted_pages)

        for p in extracted_pages:
            p_text = p.text.strip()
            blocks_to_save: List[ExtractedBlock] = []

            if p_text:
                # 1. Native digital PDF text extraction
                blocks_to_save = segment_text_into_blocks(p_text, page_index=p.page_index)
                quality_state = "READABLE"
                quality_metrics = {"is_pdf_native": True, "char_count": len(p_text)}
            else:
                # 2. Scanned PDF page fallback: Render page to image and run real RapidOCR
                rendered_png = render_pdf_page_to_png(file_bytes, page_index=p.page_index, dpi=150)
                if rendered_png:
                    blocks_to_save = extract_text_blocks_from_image(rendered_png, page_index=p.page_index)
                    combined_scanned_text = " ".join(b.text_original for b in blocks_to_save)
                    q = assess_image_quality(rendered_png, extracted_text_sample=combined_scanned_text)
                    quality_state = q.quality_state
                    quality_metrics = q.metrics
                else:
                    quality_state = "EMPTY_PAGE"
                    quality_metrics = {"is_scanned": True, "error": "Could not render page image"}

            page = DocumentPage(
                document_id=doc.document_id,
                page_index=p.page_index,
                width=p.width,
                height=p.height,
                quality_state=quality_state,
                quality_metrics=quality_metrics
            )
            db.add(page)
            db.commit()
            db.refresh(page)

            logger.info(f"PDF Page {p.page_index}/{len(extracted_pages)}: {len(blocks_to_save)} blocks saved (state={quality_state})")
            for idx, b in enumerate(blocks_to_save):
                logger.debug(f"PDF Page {p.page_index} Block [{idx+1}]: '{b.text_original}'")

            for b in blocks_to_save:
                tb = TextBlock(
                    block_id=b.block_id,
                    page_id=page.page_id,
                    page_number=page.page_index,
                    document_id=doc.document_id,
                    text_original=b.text_original,
                    text_normalized=b.text_normalized,
                    bbox=b.bbox,
                    confidence=b.confidence,
                    extraction_version=b.engine
                )
                db.add(tb)
            db.commit()

    # Extract Structured Candidate Facts
    all_blocks = db.query(TextBlock).filter(TextBlock.document_id == doc.document_id).all()
    extracted_facts = extract_facts_from_blocks(all_blocks)
    for ef in extracted_facts:
        fact = ExtractedFact(
            document_id=doc.document_id,
            field_type=ef.field_type,
            raw_value=ef.raw_value,
            normalized_value=ef.normalized_value,
            status=ef.status,
            reason_code=ef.reason_code,
            evidence_refs=ef.evidence_refs
        )
        db.add(fact)
    db.commit()

    # Generate Action Cards with Proof
    cards = generate_action_cards_for_document(db, doc.document_id)
    for c in cards:
        db.add(c)
    db.commit()

    doc.state = "READY"
    db.commit()
    db.refresh(doc)
    return doc

def delete_document_cascade(db: Session, document_id: str) -> None:
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        return

    doc.state = "DELETION_REQUESTED"
    db.commit()

    # Collect page and audio keys
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
    page_keys = [p.derived_image_key for p in pages if p.derived_image_key]

    # Remove files from private storage
    storage_service.delete_document_assets(doc.storage_key, page_keys=page_keys)

    # Mark deleted in DB (or remove cascade)
    doc.deleted_at = datetime.now(timezone.utc)
    doc.state = "DELETED"

    # Delete child rows
    db.query(ActionCard).filter(ActionCard.document_id == document_id).delete()
    db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).delete()
    db.query(TextBlock).filter(TextBlock.document_id == document_id).delete()
    db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
    db.query(ProcessingJob).filter(ProcessingJob.document_id == document_id).delete()

    db.commit()
