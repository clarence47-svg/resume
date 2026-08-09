def score_jobs(state: dict) -> dict:
    return {"evaluations": state.get("evaluations", state.get("filtered_jobs", []))}
