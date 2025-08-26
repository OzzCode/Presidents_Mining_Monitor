from config import EFFICIENCY_J_PER_TH, EFFICIENCY_MAP

def efficiency_for_model(model: str | None) -> float:
    """
    Return J/TH for a given model using a fuzzy match against EFFICIENCY_MAP.
    Falls back to EFFICIENCY_J_PER_TH if no match.
    """
    if not model:
        return EFFICIENCY_J_PER_TH

    name = model.strip().lower()
    # try exact-ish keys first
    for key, val in EFFICIENCY_MAP.items():
        if key.lower() == name:
            return val
    # fuzzy contains match (handles 'Antminer S19 Pro', 'S19 Pro 110T', etc.)
    for key, val in EFFICIENCY_MAP.items():
        if key.lower() in name:
            return val
    return EFFICIENCY_J_PER_TH
