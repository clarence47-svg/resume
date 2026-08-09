def render_exports(state: dict) -> dict:
    return {"result": state.get("document", {}), "export_paths": state.get("export_paths", {})}
