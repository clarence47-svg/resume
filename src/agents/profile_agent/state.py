import operator
from typing import Annotated, Any, TypedDict


class ProfileAgentState(TypedDict, total=False):
    task_id: str
    export_dir: str
    mode: str
    review_mode: str
    review_completed: bool
    chunks: list[dict[str, Any]]
    chunk: dict[str, Any]
    extracted_fact_batches: Annotated[list[list[dict[str, Any]]], operator.add]
    facts: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    section_name: str
    section_outputs: Annotated[list[dict[str, Any]], operator.add]
    result: dict[str, Any]
    export_paths: dict[str, str]
    warnings: Annotated[list[str], operator.add]
