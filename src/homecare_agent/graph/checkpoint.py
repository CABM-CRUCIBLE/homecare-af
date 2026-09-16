# Author: C A B M
# Date: 2026-09-17

"""State Checkpointing and Pipeline Resumption.

Provides persistent state storage and retrieval, step sequencing (Steps 1–14),
and dynamic entry resolution to allow resuming execution from any step
(e.g., Step 4: generate_strategy) without re-running prior completed steps.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Any
import uuid

from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)

# Default checkpoint storage directory
DEFAULT_CHECKPOINT_DIR = Path(".homecare/checkpoints")

# ─── Canonical 14-Step Sequencing ──────────────────────────────────────────

ORDERED_STEPS: list[dict[str, Any]] = [
    {"number": 1, "name": "intake_feature", "description": "Feature intake & specification analysis"},
    {"number": 2, "name": "ask_clarifications", "description": "Interactive clarification Q&A"},
    {"number": 3, "name": "analyze_codebase", "description": "Codebase AST & pattern analysis"},
    {"number": 4, "name": "generate_strategy", "description": "Architecture strategy document"},
    {"number": 5, "name": "generate_tactical_plan", "description": "Tactical plan & work packages"},
    {"number": 6, "name": "generate_adrs", "description": "Architecture decision records"},
    {"number": 7, "name": "generate_agentic_prompts", "description": "Agentic prompts & file matrix"},
    {"number": 8, "name": "review_architecture", "description": "Architecture review & revision"},
    {"number": 9, "name": "create_branch", "description": "Git feature branch creation"},
    {"number": 10, "name": "execute_wave", "description": "Code generation & unit tests"},
    {"number": 11, "name": "run_e2e_tests", "description": "E2E and load testing"},
    {"number": 12, "name": "generate_manual_test_doc", "description": "QA manual test documentation"},
    {"number": 13, "name": "create_pr", "description": "Pull request & code review"},
    {"number": 14, "name": "notify_ready_for_merge", "description": "Merge readiness notification"},
]

STEP_NUMBER_TO_NAME: dict[int, str] = {s["number"]: s["name"] for s in ORDERED_STEPS}
STEP_NAME_TO_NUMBER: dict[str, int] = {s["name"]: s["number"] for s in ORDERED_STEPS}

# Nodes eligible as entry points when resuming
ENTRY_ELIGIBLE_NODES: set[str] = {s["name"] for s in ORDERED_STEPS} | {
    "write_files",
    "run_unit_tests",
    "commit_wave",
    "run_load_tests",
    "commit_test_suite",
    "commit_documentation",
    "perform_code_review",
    "apply_review_fixes",
    "commit_fixes",
    "post_review_comments",
}


def resolve_step_name(step_spec: str | int) -> str:
    """Resolve a step specification (number 1-14 or node name) to canonical node name.

    Args:
        step_spec: Step number (e.g. 4 or "4") or node name (e.g. "generate_strategy").

    Returns:
        Canonical node name.

    Raises:
        ValueError: If step specification is invalid.
    """
    if isinstance(step_spec, int):
        if step_spec in STEP_NUMBER_TO_NAME:
            return STEP_NUMBER_TO_NAME[step_spec]
        raise ValueError(f"Invalid step number: {step_spec}. Must be between 1 and {len(ORDERED_STEPS)}.")

    spec_str = str(step_spec).strip()
    if spec_str.isdigit():
        num = int(spec_str)
        if num in STEP_NUMBER_TO_NAME:
            return STEP_NUMBER_TO_NAME[num]
        raise ValueError(f"Invalid step number: {num}. Must be between 1 and {len(ORDERED_STEPS)}.")

    canonical = spec_str.lower().replace("-", "_")
    if canonical in ENTRY_ELIGIBLE_NODES:
        return canonical

    valid_names = ", ".join(s["name"] for s in ORDERED_STEPS)
    raise ValueError(f"Unknown step name '{step_spec}'. Valid steps are: {valid_names}")


def get_step_number(step_name: str) -> int | None:
    """Get the step number (1-14) for a given node name if in canonical sequence."""
    return STEP_NAME_TO_NUMBER.get(step_name)


def resolve_next_step(state: dict[str, Any], explicit_step: str | int | None = None) -> str:
    """Determine the next step to execute when resuming.

    If explicit_step is provided, it is validated and used.
    Otherwise, inspects state['completed_steps'] and state['current_step'] to
    find the highest completed step and advances to the next step.

    Args:
        state: The restored AgentState dictionary.
        explicit_step: Optional explicit step name or number override.

    Returns:
        Canonical node name to resume from.
    """
    if explicit_step is not None:
        return resolve_step_name(explicit_step)

    completed = state.get("completed_steps", [])
    highest_step_num = 0

    for step in completed:
        num = STEP_NAME_TO_NUMBER.get(step)
        if num and num > highest_step_num:
            highest_step_num = num

    # Also check current_step if present
    current_step = state.get("current_step")
    if current_step and highest_step_num == 0:
        current_num = STEP_NAME_TO_NUMBER.get(current_step)
        if current_num:
            # Assume current_step failed/interrupted, so retry current_step
            return current_step

    next_step_num = highest_step_num + 1
    if next_step_num in STEP_NUMBER_TO_NAME:
        return STEP_NUMBER_TO_NAME[next_step_num]

    # Default fallback to Step 1 if nothing completed or invalid
    return "intake_feature"


# ─── State Pruning (ARCH-02) ─────────────────────────────────────────────


def prune_state(
    state: dict[str, Any] | AgentState,
    max_errors: int = 50,
    max_findings: int = 100,
) -> dict[str, Any]:
    """Prune unbounded state fields (ARCH-02) prior to checkpoint persistence.

    Caps errors list to `max_errors` most recent entries.
    Caps code_review_findings list to `max_findings` most recent entries.
    Records count of pruned items to maintain observability.

    Args:
        state: State dictionary to prune.
        max_errors: Maximum number of recent error records to retain.
        max_findings: Maximum number of recent code review findings to retain.

    Returns:
        Pruned state dictionary copy.
    """
    pruned = dict(state)
    errors = pruned.get("errors", [])
    if isinstance(errors, list) and len(errors) > max_errors:
        pruned_count = len(errors) - max_errors
        pruned["errors"] = errors[-max_errors:]
        pruned["_pruned_error_count"] = pruned.get("_pruned_error_count", 0) + pruned_count
        logger.debug("[PRUNE:STATE] Pruned %d older error(s) from state", pruned_count)

    findings = pruned.get("code_review_findings", [])
    if isinstance(findings, list) and len(findings) > max_findings:
        pruned_count = len(findings) - max_findings
        pruned["code_review_findings"] = findings[-max_findings:]
        pruned["_pruned_findings_count"] = pruned.get("_pruned_findings_count", 0) + pruned_count
        logger.debug("[PRUNE:STATE] Pruned %d older review finding(s) from state", pruned_count)

    return pruned


# ─── Safe Serialization ──────────────────────────────────────────────────


class _StateEncoder(json.JSONEncoder):
    """Custom JSON encoder handling Path, datetime, and LangChain objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if hasattr(o, "model_dump"):
            return o.model_dump()
        if hasattr(o, "dict"):
            return o.dict()
        if hasattr(o, "to_json"):
            return o.to_json()
        if hasattr(o, "__dict__"):
            return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
        return super().default(o)


