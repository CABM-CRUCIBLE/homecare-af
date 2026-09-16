# Implementation Plan: Local LLM Support for Code Generation

Enable the HomeCare Agentic Framework to route code generation work packages to locally hosted, OpenAI-compatible LLM servers (e.g., **Ollama**, **vLLM**, **LM Studio**, **LocalAI**) as an **optional configuration**, while **fully retaining OpenRouter as the primary default provider**.

> [!IMPORTANT]
> **OpenRouter Retention Guarantee:**
> - **100% Backward Compatible:** OpenRouter remains the default provider (`LOCAL_LLM_ENABLED=false`). If local LLM settings are not enabled, the framework continues using OpenRouter for every step exactly as it does today.
> - **No Deprecation:** All existing OpenRouter settings (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `MODEL_ARCHITECTURE`, `MODEL_CODE`, `MODEL_REVIEW`, `NODE_MODELS`) remain fully active and supported.
> - **Flexible Hybrid Option:** You can choose between:
>   1. **Pure OpenRouter (Default):** All nodes (architecture, code, review) run via OpenRouter.
>   2. **Hybrid:** Architecture & reviews run via OpenRouter (e.g., Claude 3.7 Sonnet), while code generation runs via local LLM (e.g., Ollama).
>   3. **Pure Local:** Run entirely on local endpoints if desired.

## Proposed Changes

### 1. Configuration
#### [MODIFY] [config.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/config.py)
- Add Local LLM settings to `Settings`:
  - `local_llm_enabled: bool = False`
  - `local_llm_base_url: str = "http://localhost:11434/v1"` (defaults to Ollama's OpenAI-compatible endpoint)
  - `local_llm_api_key: str = "ollama"` (dummy key for servers that don't require auth)
  - `local_llm_code_model: str = "qwen2.5-coder:32b"` (standard high-performing local coder model)
  - `local_llm_for_code: bool = True` (automatically routes code nodes to local LLM when enabled)
  - `local_llm_timeout: float = 300.0`
- Update `is_code_node(node_name: str) -> bool` helper.

#### [MODIFY] [.env.example](file:///c:/WorkingFolder/homecare-af/.env.example)
- Add documentation for local LLMs with configurations for:
  - **Ollama** (`http://localhost:11434/v1`)
  - **vLLM** (`http://localhost:8000/v1`)
  - **LM Studio** (`http://localhost:1234/v1`)

---

### 2. LLM Provider Multi-Endpoint Routing
#### [MODIFY] [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)
- Update `_create_llm(model, base_url=None, api_key=None, timeout=None)` to support arbitrary base URLs and keys.
- Update cache key format to `f"{clean_model}@{effective_base_url}"` so local and cloud models can coexist simultaneously.
- Enhance `get_llm_for_node(node_name, model_override=..., state_overrides=...)`:
  - If `node_name` is a code generation node (`execute_wave`, `write_files`, `apply_review_fixes`) and `local_llm_enabled` is active:
    - Route to `local_llm_base_url`, `local_llm_api_key`, and `local_llm_code_model`.
  - Otherwise, route to configured OpenRouter model.
- Return both resolved LLM and model name for accurate Langfuse tracing metadata.

---

### 3. CLI & Web UI Integration
#### [MODIFY] [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)
- Add CLI arguments to `run` and `generate` commands:
  - `--local-code / --no-local-code`: Toggle local LLM for code generation.
  - `--local-llm-url`: Specify local base URL (default: `http://localhost:11434/v1`).
  - `--local-llm-model`: Specify local model name (e.g. `qwen2.5-coder:32b`, `deepseek-coder:33b`).

#### [MODIFY] [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- Add controls in the Gradio Web UI:
  - Checkbox: "Use Local LLM for Code Generation (Ollama / vLLM / LM Studio)"
  - Textboxes: "Local LLM Base URL" and "Local Code Model Name".

---

### 4. Verification & Testing
#### [NEW] [tests/test_local_llm.py](file:///c:/WorkingFolder/homecare-af/tests/test_local_llm.py)
- Test hybrid routing: architecture nodes route to OpenRouter, code nodes route to `local_llm_base_url`.
- Test model cache handles multiple endpoints without collision.
- Test CLI override propagation for local LLM settings.
- Run full test suite: `pytest tests/ -v`.

## User Review Required
> [!NOTE]
> The default configuration defaults to **Ollama** at `http://localhost:11434/v1` with `qwen2.5-coder:32b` or `deepseek-coder`, which are currently state-of-the-art open weights coding models. You can also point to vLLM (`http://localhost:8000/v1`) or LM Studio (`http://localhost:1234/v1`).
