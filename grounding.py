"""Structural grounding gates. Semantic support is separately checked, not certified."""
import re
from api_contracts import ModelTurn, Profile, Fact

def validate_turn(raw, evidence, catalog):
    turn = ModelTurn.model_validate(raw)
    ids = {c['id'] for c in evidence}
    programs = {p['id'] for p in catalog['programs']}
    if any(pid not in programs for pid in turn.program_ids):
        raise ValueError('Unknown route')
    for block in turn.blocks:
        if not set(block.citations) <= ids:
            raise ValueError('Citation was not retrieved')
        # Amounts, dates and URLs must come from structured records, not model prose.
        if re.search(r'https?://|<[^>]+>|\$\s*\d|\b\d{2,}\b', block.text):
            raise ValueError('Unvalidated numeric claim or URL')
        if re.search(r'you (?:are eligible|qualify|will receive|are approved)|vous (?:êtes admissible|recevrez|avez droit)', block.text, re.I):
            raise ValueError('Personal eligibility claim')
    for f in turn.proposed_facts:
        Profile(facts={f.field: Fact(value=f.value, state=f.value if f.value in ('unknown','declined') else 'proposed')})
    for q in turn.questions:
        if len(q) > 300 or re.search(r'(?:your|votre) (?:SIN|passport number|account number|password|numéro d.assurance sociale|mot de passe)', q, re.I):
            raise ValueError('Invalid question')
    return turn.model_dump()
