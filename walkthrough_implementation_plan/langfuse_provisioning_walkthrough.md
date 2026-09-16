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

---

## 7. Security Hardening & Threat Mitigation

A multi-layered defense-in-depth architecture has been implemented across the framework to protect the host, repository, secrets, and services:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Defense-in-Depth Model                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
      ┌────────────────────────────────┼────────────────────────────────┐
      │                                │                                │
      ▼                                ▼                                ▼
[Path Sandboxing]              [Safe Git Staging]              [Secret Redaction]
- validate_safe_path()         - is_forbidden_staging_file()   - SecretMaskingFilter
- Rejects ../ traversal        - scan_file_for_secrets()       - Scrubs logs and traces
- Blocks .git / workflows      - Halts on keys, PATs, .env     - Masks sk-*, ghp_*, db URLs
      │                                │                                │
      └────────────────────────────────┼────────────────────────────────┘
                                       │
      ┌────────────────────────────────┴────────────────────────────────┐
      │                                                                 │
      ▼                                                                 ▼
[Localhost Binding]                                            [Web UI Access Control]
- docker-compose.yml                                           - 127.0.0.1 binding
- 127.0.0.1:13000 (Langfuse)                                   - Basic Auth (GRADIO_AUTH_USER)
- 127.0.0.1:15432 (PostgreSQL)                                 - Prevents unauthorized runs
```

### 1. Path Traversal & Safe File Writing Guardrail
- **Module:** [file_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/file_tools.py) & [execute_prompt.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/execute_prompt.py)
- **Functions:** `validate_safe_path(target_path, base_dir)` and `PathTraversalSecurityError`.
- **Enforcement:**
  - Verifies `target_path.resolve()` is strictly within `base_dir.resolve()`.
  - Rejects null bytes and traversal syntax (`..`).
  - Explicitly blocks writes targeting `.git/`, `.github/workflows/`, `.github/actions/`, `.env*`, and cryptographic key extensions (`.pem`, `.key`, `.pfx`, `.p12`).
  - Integrated into `write_generated_files` so rogue/hallucinated model paths cannot escape the repository or tamper with VCS hooks.

### 2. Selective Git Staging & Pre-Commit Secret Scanner
- **Module:** [git_ops.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/git_ops.py)
- **Functions:** `scan_file_for_secrets(file_path)`, `is_forbidden_staging_file(file_name)`, and `GitSecurityViolationError`.
- **Enforcement:**
  - Replaced blind `repo.git.add(A=True)` with selective staging of candidate files.
  - Automatically blocks staging of forbidden files (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials.json`).
  - Scans file contents for cryptographic private keys, OpenRouter API keys (`sk-or-v1-*`), Anthropic keys (`sk-ant-*`), and GitHub PATs (`ghp_*`).
  - Halts git commit and logs critical alerts if sensitive data is detected.

### 3. Sensitive Data Redaction in Logs and Traces
- **Module:** [src/homecare_agent/security/redaction.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/security/redaction.py)
- **Components:** `redact_secrets(text)` and `SecretMaskingFilter(logging.Filter)`.
- **Enforcement:**
  - Automatically scrubs known secret patterns: OpenRouter keys, Anthropic keys, generic API keys, GitHub tokens, Bearer tokens, private keys, and database passwords in connection strings.
  - Attached to console and file logging handlers in [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py).
  - Sanitizes trace metadata in [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py) so raw secrets are never persisted in Langfuse.

### 4. Docker Container Localhost Binding
- **Configuration:** [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml)
- **Enforcement:**
  - Port mappings for `homecare-agent` (`127.0.0.1:7860:7860`), `langfuse-server` (`127.0.0.1:13000:3000`), and `langfuse-db` (`127.0.0.1:${LANGFUSE_DB_PORT:-15432}:5432`) are bound explicitly to `127.0.0.1` rather than `0.0.0.0`, preventing exposure to the local network or external interfaces.

