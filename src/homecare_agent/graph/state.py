# Author: C A B M
# Date: 2026-09-17

"""LangGraph state definition for the HomeCare Agentic Framework.

The AgentState is a TypedDict that flows through the entire LangGraph
workflow. Each node reads and writes specific keys. The state is the
single source of truth for the pipeline's progress.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


def merge_dicts(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Reducer that merges dictionaries (new keys override existing)."""
    merged = {**existing}
    merged.update(new)
    return merged


def append_list(existing: list[Any], new: list[Any]) -> list[Any]:
    """Reducer that appends to a list without duplicates by 'id' key if dicts."""
    result = list(existing)
    existing_ids = {item.get("id") for item in result if isinstance(item, dict) and "id" in item}
    for item in new:
        if isinstance(item, dict) and "id" in item:
            if item["id"] not in existing_ids:
                result.append(item)
                existing_ids.add(item["id"])
        else:
            result.append(item)
    return result


class AgentState(TypedDict, total=False):
    """Central state flowing through the LangGraph workflow.

    Organized into logical sections:
    - Input: User-provided feature request data
    - Clarification: Interactive Q&A loop
    - Analysis: Codebase analysis results
    - Architecture: Generated documents
    - Execution: Code generation and git operations
    - Testing: Test execution results
    - Review: Code review and PR
    - Status: Pipeline progress tracking
    """

    # ─── Input ───────────────────────────────────────────────────────────
    trace_id: str
    feature_name: str
    feature_description: str
    wireframe_paths: list[str]
    wireframe_urls: list[str]
    repo_path: str
    repo_url: str

    # ─── Model Routing Overrides ─────────────────────────────────────────
    model_architecture: str
    model_code: str
    model_review: str
    model_intake: str
    node_models: dict[str, str]

    # ─── Clarification Loop ──────────────────────────────────────────────
    clarification_questions: Annotated[list[dict[str, Any]], append_list]
    clarification_answers: Annotated[list[dict[str, Any]], append_list]
    clarification_complete: bool
    clarification_iteration: int

    # ─── Analysis ────────────────────────────────────────────────────────
    codebase_analysis: Annotated[dict[str, Any], merge_dicts]
    existing_patterns: Annotated[dict[str, Any], merge_dicts]
    gap_analysis: Annotated[dict[str, Any], merge_dicts]

    # ─── Architecture Documents ──────────────────────────────────────────
    strategy_document: str
    tactical_plan: str
    adr_documents: Annotated[list[dict[str, Any]], append_list]
    architecture_review: str
    architecture_approved: bool
    arch_iteration: int

    # ─── Agentic Prompts ─────────────────────────────────────────────────
    standing_instructions: str
    agentic_prompts: Annotated[list[dict[str, Any]], append_list]
    file_ownership_matrix: Annotated[list[dict[str, str]], append_list]

    # ─── Execution ───────────────────────────────────────────────────────
    branch_name: str
    work_packages: Annotated[list[dict[str, Any]], append_list]
    current_wave: int
    current_wp_index: int
    generated_code: Annotated[dict[str, str], merge_dicts]

    # ─── Testing ─────────────────────────────────────────────────────────
    backend_test_results: Annotated[dict[str, Any], merge_dicts]
    frontend_test_results: Annotated[dict[str, Any], merge_dicts]
    e2e_test_results: Annotated[dict[str, Any], merge_dicts]
    load_test_results: Annotated[dict[str, Any], merge_dicts]

    # ─── Review ──────────────────────────────────────────────────────────
    pr_number: int
    pr_url: str
    code_review_findings: Annotated[list[dict[str, Any]], append_list]
    review_changes_needed: bool
    review_iteration: int

    # ─── Status & Resource Tracking ───────────────────────────────────────
    current_step: str
    completed_steps: Annotated[list[str], append_list]
    errors: Annotated[list[dict[str, Any]], append_list]
    commit_log: Annotated[list[dict[str, str]], append_list]
    llm_call_count: int

    # ─── Messages (LangGraph built-in) ───────────────────────────────────
    messages: Annotated[list[Any], add_messages]
