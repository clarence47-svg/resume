from langgraph.types import interrupt


def confirmation(state: dict) -> dict:
    if state.get("confirmed"):
        return {"confirmed": True}
    decision = interrupt(
        {
            "type": "application_confirmation",
            "preview": state.get("preview", {}),
            "preview_hash": state.get("preview_hash", ""),
        }
    )
    return {"confirmed": bool(decision)}
