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
- Ran full test suite including new test file `tests/test_tracing.py`:
  ```bash
  pytest tests/ -v
  ```
- **Results:** 40 passed in 1.92s (100% passing).
