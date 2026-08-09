def shortlist(state: dict) -> dict:
    items = [
        item
        for item in state.get("evaluations", [])
        if item.get("passed", True) and not item.get("rejected", False)
    ]
    return {"shortlist": items}


def persist(state: dict) -> dict:
    return {
        "result": {
            "shortlist": state.get("shortlist", []),
            "duplicates": state.get("duplicate_ids", []),
        }
    }
