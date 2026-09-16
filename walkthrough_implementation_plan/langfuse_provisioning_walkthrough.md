# Walkthrough: Automatic Langfuse Provisioning & Single Unified Trace ID

We have implemented automatic headless initialization for the local Langfuse instance and unified single `trace_id` propagation across the entire LangGraph workflow run.

## 1. Automated Langfuse Provisioning

Langfuse is configured to self-provision on startup using headless initialization environment variables defined in [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml) and [.env](file:///c:/WorkingFolder/homecare-af/.env).

### Access & Credentials
| Parameter | Value | Config Source |
|---|---|---|
| **Web UI URL** | `http://localhost:13000` | `docker-compose.yml` (`ports: 13000:3000`) |
| **Email / Username** | `admin@homecare.local` | `LANGFUSE_INIT_USER_EMAIL` |
| **Password** | `HomeCareAdmin123!` | `LANGFUSE_INIT_USER_PASSWORD` |
| **Organization** | `HomeCare` (`homecare-org`) | `LANGFUSE_INIT_ORG_NAME` / `ID` |
| **Project** | `HomeCare` (`homecare`) | `LANGFUSE_INIT_PROJECT_NAME` / `ID` |
| **Public Key** | `pk-lf-homecare-local` | `LANGFUSE_PUBLIC_KEY` |
| **Secret Key** | `sk-lf-homecare-local` | `LANGFUSE_SECRET_KEY` |

> [!NOTE]
> Database port for PostgreSQL container is mapped to `15432:5432` (`${LANGFUSE_DB_PORT:-15432}:5432`) to prevent collisions if a PostgreSQL server is already running on the host machine's port 5432.

---

## 2. Single Unified Trace ID Implementation

Each workflow execution generates exactly one OpenTelemetry-compliant 32-character hexadecimal trace ID (`^[0-9a-f]{32}$`) that links every node, span, generation, and callback.

### Key Changes
1. **[state.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/state.py)**:
   - Added `trace_id: str` to `AgentState`.
2. **[provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)**:
   - Added `normalize_trace_id(trace_id)` ensuring 32-character lowercase hex format.
   - Added `set_workflow_trace(trace_id, trace_name)` to configure the root trace for the pipeline.
   - Added `get_langfuse_handler(trace_id)` returning a Langfuse `CallbackHandler` bound to `trace_context={"trace_id": norm_id}`.
   - Updated `ainvoke`, `ainvoke_with_vision`, and `invoke_sync` to resolve the single trace ID from `state_overrides["trace_id"]` or workflow trace ID and pass `metadata["workflow_trace_id"]`.
3. **[main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)**:
   - Generates `trace_id = uuid.uuid4().hex` in `run` and `generate` commands.
   - Binds `llm.set_workflow_trace(trace_id)` and populates `initial_state["trace_id"]`.
   - Passes `config={"callbacks": [handler]}` to `graph.astream(...)` so the root LangGraph execution is attached to the trace.
   - Displays trace ID and clickable Langfuse trace URL in the console.
4. **[web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)**:
   - Generates `trace_id` and renders a direct markdown link in the Gradio status panel.
5. **[main_graph.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/main_graph.py) & Node Implementations**:
   - Ensured all node calls pass `state_overrides=state` and `node_name` to preserve trace context.

---

## 3. Verification & Testing

### Live Container Verification
- Started `langfuse-db` and `langfuse-server` via `docker compose up -d`.
- Verified HTTP health check:
  ```json
  GET http://localhost:13000/api/public/health -> 200 {"status":"OK","version":"2.95.11"}
  ```
- Queried PostgreSQL database in `langfuse-db`:
  - `users`: `admin@homecare.local | HomeCare Admin` (1 row)
  - `organizations`: `homecare-org | HomeCare` (1 row)
  - `projects`: `homecare | HomeCare` (1 row)
  - `api_keys`: `homecare | pk-lf-homecare-local` (1 row)
- Tested credentials login via HTTP POST:
  ```
  POST http://localhost:13000/api/auth/callback/credentials -> 200 {"url":"http://localhost:13000"}
  ```

### Automated Unit Test Suite
- Ran full test suite including test suite in `tests/test_tracing.py` and `tests/test_nodes.py`:
  ```bash
  pytest tests/ -v
  ```
- **Results:** 44 passed in 1.93s (100% passing).

---

## 4. Comprehensive Node Logging & Error Tracing

Standardized, trace-aware logging has been integrated across all LangGraph nodes in the pipeline to make error tracing and root-cause analysis straightforward:

### Logging Standard Pattern
Every node adheres to the following structure:
- **Node Start:**
  ```python
  logger.info("[START:<node_name>][trace_id=%s] <description> for '%s'", trace_id, feature_name, ...)
  ```
- **Checkpoint / Progress:**
  ```python
  logger.debug("[<node_name>][trace_id=%s] <progress info>", trace_id, ...)
  ```
- **Node Completion:**
  ```python
  logger.info("[COMPLETED:<node_name>][trace_id=%s] <summary of outputs>", trace_id, ...)
  ```
- **Error Handling & State Propagation:**
  ```python
  except Exception as e:
      logger.error(
          "[ERROR:<node_name>][trace_id=%s] <Operation> failed for '%s': %s",
          trace_id, feature_name, e, exc_info=True
      )
      return {
          "errors": [{"step": "<node_name>", "trace_id": trace_id, "message": f"<Operation> failed: {e}"}],
          "current_step": "<node_name>",
          "completed_steps": ["<node_name>"],
      }
  ```

### Updated Nodes
1. [intake.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/intake.py): `intake_feature` — vision wireframe analysis & requirements parsing with trace correlation.
2. [analyze.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/analyze.py): `analyze_codebase` — repo scan progress and structured error reporting.
3. [architect.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/architect.py): `generate_strategy`, `generate_tactical_plan`, `generate_adrs`.
4. [generate_prompts.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/generate_prompts.py): `generate_agentic_prompts`.
5. [review_arch.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/review_arch.py): `review_architecture`.
6. [execute_prompt.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/execute_prompt.py): `execute_wave`, `_execute_single_wp`, `write_generated_files`.
7. [code_review.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/code_review.py): `perform_code_review`, `apply_review_fixes`.
8. [git_ops.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/git_ops.py): `create_branch`, `commit_and_push`, `create_pull_request`.
9. [main_graph.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/main_graph.py): `_ask_clarifications`, `_revise_architecture`, `_run_tests`, `_generate_manual_test_doc`, `_post_review_comments`, `_notify_completion`.

---

## 5. Verification of Pipeline Gaps & Tool-Level Hardening

Following an audit across the entire codebase, several additional gaps in logging and exception handling were identified and addressed:

1. **Routing Edges ([routing.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/edges/routing.py))**:
   - Added trace-aware decision logging `[ROUTE:<edge>][trace_id=...] Decision -> ...` to `needs_clarification`, `arch_approved`, `more_waves`, and `changes_needed`.
2. **LLM Provider ([provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py))**:
   - Wrapped `ainvoke`, `ainvoke_with_vision`, and `invoke_sync` in `try...except` logging `[ERROR:LLMProvider][trace_id=...]` with model, node name, and traceback details before re-raising.
3. **Build & Test Tools ([build_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/build_tools.py))**:
   - Added command execution and completion logging.
   - Added generic `except Exception as e` handling to catch unexpected `OSError`, `PermissionError`, or subprocess faults instead of crashing.
4. **GitHub Tools ([github_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/github_tools.py))**:
   - Added structured exception handling and error logging around PyGithub and HTTP diff operations.
5. **Image Tools ([image_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/image_tools.py))**:
   - Protected `analyze_wireframe` vision invocations with `try...except` and structured error output.
6. **Codebase & File Tools ([codebase_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/codebase_tools.py), [file_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/file_tools.py))**:
   - Replaced silent `pass` in route analysis with debug logging and added extraction counts.

### Test Results
- Total tests passing: **45 passed in 1.91s** (`pytest tests/ -v`).

---

## 6. Safety Guardrails & API Credit Exhaustion Protection

To prevent credit exhaustion from uncontrolled retries or runaway graph loops, a multi-layered guardrail system has been established:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                    Inbound LLM Call                    │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │  Budget Ceiling: call_count >= MAX_CALLS? │
                       └───────┬───────────────────────────┬───────┘
                              YES                          NO
                               │                           │
                               ▼                           ▼
                     [LLMBudgetExceededError]   ┌─────────────────────┐
                     (Halt run immediately)     │ asyncio.Semaphore   │
                                                │ (Throttle parallel) │
                                                └──────────┬──────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────────┐
                                                │  Execute LLM Call   │
                                                └──────────┬──────────┘
                                                           │
                                     ┌─────────────────────┴─────────────────────┐
                                     │                                           │
                                  Success                                      Error
                                     │                                           │
                                     ▼                                           ▼
                                [Return Text]                 ┌─────────────────────────────────────┐
                                                              │ Status 402 / Insufficient Credits?   │
                                                              └──────┬───────────────────────┬──────┘
                                                                    YES                      NO
                                                                     │                       │
                                                                     ▼                       ▼
                                                        [InsufficientCreditsError]   Transient (429/503)?
                                                        (Fail-Fast: NO retries)              │
                                                                                 ┌───────────┴───────────┐
                                                                                YES                      NO
                                                                                 │                       │
                                                                                 ▼                       ▼
                                                                        Exponential Backoff        [Re-raise]
                                                                        (up to max_retries)
```

### 1. Fail-Fast Credit Exhaustion Detection
- **Error Types Caught:** HTTP 402 status code, `insufficient_credits`, `payment_required`, `out of credits`, `credit balance is too low`.
- **Behavior:** Immediately trips an `InsufficientCreditsError` without retrying. This prevents draining credits or hanging while an API key is depleted.

### 2. Transient Error Retry & Exponential Backoff
- **Error Types Retried:** HTTP 429 (Rate Limit), 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout).
- **Behavior:** Bounded by `MAX_RETRIES` (default: 3). Implements exponential backoff (`(2 ** attempt) + 0.5` seconds) before retrying.

### 3. Global Workflow Call Budget Ceiling
- **Setting:** `MAX_LLM_CALLS_PER_RUN` (default: 60, configurable via `.env` or CLI).
- **Behavior:** Tracks cumulative invocations on `LLMProvider.call_count`. If a runaway process exceeds this threshold, it raises `LLMBudgetExceededError` and halts the workflow run before incurring excessive costs.

### 4. Concurrency Throttling via Semaphore
- **Setting:** `asyncio.Semaphore(settings.max_parallel_workers)` inside `LLMProvider`.
- **Behavior:** Caps concurrent outbound LLM requests during parallel wave execution to prevent bursting OpenRouter concurrency limits.

### 5. LangGraph Cyclic Edge Loop Ceilings
Bounded loop iterations prevent infinite loops in the workflow graph:
- **Architecture Review Loop:** `MAX_ARCH_ITERATIONS` (default: 3). If rejected 3 times, `arch_approved` logs a warning and routes to `create_branch` to prevent endless revision cycles.
- **Clarification Loop:** `MAX_CLARIFICATION_ITERATIONS` (default: 2). If user clarification questions cycle twice, `needs_clarification` forces progression to `analyze_codebase`.
- **Code Review Loop:** `MAX_REVIEW_ITERATIONS` (default: 3). After 3 fix cycles, `changes_needed` forces progression to `post_review_comments`.

### 6. Automated Unit Tests
A dedicated test suite was added in [test_guardrails.py](file:///c:/WorkingFolder/homecare-af/tests/test_guardrails.py):
- `test_credit_exhaustion_detection`: Verifies keywords and status 402 matching.
- `test_retryable_error_detection`: Verifies HTTP 429/503 matching.
- `test_insufficient_credits_fail_fast`: Verifies zero retries when 402 is raised.
- `test_llm_budget_ceiling`: Verifies `LLMBudgetExceededError` triggers at max calls.
- `test_retry_on_transient_rate_limit`: Verifies backoff and successful recovery.
- `test_arch_iteration_guardrail`: Verifies loop cutoff after max architecture iterations.
- `test_clarification_iteration_guardrail`: Verifies loop cutoff after max clarification iterations.

**Final Test Results:** **52 passed in 1.90s** (`pytest tests/ -v`).



