def prepare_campaign(state: dict) -> dict:
    return {"campaign": state.get("campaign", {})}


def collect_sources(state: dict) -> dict:
    return {"collected_jobs": state.get("collected_jobs", state.get("jobs", []))}
