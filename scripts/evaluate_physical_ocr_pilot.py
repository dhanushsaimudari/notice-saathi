#!/usr/bin/env python3
"""
NoticeSaathi — Physical Document OCR Pilot Evaluation Engine
Evaluates OCR, critical-field extraction, and quality gate abstention
across permissioned, redacted physical court notice photographs.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.modules.ocr.service import extract_text_blocks_from_image, _ocr_engine
from backend.modules.image_quality.service import assess_image_quality
from backend.modules.validators.regex_patterns import (
    extract_dates_with_context,
    extract_monetary_amounts,
    extract_case_numbers,
    extract_statutory_references
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OCRPilotEvaluator")

def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def calculate_cer_and_wra(ground_truth: str, prediction: str) -> Tuple[float, float]:
    """Calculates Character Error Rate (CER) and Word Recognition Accuracy (WRA)."""
    gt_chars = len(ground_truth)
    if gt_chars == 0:
        return (0.0, 100.0 if len(prediction) == 0 else 0.0)
    
    char_edits = levenshtein_distance(ground_truth, prediction)
    cer = min(1.0, char_edits / gt_chars)

    gt_words = [w.strip().lower() for w in ground_truth.split() if w.strip()]
    pred_words = [w.strip().lower() for w in prediction.split() if w.strip()]
    if not gt_words:
        return (cer, 100.0 if not pred_words else 0.0)
    
    word_edits = levenshtein_distance(" ".join(gt_words), " ".join(pred_words))
    word_acc = max(0.0, 1.0 - (word_edits / max(len(" ".join(gt_words)), 1))) * 100.0
    return (cer * 100.0, word_acc)

def evaluate_sample(sample_meta: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
    """Evaluates a single physical notice photograph against double-keyed ground truth."""
    sample_id = sample_meta["sample_id"]
    ground_truth_text = sample_meta.get("ground_truth_text", "")
    gt_fields = sample_meta.get("critical_fields", {})
    expected_quality = sample_meta.get("expected_quality", "READY")
    condition_tags = sample_meta.get("condition_tags", [])

    # 1. Quality Assessment Gate
    quality_result = assess_image_quality(image_bytes)
    abstention_triggered = quality_result.state == "NEEDS_RECAPTURE"
    abstention_correct = (quality_result.state == expected_quality)

    # 2. OCR Execution
    blocks = extract_text_blocks_from_image(image_bytes)
    predicted_text = "\n".join(b.text_original for b in blocks)

    # 3. Text Metrics
    cer, wra = calculate_cer_and_wra(ground_truth_text, predicted_text)

    # 4. Critical Field Extraction & Deadline Evaluation
    pred_dates = extract_dates_with_context(predicted_text)
    pred_amounts = extract_monetary_amounts(predicted_text)
    pred_cases = extract_case_numbers(predicted_text)
    pred_statutes = extract_statutory_references(predicted_text)

    gt_date = gt_fields.get("hearing_date")
    gt_amount = gt_fields.get("penalty_amount")
    gt_case = gt_fields.get("case_number")
    gt_statute = gt_fields.get("statutory_section")

    # Match dates
    date_matched = False
    missed_deadline = False
    false_deadline = False

    if gt_date:
        matched_any = any(d.normalized_date == gt_date or gt_date in d.raw_text for d in pred_dates)
        if matched_any:
            date_matched = True
        else:
            missed_deadline = True
    else:
        if len(pred_dates) > 0 and any("hearing" in d.context_label for d in pred_dates):
            false_deadline = True

    # Match amounts
    amount_matched = False
    if gt_amount:
        amount_matched = any(gt_amount in a.raw_text or str(a.numeric_value) in gt_amount for a in pred_amounts)

    # Match case numbers
    case_matched = False
    if gt_case:
        case_matched = any(gt_case in c.clean_text or c.clean_text in gt_case for c in pred_cases)

    # Match statutes
    statute_matched = False
    if gt_statute:
        statute_matched = any(gt_statute.lower() in s.raw_text.lower() for s in pred_statutes)

    return {
        "sample_id": sample_id,
        "condition_tags": condition_tags,
        "quality_gate": {
            "predicted_state": quality_result.state,
            "expected_state": expected_quality,
            "reason_code": quality_result.reason_code,
            "abstention_correct": abstention_correct
        },
        "metrics": {
            "cer_percentage": round(cer, 2),
            "wra_percentage": round(wra, 2),
            "word_count_gt": len(ground_truth_text.split()),
            "word_count_pred": len(predicted_text.split())
        },
        "critical_fields": {
            "date": {"ground_truth": gt_date, "matched": date_matched, "missed": missed_deadline, "false_positive": false_deadline},
            "amount": {"ground_truth": gt_amount, "matched": amount_matched},
            "case_number": {"ground_truth": gt_case, "matched": case_matched},
            "statute": {"ground_truth": gt_statute, "matched": statute_matched}
        }
    }

def run_pilot_evaluation(manifest_path: str) -> Dict[str, Any]:
    """Runs the full evaluation across all samples listed in manifest_path."""
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    samples = manifest.get("samples", [])
    logger.info(f"Loaded {len(samples)} evaluation samples from {manifest_path}")

    results = []
    total_dates_gt = 0
    matched_dates = 0
    missed_deadlines = 0
    false_deadlines = 0

    total_amounts_gt = 0
    matched_amounts = 0

    total_cases_gt = 0
    matched_cases = 0

    total_statutes_gt = 0
    matched_statutes = 0

    quality_gate_evaluations = 0
    correct_abstentions = 0

    cer_sum = 0.0
    wra_sum = 0.0
    readable_sample_count = 0

    base_dir = Path(manifest_path).parent

    for s in samples:
        img_rel = s["image_path"]
        img_full = base_dir / img_rel
        if not img_full.exists():
            logger.warning(f"Image not found: {img_full}; skipping.")
            continue

        with open(img_full, "rb") as f:
            img_bytes = f.read()

        res = evaluate_sample(s, img_bytes)
        results.append(res)

        # Aggregate metrics
        q = res["quality_gate"]
        quality_gate_evaluations += 1
        if q["abstention_correct"]:
            correct_abstentions += 1

        if q["predicted_state"] != "NEEDS_RECAPTURE":
            readable_sample_count += 1
            cer_sum += res["metrics"]["cer_percentage"]
            wra_sum += res["metrics"]["wra_percentage"]

        cf = res["critical_fields"]
        if cf["date"]["ground_truth"]:
            total_dates_gt += 1
            if cf["date"]["matched"]:
                matched_dates += 1
            if cf["date"]["missed"]:
                missed_deadlines += 1
        if cf["date"]["false_positive"]:
            false_deadlines += 1

        if cf["amount"]["ground_truth"]:
            total_amounts_gt += 1
            if cf["amount"]["matched"]:
                matched_amounts += 1

        if cf["case_number"]["ground_truth"]:
            total_cases_gt += 1
            if cf["case_number"]["matched"]:
                matched_cases += 1

        if cf["statute"]["ground_truth"]:
            total_statutes_gt += 1
            if cf["statute"]["matched"]:
                matched_statutes += 1

    summary = {
        "dataset_type": manifest.get("dataset_type", "physical_paper_pilot"),
        "total_samples_evaluated": len(results),
        "readable_samples": readable_sample_count,
        "unreadable_abstentions": len(results) - readable_sample_count,
        "quality_gate_accuracy": round((correct_abstentions / max(quality_gate_evaluations, 1)) * 100.0, 2),
        "average_cer": round(cer_sum / max(readable_sample_count, 1), 2),
        "average_wra": round(wra_sum / max(readable_sample_count, 1), 2),
        "deadline_evaluation": {
            "total_ground_truth_deadlines": total_dates_gt,
            "exact_match_deadlines": matched_dates,
            "deadline_recall_pct": round((matched_dates / max(total_dates_gt, 1)) * 100.0, 2),
            "missed_deadlines_count": missed_deadlines,
            "false_deadlines_extracted": false_deadlines
        },
        "critical_field_accuracy": {
            "amounts_recall_pct": round((matched_amounts / max(total_amounts_gt, 1)) * 100.0, 2),
            "case_numbers_recall_pct": round((matched_cases / max(total_cases_gt, 1)) * 100.0, 2),
            "statutes_recall_pct": round((matched_statutes / max(total_statutes_gt, 1)) * 100.0, 2)
        },
        "sample_results": results
    }

    return summary

if __name__ == "__main__":
    if len(sys.argv) > 1:
        manifest_file = sys.argv[1]
    else:
        manifest_file = "data/benchmarks/physical_pilot_manifest.json"

    if os.path.exists(manifest_file):
        summary_res = run_pilot_evaluation(manifest_file)
        print(json.dumps(summary_res, indent=2))
    else:
        print(f"Manifest not found: {manifest_file}. Please consult docs/physical-ocr-evaluation-protocol.md.")
