# HomeCare Agentic Framework — Implementation Tasks

## Phase 1: Project Scaffolding
- [/] Initialize Python project with `uv` and `pyproject.toml`
- [ ] Create directory structure
- [ ] Create `.env.example`
- [ ] Create `README.md`

## Phase 2: Core Models & Configuration
- [ ] `src/homecare_agent/config.py` — Configuration & environment
- [ ] `src/homecare_agent/models/` — Pydantic data models (feature_request, architecture, work_package, test_result, review)

## Phase 3: Knowledge Base
- [ ] `src/homecare_agent/knowledge/architecture.py` — Architecture patterns
- [ ] `src/homecare_agent/knowledge/conventions.py` — Enterprise standards
- [ ] `src/homecare_agent/knowledge/templates.py` — Document templates

## Phase 4: LLM Provider
- [ ] `src/homecare_agent/llm/provider.py` — OpenRouter BYOK client
- [ ] `src/homecare_agent/llm/prompts/` — All prompt templates

## Phase 5: Tools
- [ ] `src/homecare_agent/tools/github_tools.py` — GitHub API
- [ ] `src/homecare_agent/tools/git_tools.py` — Local git ops
- [ ] `src/homecare_agent/tools/file_tools.py` — File operations
- [ ] `src/homecare_agent/tools/codebase_tools.py` — AST analysis
- [ ] `src/homecare_agent/tools/build_tools.py` — Build & test
- [ ] `src/homecare_agent/tools/image_tools.py` — Wireframe analysis
- [ ] `src/homecare_agent/tools/mermaid_tools.py` — Diagram generation

## Phase 6: Graph (LangGraph)
- [ ] `src/homecare_agent/graph/state.py` — Graph state
- [ ] `src/homecare_agent/graph/nodes/` — All graph nodes
- [ ] `src/homecare_agent/graph/edges/routing.py` — Conditional routing
- [ ] `src/homecare_agent/graph/main_graph.py` — Top-level graph

## Phase 7: UI
- [ ] `src/homecare_agent/ui/cli.py` — Rich CLI interface
- [ ] `src/homecare_agent/ui/web.py` — Gradio web UI
- [ ] `src/homecare_agent/main.py` — CLI entry point

## Phase 8: Document Templates
- [ ] `templates/STRATEGY_TEMPLATE.md`
- [ ] `templates/TACTICAL_PLAN_TEMPLATE.md`
- [ ] `templates/ADR_TEMPLATE.md`
- [ ] `templates/AGENTIC_PROMPTS_TEMPLATE.md`
- [ ] `templates/ARCHITECTURE_REVIEW_TEMPLATE.md`
- [ ] `templates/CODE_REVIEW_TEMPLATE.md`
- [ ] `templates/PR_DESCRIPTION_TEMPLATE.md`
- [ ] `templates/MANUAL_TESTING_GUIDE_TEMPLATE.md`
- [ ] `templates/STANDING_INSTRUCTIONS.md`

## Phase 9: Testing
- [ ] `tests/test_graph.py`
- [ ] `tests/test_nodes.py`
- [ ] `tests/test_tools.py`
- [ ] `tests/test_prompts.py`

## Phase 10: Docker & Docs
- [ ] `Dockerfile`
- [ ] `docker-compose.yml`
- [ ] `docs/ARCHITECTURE.md`
- [ ] `docs/CONFIGURATION.md`
- [ ] `docs/WORKFLOW.md`
