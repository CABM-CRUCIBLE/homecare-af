# Implementation Plan — Priority Actions Remediation (Section 6)

This implementation plan addresses the 12 prioritized architectural, concurrency, security, resilience, and code quality remediation actions identified in **Section 6 of the Senior Software Architect Code Review (Level 3)**.

---

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **ARCH-01 (Error Halting):** Critical architecture nodes (`generate_strategy`, `generate_tactical_plan`, `generate_agentic_prompts`) will route to a new terminal node `error_halt` if essential outputs (such as `strategy_document`, `tactical_plan`, or `prompts`) are missing or failed. The pipeline will cleanly stop rather than silently cascading through downstream nodes on empty state.
> 2. **ARCH-03 (Node Modularization):** The 6 inline node functions in [main_graph.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/main_graph.py) (`_ask_clarifications`, `_revise_architecture`, `_run_tests`, `_generate_manual_test_doc`, `_post_review_comments`, `_notify_completion`) will be extracted into dedicated modules under `src/homecare_agent/graph/nodes/`. Backward-compatible aliases will remain in `main_graph.py` so existing tests and imports are preserved.
> 3. **CP-01 (Checkpoint Integrity):** Checkpoints will write and verify a SHA-256 checksum envelope and `.sha256` sidecar file to detect file truncation or tampering on load.
> 4. **UI-01 (Web UI):** Gradio `start_pipeline` will be upgraded from a static stub to an async streaming generator that invokes `compile_graph` and streams live step progress updates to the UI, while clearly noting CLI options for interactive headless runs.

---

## Proposed Changes

The changes span 12 items grouped across P0, P1, and P2 priority tiers.

### Component 1: State Management & Reducers (`STATE-01`, `STATE-02`, `ARCH-02`)

#### [MODIFY] [state.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/state.py)
- **STATE-01:** Update `append_list` reducer to deduplicate primitive types (such as `str` in `completed_steps`) in addition to dicts by `"id"`. Prevents duplicate step names during retry or revision loops.
- **STATE-02:** Ensure `llm_call_count` is recognized and typed in `AgentState`.

#### [MODIFY] [checkpoint.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/checkpoint.py)
- **CP-01 & CP-02:** 
  - Compute SHA-256 checksum of saved JSON payload and store inside envelope (`"checksum": "<sha256>"`) and write `<trace_id>.sha256` sidecar.
  - On `load_checkpoint`: verify checksum integrity before returning state. Raise `ValueError` if checksum mismatch occurs.
  - Use `uuid.uuid4().hex[:8]` for temporary checkpoint files instead of float timestamps to eliminate collision risk.
- **STATE-02:** Save and persist `llm_call_count` into state and metadata envelope.
- **ARCH-02:** Implement `prune_state(state: dict[str, Any], max_errors: int = 50, max_findings: int = 100) -> dict[str, Any]` to cap unbounded growth of error logs and code review findings before serialization.

---

### Component 2: LLM Provider & Concurrency (`LLM-01`, `LLM-02`, `STATE-02`)

#### [MODIFY] [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)
- **LLM-01:** Add `self._sync_budget_lock = threading.Lock()` in `LLMProvider.__init__`. Acquire `self._sync_budget_lock` in `_check_and_increment_budget_sync()` so synchronous invocations across threads cannot race on `self._call_count`.
- **LLM-02:** Unify model cache key strategy in `get_llm()`: always use `cache_key = f"{clean_model}@{effective_base_url}"` and remove redundant non-URL cache path.
- **STATE-02:** Add `set_call_count(self, count: int) -> None` protected by `_sync_budget_lock` so resumed pipelines restore prior budget consumption.

---

### Component 3: JSON Parsing Utility (`CODEGEN-01`)

#### [NEW] [json_utils.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/json_utils.py)
- Implement `extract_json(text: str, default: Any = None) -> Any` with:
  - Markdown code block fence stripping (```json ... ``` and ``` ... ```).
  - Outermost brace `{...}` and bracket `[...]` detection.
  - Trailing comma cleanup and json parsing with error logging.
  - Safe fallback to default if parsing fails.

#### [MODIFY] [tools/__init__.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/__init__.py)
- Export `extract_json` from `tools`.

#### [MODIFY] [intake.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/intake.py)
#### [MODIFY] [analyze.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/analyze.py)
#### [MODIFY] [architect.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/architect.py)
#### [MODIFY] [generate_prompts.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/generate_prompts.py)
#### [MODIFY] [review_arch.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/review_arch.py)
- Adopt `extract_json` to replace fragile slice-based `json.loads` parsing.

---

### Component 4: Edge Routing & Error Sentinel Edges (`ARCH-01`, `EDGE-01`)

