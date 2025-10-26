from app.config import SET

def evidence_ok(docs) -> bool:
    return len(docs) >= SET.min_evidence
