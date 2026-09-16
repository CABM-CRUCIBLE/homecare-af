# Automated Langfuse Project Provisioning & Single Workflow Trace ID

This plan implements two core capabilities:
1. **Automated Langfuse Initialization:** Auto-provisions the Langfuse organization, project, admin account, and API keys on container startup using credentials configured in `docker-compose.yml` and `.env` (without requiring manual web UI setup).
2. **Unified Single Trace ID:** Guarantees that an entire LangGraph workflow run shares exactly one OpenTelemetry-compliant `trace_id` (32-character hex) so all nodes, spans, generations, and token metrics are grouped into a single hierarchical trace tree in Langfuse.

## User Review Required

> [!IMPORTANT]
> - **Langfuse Web UI Access:** Langfuse will run at `http://localhost:13000`.
> - **Default Credentials (configurable via `.env`):**
>   - **Email/Username:** `admin@homecare.local` (or `LANGFUSE_INIT_USER_EMAIL`)
>   - **Password:** `HomeCareAdmin123!` (or `LANGFUSE_INIT_USER_PASSWORD`)
>   - **Public API Key:** `pk-lf-homecare-local` (or `LANGFUSE_PUBLIC_KEY`)
>   - **Secret API Key:** `sk-lf-homecare-local` (or `LANGFUSE_SECRET_KEY`)
> - **Database Persistence:** PostgreSQL data volume `langfuse_db_data` ensures credentials and trace history persist across container restarts.

## Proposed Changes

### Configuration & Docker Compose

#### [MODIFY] [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml)
- Update `langfuse-server` environment variables with Langfuse Headless Initialization variables:
  - `LANGFUSE_INIT_ORG_ID=${LANGFUSE_INIT_ORG_ID:-homecare-org}`
  - `LANGFUSE_INIT_ORG_NAME=${LANGFUSE_INIT_ORG_NAME:-HomeCare}`
  - `LANGFUSE_INIT_PROJECT_ID=${LANGFUSE_INIT_PROJECT_ID:-homecare}`
  - `LANGFUSE_INIT_PROJECT_NAME=${LANGFUSE_INIT_PROJECT_NAME:-HomeCare}`
  - `LANGFUSE_INIT_PROJECT_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY:-pk-lf-homecare-local}`
  - `LANGFUSE_INIT_PROJECT_SECRET_KEY=${LANGFUSE_SECRET_KEY:-sk-lf-homecare-local}`
  - `LANGFUSE_INIT_USER_EMAIL=${LANGFUSE_INIT_USER_EMAIL:-admin@homecare.local}`
  - `LANGFUSE_INIT_USER_NAME=${LANGFUSE_INIT_USER_NAME:-HomeCare Admin}`
  - `LANGFUSE_INIT_USER_PASSWORD=${LANGFUSE_INIT_USER_PASSWORD:-HomeCareAdmin123!}`
- Update `homecare-agent` service defaults:
  - `LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY:-pk-lf-homecare-local}`
  - `LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY:-sk-lf-homecare-local}`
  - `LANGFUSE_HOST=http://langfuse-server:3000`

#### [MODIFY] [.env](file:///c:/WorkingFolder/homecare-af/.env) and [.env.example](file:///c:/WorkingFolder/homecare-af/.env.example)
- Update default keys and host:
  - `LANGFUSE_PUBLIC_KEY=pk-lf-homecare-local`
  - `LANGFUSE_SECRET_KEY=sk-lf-homecare-local`
  - `LANGFUSE_HOST=http://localhost:13000`
- Add initialization credentials:
  - `LANGFUSE_INIT_ORG_ID=homecare-org`
  - `LANGFUSE_INIT_ORG_NAME=HomeCare`
  - `LANGFUSE_INIT_PROJECT_ID=homecare`
  - `LANGFUSE_INIT_PROJECT_NAME=HomeCare`
  - `LANGFUSE_INIT_USER_EMAIL=admin@homecare.local`
  - `LANGFUSE_INIT_USER_NAME=HomeCare Admin`
  - `LANGFUSE_INIT_USER_PASSWORD=HomeCareAdmin123!`

---

### Core Pipeline & Trace Propagation

#### [MODIFY] [state.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/state.py)
- Add `trace_id: str` to `AgentState`.

#### [MODIFY] [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)
- Update Langfuse initialization for modern Langfuse v4 (`from langfuse.langchain import CallbackHandler` with fallback).
- Initialize `self._langfuse_client = Langfuse(public_key=..., secret_key=..., host=...)`.
- Add `workflow_trace_id` state and `set_workflow_trace(trace_id: str)`.
- Add `get_langfuse_handler(trace_id: str | None = None) -> Any` returning a `CallbackHandler` configured with `trace_context={"trace_id": ...}` conforming to the OpenTelemetry 32-hex trace ID standard.
- In `ainvoke`, `ainvoke_with_vision`, and `invoke_sync`:
  - Accept `trace_id: str = ""` (falling back to `state_overrides.get("trace_id")` or `self._workflow_trace_id`).
  - Attach the execution callback handler configured with the unified `trace_id`.
  - Record `workflow_trace_id` in metadata.

#### [MODIFY] [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)
- In `run`:
  - Generate a 32-hex `trace_id = uuid.uuid4().hex`.
  - Configure `llm.set_workflow_trace(trace_id)`.
  - Put `trace_id` in `initial_state["trace_id"]`.
  - Display the Langfuse trace URL / trace ID in the console banner.
  - Pass the Langfuse callback handler to `graph.astream(..., config={"callbacks": [handler]})` so LangGraph node executions nest directly under the root trace.
- In `generate`:
  - Generate `trace_id` and configure `llm.set_workflow_trace(trace_id)`.

#### [MODIFY] [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- Generate a 32-hex `trace_id` on each pipeline invocation.
- Configure `llm.set_workflow_trace(trace_id)`.
- Display a clickable link in the Gradio status panel: `Langfuse Trace: http://localhost:13000/project/homecare/traces/{trace_id}`.

#### [MODIFY] Node implementations
- Verify that `state_overrides=state` or `trace_id=state.get("trace_id")` is passed across all nodes in `src/homecare_agent/graph/nodes/`.

---

### Verification Plan

### Automated Tests
- Run `pytest tests/ -v` to ensure existing 30 tests pass.
- Add new test suite `tests/test_tracing.py`:
  - Test valid 32-hex trace ID generation and formatting.
  - Test `LLMProvider.set_workflow_trace` and `get_langfuse_handler`.
  - Test trace ID propagation into `ainvoke` callbacks and metadata.
  - Test `AgentState` contains `trace_id`.

### Integration & Docker Verification
- Validate docker-compose syntax: `docker compose config`.
- Start the containers in background: `docker compose up -d langfuse-db langfuse-server`.
- Verify `langfuse-server` starts and logs indicate headless initialization completed.
- Test connection to `http://localhost:13000` and verify login with configured credentials.
