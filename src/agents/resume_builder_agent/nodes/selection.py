def select_content(state: dict) -> dict:
    return {"selected_content": state.get("match_result", {})}