#### [MODIFY] [routing.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/edges/routing.py)
- **EDGE-01:** In `more_waves()`, filter out empty or falsy wave IDs:
  `wave_ids = sorted(list({str(wp["wave"]) for wp in work_packages if wp.get("wave")}))`
  Eliminates phantom wave `""` that causes infinite loops.
- **ARCH-01:** Add sentinel routing functions:
  - `check_strategy_output(state: AgentState) -> Literal["generate_tactical_plan", "error_halt"]`: checks if `strategy_document` is populated.
  - `check_tactical_output(state: AgentState) -> Literal["generate_adrs", "error_halt"]`: checks if `tactical_plan` and `work_packages` are populated.
  - `check_prompts_output(state: AgentState) -> Literal["review_architecture", "error_halt"]`: checks if `prompts` are generated.

#### [MODIFY] [execute_prompt.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/execute_prompt.py)
- **EDGE-01:** Ensure `execute_wave` ignores work packages with empty wave assignments, aligning with `more_waves()`.

---

### Component 5: Node Extraction & Modularization (`ARCH-03`, `ARCH-01`)

#### [NEW] [clarification.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/clarification.py)
- Extract `ask_clarifications` from `main_graph.py`.

#### [NEW] [testing.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/testing.py)
- Extract `run_tests` from `main_graph.py`.

#### [NEW] [documentation.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/documentation.py)
- Extract `generate_manual_test_doc` from `main_graph.py`.

#### [NEW] [notifications.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/notifications.py)
- Extract `post_review_comments`, `notify_completion` from `main_graph.py`.
- Implement `error_halt(state: AgentState, settings: Settings) -> dict[str, Any]` for `ARCH-01`.

#### [MODIFY] [review_arch.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/review_arch.py)
- Add `revise_architecture` extracted from `main_graph.py`.

#### [MODIFY] [main_graph.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/main_graph.py)
- Register `error_halt` node.
- Wire conditional sentinel edges after `generate_strategy`, `generate_tactical_plan`, and `generate_agentic_prompts`.
- Connect `error_halt` to `END`.
- Replace inline node implementations with imports from dedicated node modules.
- Maintain backward-compatible aliases for existing tests.

---

### Component 6: Pipeline Execution & Resumption (`STATE-02`)

#### [MODIFY] [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)
- In `_run_pipeline`: update `final_state["llm_call_count"] = llm.call_count` before checkpointing.
- In `_execute_resume`: when resuming from checkpoint, call `llm.set_call_count(saved_state.get("llm_call_count", 0))` to maintain budget integrity across runs.

---

### Component 7: Web UI Streaming & Preview Improvements (`UI-01`)

#### [MODIFY] [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- Upgrade `start_pipeline` to an async generator that yields live progress updates for each step using `graph.astream(...)`.
- Add prominent badges: `[Interactive Studio & Execution Monitor]` with CLI instructions for batch mode.
- Cache checkpoint choices cleanly to avoid redundant disk reads.

---

### Component 8: Docker Security Parameterization (`SEC-04`)

#### [MODIFY] [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml)
- Parameterize `POSTGRES_USER` and `POSTGRES_PASSWORD` with `${LANGFUSE_DB_USER:-postgres}` and `${LANGFUSE_DB_PASSWORD:-postgres}`.
- Parameterize `DATABASE_URL` and `pg_isready` healthcheck command.

---

## Verification Plan

### Automated Tests
1. Run existing full test suite to guarantee zero regression:
   ```powershell
   pytest
   ```
2. Create dedicated comprehensive test suite `tests/test_priority_actions.py` testing all 12 items:
   - `test_state_append_list_deduplicates_strings()` (STATE-01)
   - `test_sync_budget_counter_thread_safety()` (LLM-01)
   - `test_model_cache_unified_key()` (LLM-02)
   - `test_checkpoint_checksum_verification_and_tamper_detection()` (CP-01)
   - `test_checkpoint_uuid_temp_files()` (CP-02)
   - `test_more_waves_filters_empty_wave_ids()` (EDGE-01)
   - `test_json_utils_strips_fences_and_extracts_cleanly()` (CODEGEN-01)
   - `test_state_pruning_caps_errors_and_findings()` (ARCH-02)
   - `test_error_halt_sentinel_edge_triggers_on_missing_strategy()` (ARCH-01)
   - `test_extracted_nodes_callable_from_dedicated_modules()` (ARCH-03)
   - `test_llm_call_count_persisted_and_restored()` (STATE-02)
   - `test_docker_compose_credentials_parameterized()` (SEC-04)

### Manual Verification
- Verify `pytest -v tests/test_priority_actions.py` passes cleanly.
- Verify CLI `--help` and checkpoint commands run smoothly.
