import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import TextBlock

def retrieve_relevant_blocks(
    db: Session,
    document_id: str,
    query: str,
    limit: int = 5
) -> List[TextBlock]:
    """
    Retrieves the most relevant text blocks from a single document.
    Enforces per-document scoping so cross-document leakage is strictly impossible.
    """
    all_blocks = db.query(TextBlock).filter(
        TextBlock.document_id == document_id
    ).all()
    
    if not all_blocks:
        return []
        
    query_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))
    if not query_tokens:
        return all_blocks[:limit]
        
    scored = []
    for block in all_blocks:
        block_tokens = set(re.findall(r'\b\w{3,}\b', block.text_normalized.lower()))
        overlap = query_tokens.intersection(block_tokens)
        score = len(overlap)
        scored.append((score, block))
        
    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [b for s, b in scored[:limit]]

