from profile.models import ProfileFact

from langgraph.types import interrupt


def optional_review(state: dict) -> dict:
    if state.get("review_mode") != "pause" or state.get("review_completed"):
        return {}
    resumed = interrupt(
        {
            "task_id": state["task_id"],
            "facts": state.get("facts", []),
            "conflicts": state.get("conflicts", []),
        }
    )
    payload = resumed.get("facts", resumed) if isinstance(resumed, dict) else resumed
    facts = [ProfileFact.model_validate(item) for item in payload]
    return {
        "facts": [fact.model_dump(mode="json") for fact in facts],
        "review_completed": True,
    }
