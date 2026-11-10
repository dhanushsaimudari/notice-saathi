import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import TextBlock

STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "the", "and", "for", "with", "from", "that", "this", "these", "those",
    "is", "are", "was", "were", "been", "being", "have", "has", "had", "does", "did",
    "can", "could", "should", "would", "will", "shall", "may", "might", "must",
    "about", "into", "through", "after", "before", "above", "below", "between",
    "any", "some", "such", "than", "then", "very", "just", "also", "out"
}

def retrieve_relevant_blocks(
    db: Session,
    document_id: str,
    query: str,
    limit: int = 5
) -> List[TextBlock]:
    """
    Retrieves the most relevant text blocks from a single document.
    Enforces per-document scoping so cross-document leakage is strictly impossible.
    Ignores common stop words so non-pertinent queries do not match on words like 'the'.
    """
    all_blocks = db.query(TextBlock).filter(
        TextBlock.document_id == document_id
    ).all()
    
    if not all_blocks:
        return []
        
    raw_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))
    if not raw_tokens:
        return []

    meaningful_tokens = {t for t in raw_tokens if t not in STOP_WORDS}
    query_tokens = meaningful_tokens if meaningful_tokens else raw_tokens

    scored = []
    for block in all_blocks:
        block_tokens = set(re.findall(r'\b\w{3,}\b', block.text_normalized.lower()))
        overlap = query_tokens.intersection(block_tokens)
        score = len(overlap)
        if score > 0:
            scored.append((score, block))

    if not scored:
        return []

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [b for s, b in scored[:limit]]

