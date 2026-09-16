# Pipeline Resumption & State Checkpointing Architecture (Resume from Step 4)

## Overview
When running an automated agentic workflow, failures can occur at any stage (e.g., API rate limits, network timeouts, credit exhaustion, or runtime errors). If the framework stops after **Step 3 (`analyze_codebase`)**, re-running from **Step 1 (`intake_feature`)** is wasteful, expensive, and time-consuming.

This implementation provides:
1. **Automated State Checkpointing**: Persists the full `AgentState` to JSON on disk (`.homecare/checkpoints/<trace_id>.json`) after every completed pipeline step.
2. **Dynamic Graph Entry Point**: Enables LangGraph's `START` node to route conditionally to any step (e.g., `generate_strategy` for Step 4) when resuming.
3. **Smart Step Sequencing**: Maps numeric steps (1–14) and node names bi-directionally, allowing auto-detection of the next step (e.g., if Step 3 succeeded, auto-resume at Step 4) or explicit overrides (`--from-step 4` or `--from-step generate_strategy`).
4. **CLI & Web UI Commands**:
   - `homecare-agent resume [--trace-id <id>] [--from-step <step_or_number>]`
   - `homecare-agent run --resume [trace_id]`
   - Web UI "Resume Run" control in Gradio.

---

## Pipeline Step Mapping

The 14 canonical steps in the pipeline:

| Step # | Node Name | Description | Required Prior State |
|---|---|---|---|
| **1** | `intake_feature` | Intake & specification analysis | Feature name, description |
| **2** | `ask_clarifications` | Interactive Q&A loop | Clarification questions |
| **3** | `analyze_codebase` | Ast/grep & pattern analysis | Target repo path |
| **4** | `generate_strategy` | High-level architectural strategy | `codebase_analysis`, `feature_description` |
| **5** | `generate_tactical_plan` | Wave breakdown & work packages | `strategy_document` |
| **6** | `generate_adrs` | Architecture Decision Records | `tactical_plan`, `strategy_document` |
| **7** | `generate_agentic_prompts` | Prompt engineering & file matrix | `tactical_plan`, `adr_documents` |
| **8** | `review_architecture` | Multi-agent arch review loop | Architecture docs |
| **9** | `create_branch` | Git feature branch creation | `branch_name`, `feature_name` |
| **10** | `execute_wave` | Code generation, write files, unit tests | `work_packages`, `standing_instructions` |
| **11** | `run_e2e_tests` | End-to-end and load testing | Committed code branch |
| **12** | `generate_manual_test_doc` | QA manual testing guides | Committed test suite |
| **13** | `create_pr` | PR creation & AI code review | Feature branch pushed to remote |
| **14** | `notify_ready_for_merge` | Review summary & team notification | Approved PR review |

---

## Implemented Components

### 1. Checkpoint Manager (`src/homecare_agent/graph/checkpoint.py`)
- Real-time disk persistence in `.homecare/checkpoints/<trace_id>.json`.
- Safe JSON serialization for complex types and LangChain messages.
- Automatic next-step resolution (`resolve_next_step`) detecting Step 4 when Step 3 finishes.

### 2. Dynamic Routing (`src/homecare_agent/graph/main_graph.py`)
- Replaced static `START -> intake_feature` with `_route_entry` conditional edge.
- Directly routes `START -> generate_strategy` (or any other step) without re-executing previous steps.

### 3. CLI Integration (`src/homecare_agent/main.py`)
- Added `homecare-agent resume [--trace-id <id>] [--from-step <step_or_num>] [--list]`.
- Added `--resume` and `--from-step` flags to `homecare-agent run`.

### 4. Web UI Integration (`src/homecare_agent/ui/web.py`)
- Added "Resume Pipeline" tab in Gradio interface with checkpoint dropdown and step selector.

### 5. Automated Tests (`tests/test_checkpoint_resume.py`)
- 8 tests verifying serialization, step mapping, LangGraph dynamic entry starting at Step 4, and CLI options.