# ─── Checkpoint Manager ──────────────────────────────────────────────────


class CheckpointManager:
    """Manages disk persistence and restoration of AgentState."""

    def __init__(self, checkpoint_dir: Path | str = DEFAULT_CHECKPOINT_DIR) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, trace_id: str) -> Path:
        clean_id = trace_id.strip().replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{clean_id}.json"

    def save_checkpoint(
        self,
        trace_id: str,
        state: AgentState | dict[str, Any],
        last_step: str = "",
    ) -> Path:
        """Save state to checkpoint file with atomic write, SHA-256 integrity, and pruning.

        Args:
            trace_id: Unified workflow trace ID.
            state: Active state dictionary.
            last_step: Node/step that just completed.

        Returns:
            Path to the saved checkpoint file.
        """
        if not trace_id:
            trace_id = state.get("trace_id", "unnamed_run")

        file_path = self._get_checkpoint_path(trace_id)

        # Build checkpoint metadata payload
        completed_steps = list(state.get("completed_steps", []))
        if last_step and last_step not in completed_steps:
            completed_steps.append(last_step)

        # Copy state and update completed_steps
        state_copy = dict(state)
        state_copy["completed_steps"] = completed_steps
        state_copy["last_checkpoint_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if last_step:
            state_copy["last_completed_step"] = last_step

        # STATE-02: Persist llm_call_count
        llm_call_count = int(state.get("llm_call_count", 0))
        state_copy["llm_call_count"] = llm_call_count

        # ARCH-02: Apply state pruning
        state_copy = prune_state(state_copy)

        checkpoint_data = {
            "version": "1.0",
            "trace_id": trace_id,
            "feature_name": state.get("feature_name", ""),
            "feature_description": state.get("feature_description", ""),
            "last_completed_step": last_step or state.get("last_completed_step", ""),
            "last_completed_step_number": get_step_number(last_step) if last_step else None,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "llm_call_count": llm_call_count,
            "state": state_copy,
        }

        try:
            # CP-02: Use unique UUID suffix instead of float timestamp
            temp_path = file_path.with_suffix(f".tmp_{uuid.uuid4().hex[:8]}")
            initial_bytes = json.dumps(checkpoint_data, cls=_StateEncoder, indent=2).encode("utf-8")
            checksum = hashlib.sha256(initial_bytes).hexdigest()
            checkpoint_data["checksum"] = checksum
            final_bytes = json.dumps(checkpoint_data, cls=_StateEncoder, indent=2).encode("utf-8")
            final_checksum = hashlib.sha256(final_bytes).hexdigest()

            with open(temp_path, "wb") as f:
                f.write(final_bytes)
            temp_path.replace(file_path)

            # CP-01: Write checksum sidecar file
            checksum_path = file_path.with_suffix(".sha256")
            with open(checksum_path, "w", encoding="utf-8") as f:
                f.write(f"{final_checksum}  {file_path.name}\n")

            logger.debug("[CHECKPOINT:SAVED] Checkpoint saved at %s for trace_id=%s (step=%s, sha256=%s)", file_path, trace_id, last_step, final_checksum[:8])
        except Exception as e:
            logger.error("[CHECKPOINT:ERROR] Failed to save checkpoint at %s: %s", file_path, e)

        return file_path

    def load_checkpoint(self, trace_id_or_path: str | Path) -> dict[str, Any]:
        """Load checkpoint state from disk by trace ID or direct path with integrity verification.

        Args:
            trace_id_or_path: Trace ID (e.g. 32-hex string) or Path to checkpoint file.

        Returns:
            Dictionary containing metadata and the restored AgentState under ['state'].

        Raises:
            FileNotFoundError: If checkpoint cannot be found.
            ValueError: If checkpoint checksum integrity verification fails.
        """
        path = Path(trace_id_or_path)
        if not path.is_file():
            # Try finding under checkpoint_dir
            path = self._get_checkpoint_path(str(trace_id_or_path))

        if not path.is_file():
            # Try searching for partial trace match
            candidates = list(self.checkpoint_dir.glob(f"*{trace_id_or_path}*.json"))
            if candidates:
                path = candidates[0]
            else:
                raise FileNotFoundError(f"No checkpoint found for trace ID or path: {trace_id_or_path}")

        # CP-01: Read bytes and verify checksum against sidecar if present
        with open(path, "rb") as f:
            raw_bytes = f.read()

        computed_sha = hashlib.sha256(raw_bytes).hexdigest()
        checksum_path = path.with_suffix(".sha256")
        if checksum_path.is_file():
            expected_sha = checksum_path.read_text(encoding="utf-8").strip().split()[0]
            if expected_sha and computed_sha != expected_sha:
                raise ValueError(
                    f"Checkpoint integrity verification failed for {path}: "
                    f"expected {expected_sha}, computed {computed_sha}"
                )

        data = json.loads(raw_bytes.decode("utf-8"))

        logger.info("[CHECKPOINT:LOADED] Loaded checkpoint from %s (trace_id=%s)", path, data.get("trace_id"))
        return data

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints sorted by timestamp (newest first).

        Returns:
            List of summary dicts with trace_id, feature_name, last_step, timestamp.
        """
        results: list[dict[str, Any]] = []
        if not self.checkpoint_dir.exists():
            return results

        for p in self.checkpoint_dir.glob("*.json"):
            try:
                stat = p.stat()
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                last_step = data.get("last_completed_step", "")
                step_num = data.get("last_completed_step_number") or get_step_number(last_step)
                results.append({
                    "path": str(p),
                    "trace_id": data.get("trace_id", p.stem),
                    "feature_name": data.get("feature_name", "Unknown"),
                    "last_completed_step": last_step,
                    "last_completed_step_number": step_num,
                    "timestamp": data.get("timestamp", ""),
                    "mtime": stat.st_mtime,
                    "next_recommended_step": resolve_next_step(data.get("state", {})),
                })
            except Exception as e:
                logger.warning("Could not read checkpoint %s: %s", p, e)

        # Sort newest first
        results.sort(key=lambda x: (x.get("timestamp", ""), x.get("mtime", 0.0)), reverse=True)
        return results

    def get_latest_checkpoint(self) -> dict[str, Any] | None:
        """Return the most recently modified checkpoint, or None if none exist."""
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None
        return self.load_checkpoint(checkpoints[0]["path"])
