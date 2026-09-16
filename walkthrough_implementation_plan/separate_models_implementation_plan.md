# Implementation Plan: Per-Node & Multi-Tier LLM Model Routing

Allow different LLM models to be assigned to individual nodes and phases of the LangGraph workflow, specifically enabling **high-reasoning, higher-cost models** (e.g., Claude 3.5 Sonnet, Claude Opus, GPT-4o) for Architecture Analysis, Strategy, Tactical Planning, and Code Reviews, while routing actual **code generation and test implementation** (Work Package execution) to **medium- or low-cost models** (e.g., DeepSeek-Coder, Claude Haiku, Llama-3.3-70B, GPT-4o-mini).

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **Tier-Based Defaults + Fine-Grained Node Overrides:**
>    - Role-based configuration:
>      - `MODEL_ARCHITECTURE`: Used for Codebase Analysis, Strategy, Tactical Plan, ADR generation (defaults to `OPENROUTER_MODEL`).
>      - `MODEL_CODE`: Used for Work Package code synthesis and test generation (defaults to `MODEL_ARCHITECTURE`).
>      - `MODEL_REVIEW`: Used for Pre-implementation Architecture Review and PR Code Review (defaults to `MODEL_ARCHITECTURE`).
>      - `MODEL_VISION`: Used for Wireframe screenshot analysis (defaults to `OPENROUTER_VISION_MODEL`).
>    - Granular node override map: `NODE_MODELS` (e.g. `{"execute_wave": "deepseek/deepseek-coder", "review_architecture": "anthropic/claude-opus-4"}`).
> 2. **Model Caching in `LLMProvider`:**
>    - Lazily instantiates and caches `ChatOpenAI` instances per model identifier so there is no overhead or memory leak when switching between models across nodes.
> 3. **CLI & Web UI Integration:**
>    - CLI adds `--model-arch` and `--model-code` flags to `homecare-agent run`.
>    - Web UI adds model selectors for Architecture and Code Generation in the settings and feature request intake tabs.

---

## Proposed Changes

### 1. Configuration & Settings

#### [MODIFY] [config.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/config.py)
- Add settings:
  - `model_architecture: str = Field(default="", description="High-reasoning model for architecture analysis, strategy, tactical plan, and ADRs")`
  - `model_code: str = Field(default="", description="Medium/low-cost model for work package code generation and tests")`
  - `model_review: str = Field(default="", description="High-reasoning model for architecture and PR code reviews")`
  - `node_models: dict[str, str] = Field(default_factory=dict, description="Fine-grained node name to model map")`
- Add helper method `get_model_for_node(node_name: str) -> str` resolving the model with fallback hierarchy.

---

### 2. LLM Provider

#### [MODIFY] [provider.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/llm/provider.py)
- Implement `self._model_cache: dict[str, ChatOpenAI] = {}` to cache model instances.
- Update `ainvoke`:
  - Add parameter `node_name: str = ""`.
  - Automatically lookup model for node if `model_override` is not explicitly passed.
  - Tag Langfuse traces with the effective model name and node role.
- Add `get_llm_for_node(node_name: str) -> ChatOpenAI`.

---

### 3. Graph State & Nodes

#### [MODIFY] [state.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/state.py)
- Add optional state fields:
  - `model_architecture: str`
  - `model_code: str`
  - `model_review: str`
  - `node_models: dict[str, str]`
  (Enables overriding models per execution run).

#### [MODIFY] [analyze.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/analyze.py)
- Pass `node_name="analyze_codebase"` to `llm.ainvoke(...)`.

#### [MODIFY] [architect.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/architect.py)
- Pass `node_name="generate_strategy"`, `node_name="generate_tactical_plan"`, `node_name="generate_adrs"` respectively.

#### [MODIFY] [execute_prompt.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/execute_prompt.py)
- Pass `node_name="execute_wave"` to `llm.ainvoke(...)` so it automatically invokes the `model_code` (e.g. DeepSeek-Coder / Haiku).

#### [MODIFY] [review_arch.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/review_arch.py) and [code_review.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/code_review.py)
- Pass `node_name="review_architecture"` and `node_name="perform_code_review"`.

---

### 4. CLI, Web UI & Scaffolding

#### [MODIFY] [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)
- Add CLI options to `homecare-agent run`:
  - `--model-arch`: High-reasoning model for analysis and architecture.
  - `--model-code`: Cost-effective model for code generation.
  - `--model-review`: Model for senior architect reviews.

#### [MODIFY] [cli.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/cli.py)
- Update interactive setup and run prompts to allow configuring architecture model and code generation model separately.

#### [MODIFY] [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- Add UI dropdowns/inputs for Architecture Model and Code Generation Model.

#### [MODIFY] [.env.example](file:///c:/WorkingFolder/homecare-af/.env.example) & [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml) & [docs/CONFIGURATION.md](file:///c:/WorkingFolder/homecare-af/docs/CONFIGURATION.md)
- Add `MODEL_ARCHITECTURE`, `MODEL_CODE`, `MODEL_REVIEW`, and `NODE_MODELS`.

---

## Verification Plan

### Automated Tests
- Add unit tests in `tests/test_provider.py` or `tests/test_graph.py` verifying:
  - `Settings.get_model_for_node()` fallback logic for each node category.
  - `LLMProvider` properly retrieves and caches different models for `analyze_codebase` vs `execute_wave`.
  - Full pytest suite execution: `pytest tests/ -v`.

### Manual CLI Verification
- Run `homecare-agent --help` and verify `--model-arch` and `--model-code` options.