### 5. Web UI Access Control
- **Modules:** [config.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/config.py), [.env.example](file:///c:/WorkingFolder/homecare-af/.env.example), [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- **Enforcement:**
  - Added `GRADIO_AUTH_USER` and `GRADIO_AUTH_PASSWORD` configuration options.
  - Gradio server explicitly binds to `server_name="127.0.0.1"`.
  - HTTP Basic Authentication is automatically enforced when credentials are configured.

### 6. Automated Security Test Suite
- **Module:** [tests/test_security.py](file:///c:/WorkingFolder/homecare-af/tests/test_security.py)
- **Tests Added (13 test cases):**
  - `test_validate_safe_path_valid`: Verifies standard internal path resolution.
  - `test_validate_safe_path_traversal_blocked`: Verifies `../` directory traversal is rejected.
  - `test_validate_safe_path_forbidden_git_dir`: Verifies `.git/hooks` writes are blocked.
  - `test_validate_safe_path_forbidden_workflows`: Verifies `.github/workflows` writes are blocked.
  - `test_validate_safe_path_forbidden_env_files`: Verifies `.env` writes are blocked.
  - `test_validate_safe_path_forbidden_key_extensions`: Verifies `.key`/`.pem` writes are blocked.
  - `test_write_file_sandboxing`: Verifies `write_file` enforces base directory bounds.
  - `test_write_generated_files_blocks_path_traversal`: Verifies pipeline skips malicious file entries.
  - `test_is_forbidden_staging_file`: Verifies forbidden file matching.
  - `test_scan_file_for_secrets`: Verifies secret detection in file contents.
  - `test_redact_secrets`: Verifies token masking across text and database URLs.
  - `test_secret_masking_filter`: Verifies logging filter scrubs records.
  - `test_commit_and_push_halts_on_secret`: Verifies git staging halts when secrets are detected.

---

### Comprehensive Test Suite Status
All **70 unit tests** across the entire repository pass cleanly:
```bash
pytest tests/ -v
======================== 70 passed, 1 warning in 3.44s ========================
```

---

## 8. Locally Hosted LLM Support for Code Generation

Support for locally hosted OpenAI-compatible LLM servers (**Ollama**, **vLLM**, **LM Studio**, **LocalAI**) has been integrated as an optional, opt-in capability while fully retaining OpenRouter as the default cloud provider.

```
                                  ┌───────────────────────────────────┐
                                  │      Agentic Pipeline Nodes       │
                                  └─────────────────┬─────────────────┘
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      │                                                           │
                      ▼                                                           ▼
         [Architecture / Reviews]                                      [Code Generation Tier]
       - analyze_codebase                                            - execute_wave
       - generate_strategy / tactical / ADRs                         - write_files
       - review_architecture / code_review                           - apply_review_fixes
                      │                                                           │
                      ▼                                                           ▼
           ┌─────────────────────┐                                     ┌─────────────────────┐
           │     OpenRouter      │                                     │ Local LLM Server    │
           │ (Claude Sonnet/Opus)│                                     │ (Ollama / vLLM)     │
           │  https://openrouter │                                     │ http://localhost:...│
           └─────────────────────┘                                     └─────────────────────┘
```

### 1. Retention of OpenRouter as Default
- By default (`LOCAL_LLM_ENABLED=false`), all nodes run through OpenRouter exactly as configured.
- Existing configurations (`OPENROUTER_API_KEY`, `MODEL_ARCHITECTURE`, `MODEL_CODE`, `MODEL_REVIEW`) continue to function without changes.

### 2. Multi-Endpoint Provider Caching
- **Implementation:** [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)
- `_create_llm` supports custom `base_url`, `api_key`, and `timeout`.
- Models are cached under compound keys `model@base_url` (e.g. `qwen2.5-coder:32b@http://localhost:11434/v1` and `anthropic/claude-sonnet-4@https://openrouter.ai/api/v1`), allowing local and cloud endpoints to operate concurrently in hybrid mode.
- `resolve_llm_and_model_for_node` automatically directs code nodes (`execute_wave`, `write_files`, `apply_review_fixes`) to the local server when `local_llm_enabled=True`.

### 3. Supported Local Providers
- **Ollama:** `http://localhost:11434/v1` with models like `qwen2.5-coder:32b`, `deepseek-coder-v2`, `codellama`.
- **vLLM:** `http://localhost:8000/v1`
- **LM Studio:** `http://localhost:1234/v1`

### 4. CLI & Web UI Integration
- **CLI Options:**
  ```bash
  homecare-agent run --local-code --local-llm-url http://localhost:11434/v1 --local-llm-model qwen2.5-coder:32b
  ```
- **Web UI:** Toggle and configuration fields embedded inside the `Multi-Tier Model Configuration` accordion in [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py).

### 5. Automated Tests Added
- [test_local_llm.py](file:///c:/WorkingFolder/homecare-af/tests/test_local_llm.py):
  - `test_default_openrouter_routing_when_local_disabled`: Verifies OpenRouter handles all nodes by default.
  - `test_hybrid_routing_with_local_llm_for_code`: Verifies architecture stays on OpenRouter while code generation routes to Ollama.
  - `test_multi_endpoint_model_cache`: Verifies independent caching across distinct endpoints.
  - `test_state_overrides_for_local_llm`: Verifies runtime state overrides for model and URL.
  - `test_is_code_node_helper`: Verifies tier categorization.

**Test Results:** **70 passed in 3.44s** (`pytest tests/ -v`).

---

## 9. State Checkpointing & Resuming Execution from Step 4

To eliminate the need to re-run early steps (such as intake and codebase analysis) after an interruption, credit exhaustion, or failure, persistent state checkpointing and dynamic entry routing have been implemented.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              LangGraph Dynamic Entry Router                            │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
                           ┌───────────────────────────────────┐
                           │ resume_from_step in AgentState?   │
                           └───────┬───────────────────┬───────┘
                                   │ No                │ Yes (e.g. "generate_strategy")
                                   ▼                   ▼
                           ┌──────────────┐     ┌───────────────────────┐
                           │    Step 1    │     │   Step 4 (Resumed)    │
                           │intake_feature│     │   generate_strategy   │
                           └──────┬───────┘     └───────────┬───────────┘
                                  │                         │
                                  ▼                         ▼
                            [Steps 2 & 3]        [Tactical, ADRs, Waves]
```

### 1. Persistent Checkpoint Store (`.homecare/checkpoints/`)
- **Implementation:** [checkpoint.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/checkpoint.py)
- After every node completes, [CheckpointManager](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/checkpoint.py) automatically saves the active [AgentState](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/state.py) as JSON in `.homecare/checkpoints/<trace_id>.json`.
- When an execution halts or crashes after Step 3 (`analyze_codebase`), the saved checkpoint preserves:
  - Feature name and requirements description
  - Clarification answers
  - Full codebase AST, symbols, and architectural patterns (`codebase_analysis`)
  - List of completed steps: `["intake_feature", "analyze_codebase"]`

### 2. 14-Step Sequencing & Smart Next-Step Resolution
Steps are numbered 1 through 14:
1. `intake_feature`
2. `ask_clarifications`
3. `analyze_codebase`
4. `generate_strategy`
5. `generate_tactical_plan`
6. `generate_adrs`
7. `generate_agentic_prompts`
8. `review_architecture`
9. `create_branch`
10. `execute_wave`
11. `run_e2e_tests`
12. `generate_manual_test_doc`
13. `create_pr`
14. `notify_ready_for_merge`

- `resolve_next_step(state)` automatically detects the next step after the highest completed step. If Step 3 finished, it automatically resolves to **Step 4 (`generate_strategy`)**!
- Numeric input (`4` or `"4"`) and canonical names (`"generate_strategy"`) are supported interchangeably.

### 3. Dynamic Entry Routing in LangGraph
- **Implementation:** [main_graph.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/main_graph.py)
- Replaced the static edge `START → intake_feature` with a conditional router `_route_entry`.
- If `resume_from_step` is set (e.g. `generate_strategy`), execution immediately starts at that node. All context from earlier steps is injected directly from the loaded checkpoint.

### 4. CLI Commands
```bash
# List all saved checkpoints on disk
homecare-agent resume --list

# Automatically resume the most recent run from its next pending step (Step 4)
homecare-agent resume

# Resume a specific run from Step 4 (using step number or node name)
homecare-agent resume --trace-id <trace_id> --from-step 4
homecare-agent resume --trace-id <trace_id> --from-step generate_strategy

# Or resume directly using the run command
homecare-agent run --resume <trace_id> --from-step 4
```

### 5. Web UI Integration
- Added a **"🔄 Resume Pipeline"** tab in [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py).
- Dropdown auto-populates saved runs from `.homecare/checkpoints/` showing the feature name and last completed step.
- Step dropdown defaults to `Step 4: generate_strategy`, allowing instantaneous one-click resumption.

### 6. Test Suite & Verification
- Created [test_checkpoint_resume.py](file:///c:/WorkingFolder/homecare-af/tests/test_checkpoint_resume.py):
  - `test_step_resolution_by_number_and_name`: Validates bi-directional resolution for all 14 steps.
  - `test_resolve_next_step_after_step_3_failure`: Proves automatic detection of Step 4 after Step 3 stops.
  - `test_resolve_next_step_explicit_override`: Validates explicit step overrides.
  - `test_checkpoint_save_and_load`: Tests full state JSON serialization and deserialization.
  - `test_checkpoint_listing_and_latest`: Validates listing runs ordered newest-first.
  - `test_langgraph_resumes_directly_from_step_4`: Verifies that Steps 1 and 3 are never called and execution starts directly at Step 4.
  - `test_cli_resume_list_empty` & `test_cli_resume_list_with_data`: Validates CLI table output.
- **Test Suite Results:** **78 passed in 3.81s** (`pytest tests/ -v`).






