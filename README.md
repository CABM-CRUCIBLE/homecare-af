# HomeCare Agentic Framework

> **Automated End-to-End Feature Development Pipeline for Enterprise Clean Architecture Platforms**

The **HomeCare Agentic Framework** is an autonomous engineering system powered by **LangGraph**, **OpenRouter (BYOK)**, **Local LLM Support (Ollama/vLLM/LM Studio)**, and **Langfuse Tracing**. It transforms natural language feature requests and UI wireframes into production-grade enterprise software following strict Clean Architecture, CQRS, and HIPAA/multi-tenant isolation standards.

---

## Table of Contents

- [Key Features](#key-features)
- [Workflow & Pipeline Topology](#workflow--pipeline-topology)
  - [The 14 Canonical Pipeline Steps](#the-14-canonical-pipeline-steps)
- [Installation & Setup](#installation--setup)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository & Setup Virtual Environment](#1-clone-repository--setup-virtual-environment)
  - [2. Install Dependencies](#2-install-dependencies)
- [Configuration Reference](#configuration-reference)
  - [Environment Variables (.env)](#environment-variables-env)
  - [Multi-Tier Model Routing Matrix](#multi-tier-model-routing-matrix)
  - [Optional Local LLM Setup (Zero Token Cost)](#optional-local-llm-setup-zero-token-cost)
- [Execution Instructions](#execution-instructions)
  - [1. Interactive Setup Wizard](#1-interactive-setup-wizard)
  - [2. Running the Full Pipeline via CLI](#2-running-the-full-pipeline-via-cli)
  - [3. Pipeline Resumption (Step 4 & Any Step)](#3-pipeline-resumption-step-4--any-step)
  - [4. Gradio Web Interface](#4-gradio-web-interface)
  - [5. Architecture Document Generation Only](#5-architecture-document-generation-only)
  - [6. Docker Compose Observability & Deployment](#6-docker-compose-observability--deployment)
- [Automated Testing & Quality Assurance](#automated-testing--quality-assurance)
- [Project Structure](#project-structure)
- [Architecture & Design Documentation](#architecture--design-documentation)
- [License](#license)

---

## Key Features

- **Bring Your Own Key (BYOK):** Seamless OpenRouter integration allowing arbitrary selection of frontier reasoning models (Claude Sonnet 4, Claude Opus, GPT-4o, DeepSeek, etc.).
- **Multi-Tier Model Routing:** Route complex system architecture planning to high-reasoning models while directing high-volume code synthesis and tests to cost-effective models.
- **Local LLM Execution for Code Generation:** Zero-token-cost local execution for code synthesis and test generation using Ollama, vLLM, or LM Studio (e.g. `qwen2.5-coder:32b`, `deepseek-coder`), while keeping high-reasoning models on OpenRouter for architecture.
- **State Checkpointing & Resumption (Resume from Step 4):** Automatic disk persistence after every pipeline step (`.homecare/checkpoints/`) with SHA-256 tamper detection and atomic writes. If interrupted or halted after Step 3 (`analyze_codebase`), resume directly from Step 4 (`generate_strategy`) without repeating earlier steps.
- **Automated Observability (Langfuse):** Self-provisioned headless local Langfuse container with OpenTelemetry-compliant 32-character hex `trace_id` linking all LangGraph nodes, spans, and LLM generations.
- **Multimodal UI Intake:** Accepts UI mockups and wireframes, automatically extracting UI components, route requirements, and entity structures.
- **Strict Clean Architecture & Enterprise Standards:** Enforces strict boundary separation (Domain, Application, Infrastructure, API, Frontend), zero placeholders, complete code generation, and audit logging.
- **Enterprise Guardrails & Resilience:**
  - **Circuit-Breaker Error Halting:** Sentinel routing halts pipeline progression immediately if critical documents (Strategy, Tactical Plan) fail to generate, preventing cascading token waste.
  - **Thread-Safe LLM Budgeting:** Unified concurrency-safe budget tracker (`MAX_LLM_CALLS_PER_RUN`).
  - **HTTP 402/Credit Fail-Fast:** Immediate termination on credit exhaustion with exponential backoff for transient rate limits.
  - **Path Traversal Sandboxing:** Strict validation (`validate_safe_path`) preventing access to parent paths, VCS dirs, GitHub workflows, or secrets.
  - **Secret Scanning & Redaction:** Pre-commit AST/regex inspection (`scan_file_for_secrets`, `SecretMaskingFilter`) preventing secrets from entering git staging or logs.
  - **Secure Network Binding:** Docker services bound strictly to `127.0.0.1` preventing inadvertent external exposure.
  - **Gradio Authentication:** Configurable HTTP basic authentication for browser interface.
- **Dual Interface:** Interactive Rich terminal CLI with live progress tracking or browser-based Gradio 5.0 Web UI with live streaming.
- **Automated Pull Requests & Review:** Opens GitHub PRs, commits code wave-by-wave, and performs automated code reviews with a Senior Architect persona.
- **Architecture & Visual Resource Archival:** Automatically persists all architectural documents (`STRATEGY.md`, `TACTICAL-PLAN.md`, `adrs/`, `MANUAL_TEST_GUIDE.md`) and wireframes (`Resources/`) into `docs/architecture/<feature-slug>/` and commits them to Git immediately on branch creation.

---

## Workflow & Pipeline Topology

```mermaid
flowchart TD
    A[1. Feature Intake & Wireframes] --> B[2. Clarification Loop]
    B --> C[3. Deep Codebase Analysis]
    C --> D[4. Strategy Generation]
    D --> E[5. Tactical Plan Generation]
    E --> F[6. Architectural Decision Records ADRs]
    F --> G[7. Agentic Prompts & File Ownership]
    G --> H[8. Architecture Review Loop]
    H -->|Approved| I[9. Feature Branch & Docs Commit]
    H -->|Revisions Needed| D
    I --> J[10. Wave-based Code Execution & Unit Tests]
    J -->|More Waves| J
    J -->|Waves Complete| K[11. E2E & Load Test Suite Generation]
    K --> L[12. Manual QA Documentation]
    L --> M[13. GitHub Pull Request & Automated Code Review]
    M -->|Changes Requested| J
    M -->|Approved| N[14. Merge-Ready Notification]
```

### The 14 Canonical Pipeline Steps

| Step # | Node Name | Implementation Module | Description | Resumption Point |
|:---:|---|---|---|:---:|
| **1** | `intake_feature` | `nodes/intake.py` | Parses natural language requirements and wireframe images | Initial Entry |
| **2** | `ask_clarifications` | `nodes/clarification.py` | Interactive technical Q&A loop to eliminate ambiguities | Step 2 |
| **3** | `analyze_codebase` | `nodes/analyze.py` | AST/symbol analysis of Domain, CQRS, API, and Frontend | Step 3 |
| **4** | `generate_strategy` | `nodes/architect.py` | Produces enterprise `STRATEGY.md` with C4 views & diagrams | **Step 4 (Resume Point)** |
| **5** | `generate_tactical_plan` | `nodes/architect.py` | Produces `TACTICAL-PLAN.md` breaking work into waves | Step 5 |
| **6** | `generate_adrs` | `nodes/architect.py` | Drafts formal MADR-format architectural records | Step 6 |
| **7** | `generate_agentic_prompts` | `nodes/generate_prompts.py` | Prompts engineering & file ownership matrix | Step 7 |
| **8** | `review_architecture` | `nodes/review_arch.py` | Multi-agent review with a 20+ year Senior Architect persona | Step 8 |
| **9** | `create_branch` | `nodes/git_ops.py` | Creates branch & commits `docs/architecture/<slug>/` + visual resources | Step 9 |
| **10** | `execute_wave` | `nodes/execute_prompt.py` | Synthesizes complete code, writes files, runs unit tests | Step 10 |
| **11** | `run_e2e_tests` | `nodes/testing.py` | Generates & executes Playwright E2E and k6 load tests | Step 11 |
| **12** | `generate_manual_test_doc` | `nodes/documentation.py` | Writes `MANUAL_TEST_GUIDE.md` to feature docs directory | Step 12 |
| **13** | `create_pr` | `nodes/code_review.py` | Opens GitHub PR and performs automated line-by-line review | Step 13 |
| **14** | `notify_ready_for_merge` | `nodes/notifications.py` | Posts review comments and notifies team of merge readiness | Step 14 |

---

## Installation & Setup

### Prerequisites

| Component | Minimum Version | Notes |
|---|---|---|
| **Python** | `3.11+` | Python 3.11 is strongly recommended |
| **Git** | `2.30+` | Available in system `PATH` |
| **Docker & Docker Compose** | `Compose v2+` | Optional: Required for local Langfuse tracing & PostgreSQL |
| **.NET SDK** | `8.0` or `9.0` | Optional: Required when executing backend C# builds and unit tests |
| **Node.js** | `18.0+` | Optional: Required when building and testing frontend code |
| **Ollama / vLLM / LM Studio** | Any | Optional: Required only for zero-cost local code generation |

---

### 1. Clone Repository & Setup Virtual Environment

Clone the repository and create an isolated Python 3.11 virtual environment:

#### On Windows (PowerShell):
```powershell
# Clone the repository
git clone https://github.com/organization/homecare-af.git
cd homecare-af

# Create virtual environment with Python 3.11
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

#### On Linux / macOS (Bash):
```bash
# Clone the repository
git clone https://github.com/organization/homecare-af.git
cd homecare-af

# Create virtual environment with Python 3.11
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

---

### 2. Install Dependencies

Install the framework in editable mode with development dependencies:

```bash
# Upgrade pip and build tools
pip install --upgrade pip setuptools wheel

# Install framework with development & testing dependencies
pip install -e ".[dev]"
```

Verify that the CLI is installed and available:

```bash
homecare-agent --help
```

---

## Configuration Reference

### Environment Variables (.env)

Copy `.env.example` to `.env` in the repository root:

```bash
cp .env.example .env
```

Configure your `.env` parameters according to your workflow:

```env
# ==============================================================================
# 1. OpenRouter BYOK (Bring Your Own Key)
# ==============================================================================
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-sonnet-4
OPENROUTER_VISION_MODEL=anthropic/claude-sonnet-4
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ==============================================================================
# 2. Multi-Tier Model Routing
# ==============================================================================
# High-reasoning model for Architecture Analysis, Strategy & ADRs
MODEL_ARCHITECTURE=anthropic/claude-sonnet-4

# Cost-effective model for Work Package code synthesis & test generation
MODEL_CODE=deepseek/deepseek-coder

# Senior Architect reviewer persona model
MODEL_REVIEW=anthropic/claude-sonnet-4

# Optional: Granular per-node JSON overrides
# NODE_MODELS={"execute_wave":"deepseek/deepseek-coder","review_architecture":"anthropic/claude-opus-4"}

# Token limits & sampling temperature
MAX_TOKENS=16384
TEMPERATURE=0.1

# ==============================================================================
# 3. Local LLM Configuration (Optional: Ollama, vLLM, LM Studio)
# ==============================================================================
LOCAL_LLM_ENABLED=false
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_API_KEY=ollama
LOCAL_LLM_CODE_MODEL=qwen2.5-coder:32b
LOCAL_LLM_FOR_CODE=true
LOCAL_LLM_TIMEOUT=300.0

# ==============================================================================
# 4. Target Repository & GitHub Integration
# ==============================================================================
REPO_PATH=c:/WorkingFolder/HomeCare
REPO_URL=https://github.com/organization/HomeCare
REPO_DEFAULT_BRANCH=main

# GitHub Authentication: "pat" or "github_app"
GITHUB_AUTH_MODE=pat
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# If using GitHub App authentication:
# GITHUB_APP_ID=12345
# GITHUB_APP_PRIVATE_KEY_PATH=/path/to/key.pem
# GITHUB_APP_INSTALLATION_ID=67890

# ==============================================================================
# 5. Execution Strategy & Guardrails
# ==============================================================================
EXECUTION_MODE=parallel
MAX_PARALLEL_WORKERS=5
MAX_RETRIES=3
MAX_ARCH_ITERATIONS=3
MAX_CLARIFICATION_ITERATIONS=2
MAX_LLM_CALLS_PER_RUN=60
CLARIFICATION_MODE=cli

# ==============================================================================
# 6. Observability & Tracing (Langfuse)
# ==============================================================================
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:13000
LANGFUSE_PUBLIC_KEY=pk-lf-homecare-local
LANGFUSE_SECRET_KEY=sk-lf-homecare-local

# Langfuse Docker Provisioning Secrets (Generate with: openssl rand -hex 32)
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
NEXTAUTH_SECRET=changeme-nextauth-secret-32-chars-min
SALT=changeme-salt-min-16-chars
LANGFUSE_INIT_ORG_ID=homecare-org
LANGFUSE_INIT_ORG_NAME=HomeCare
LANGFUSE_INIT_PROJECT_ID=homecare
LANGFUSE_INIT_PROJECT_NAME=HomeCare
LANGFUSE_INIT_USER_EMAIL=admin@homecare.local
LANGFUSE_INIT_USER_NAME=HomeCare Admin
LANGFUSE_INIT_USER_PASSWORD=HomeCareAdmin123!

# ==============================================================================
# 7. UI & Server Settings
# ==============================================================================
GRADIO_SERVER_NAME=127.0.0.1
GRADIO_SERVER_PORT=7860
GRADIO_AUTH_USER=admin
GRADIO_AUTH_PASSWORD=YourSecurePassword123!
# UI Theme: "crucible" (Executive Glassmorphism), "soft" (Gradio Soft), "default"
UI_THEME=crucible
LOG_LEVEL=INFO
LOG_FILE=logs/homecare-agent.log
```

---

### Multi-Tier Model Routing Matrix

The framework routes requests through a priority resolver:

| Tier | Default Variable | Sample OpenRouter Model | Local LLM Option | Purpose |
|---|---|---|---|---|
| **Architecture** | `MODEL_ARCHITECTURE` | `anthropic/claude-sonnet-4` | N/A (Cloud recommended) | Deep AST analysis, C4 strategy diagrams, tactical planning, ADR authoring |
| **Code Synthesis** | `MODEL_CODE` | `deepseek/deepseek-coder` | `qwen2.5-coder:32b` via Ollama | Work package code synthesis, unit tests, E2E scripts |
| **Review** | `MODEL_REVIEW` | `anthropic/claude-sonnet-4` | N/A | Senior Architect architecture review, GitHub PR code reviews |
| **Intake** | `MODEL_INTAKE` | `anthropic/claude-sonnet-4` | N/A | Feature requirement breakdown, wireframe parsing, clarification Q&A |

---

### Optional Local LLM Setup (Zero Token Cost)

To run code generation locally without incurring API token costs:

1. **Install and run Ollama:**
   ```bash
   ollama run qwen2.5-coder:32b
   ```
2. **Enable in `.env`:**
   ```env
   LOCAL_LLM_ENABLED=true
   LOCAL_LLM_BASE_URL=http://localhost:11434/v1
   LOCAL_LLM_CODE_MODEL=qwen2.5-coder:32b
   LOCAL_LLM_FOR_CODE=true
   ```
3. Or enable on-the-fly via CLI:
   ```bash
   homecare-agent run --local-code --local-llm-model "qwen2.5-coder:32b"
   ```

---

## Execution Instructions

### 1. Interactive Setup Wizard

If starting for the first time, run the interactive setup wizard to validate keys and create `.env`:

```bash
homecare-agent setup
```

---

### 2. Running the Full Pipeline via CLI

#### Interactive Mode:
```bash
homecare-agent run
```
You will be prompted for feature name, requirements description, and optional wireframe files.

#### Fully Scripted CLI Execution:
```bash
homecare-agent run \
  --name "Patient Medication Dispensation Queue" \
  --desc "Real-time nurse triage queue for controlled substance dispensation with audit log" \
  --repo "c:/WorkingFolder/HomeCare" \
  --wireframe "docs/mockups/med_dispensation.png" \
  --model-arch "anthropic/claude-sonnet-4" \
  --model-code "deepseek/deepseek-coder" \
  --log-level INFO
```

#### Hybrid Cloud Architecture + Local Code Generation:
```bash
homecare-agent run \
  --name "Caregiver Scheduling System" \
  --desc "Shift scheduling, conflict detection, and overtime calculation" \
  --repo "c:/WorkingFolder/HomeCare" \
  --local-code \
  --local-llm-url "http://localhost:11434/v1" \
  --local-llm-model "qwen2.5-coder:32b"
```

---

### 3. Pipeline Resumption (Step 4 & Any Step)

If a pipeline run halts or is interrupted (e.g., after Step 3 `analyze_codebase` due to rate limits or system maintenance), you **do not need to restart from Step 1**. All execution states and artifacts are checkpointed to `.homecare/checkpoints/` with SHA-256 integrity verification.

#### View All Checkpoints:
```bash
homecare-agent resume --list
```
Displays a table with trace IDs, feature names, last completed steps, and recommended resumption steps.

#### Auto-Resume Latest Run:
```bash
# Resumes automatically from the next pending step (e.g. Step 4: generate_strategy)
homecare-agent resume
```

#### Resume a Specific Trace ID from Step 4:
```bash
# By step number
homecare-agent resume --trace-id <trace_id> --from-step 4

# By node name
homecare-agent resume --trace-id <trace_id> --from-step generate_strategy

# Or resume using the run command
homecare-agent run --resume <trace_id> --from-step 4
```

---

### 4. Gradio Web Interface (Crucible — Executive Glassmorphism)

Launch the interactive executive workstation interface:

```bash
# Launch with default Crucible (Executive Glassmorphism) theme
homecare-agent web --port 7860

# Or launch with alternative swappable themes (e.g., 'soft' or 'default')
homecare-agent web --port 7860 --theme soft
```

Open your browser to `http://localhost:7860`. If `GRADIO_AUTH_USER` and `GRADIO_AUTH_PASSWORD` are configured, enter your credentials.

**Crucible Executive Workstation Layout:**
- **Compact Executive Header Strip (~48px):** Clean single-line header with Crucible branding, live system clock in `JetBrains Mono`, and inline telemetry badges (`14 Active Nodes`, `$0.00 Local Code`, `108 Passing Quality Gate`, and Sandboxed Target Workspace).
- **Inverted Visual Hierarchy (Primary Central Focus):**
  - **Highlighted Central Workstation (80% Width):** Large, prominent input form with glowing cyan borders, high-contrast labels, expanded requirements textarea, model configurations, and a prominent `Launch Autonomous Pipeline` CTA. Includes 6 core tabs (Feature Request, Clarification, Architecture Studio, Execution Engine with live stream, Code Review, and 1-Click Checkpoint Resumption).
  - **Compact Telemetry & Mission Dock (20% Width):** Lightweight right-hand intelligence dock with mission directives, resource usage meters (CPU, LLM Gateway, Host RAM), and live activity feed.

---

### 5. Architecture Document Generation Only

To generate architecture documents (`STRATEGY.md`, `TACTICAL-PLAN.md`, `ADR-xxx.md`) without creating Git branches or synthesizing code:

```bash
homecare-agent generate \
  --name "Patient Intake Flow" \
  --desc "Comprehensive patient intake with medical history forms" \
  --output ./Architecture/PatientIntake
```

---

### 6. Docker Compose Observability & Deployment

The framework includes a Docker Compose stack configured for zero-configuration observability with local security hardening (ports bound to `127.0.0.1`):

```bash
# Start the local Langfuse and PostgreSQL tracing stack
docker compose up -d
```

- **Langfuse Web UI:** `http://localhost:13000`
- **Default Admin Login:** `admin@homecare.local` / `HomeCareAdmin123!` (or value from `.env`)
- **PostgreSQL Database:** Bound to `127.0.0.1:15432` with parameterized credentials

To stop the containers:
```bash
docker compose down
```

---

## Automated Testing & Quality Assurance

## Automated Testing & Quality Assurance

The framework features a comprehensive test suite containing **108 unit, integration, and security tests** validating architecture guardrails, thread safety, state persistence, and UI theming.

### Run All Tests:
```bash
pytest
```

### Run with Verbose Output:
```bash
pytest -v
```

### Run Specific Test Modules:

| Test Target | Command | Purpose |
|---|---|---|
| **UI Theming & Crucible** | `pytest tests/test_theme.py -v` | Validates Executive Glassmorphism theme bundle, CSS, and theme switching |
| **Pipeline Resumption & Checkpoints** | `pytest tests/test_checkpoint_resume.py -v` | Validates Step 4 resumption, atomic writes, and SHA-256 tamper checks |
| **Local LLM Routing** | `pytest tests/test_local_llm.py -v` | Validates Ollama/vLLM endpoints, caching, and model overrides |
| **Security & Sandboxing** | `pytest tests/test_security.py -v` | Validates path traversal blocking, secret scanning, and redaction |
| **Priority Actions & Fixes** | `pytest tests/test_priority_actions.py -v` | Validates circuit breakers, budget locks, and state deduplication |
| **Architect Review Fixes** | `pytest tests/test_architect_review_fixes.py -v` | Validates level 1/2/3 review remediation |
| **Tracing & Langfuse** | `pytest tests/test_tracing.py -v` | Validates 32-char trace IDs and callback dispatch |

### Run with Test Coverage:
```bash
pytest --cov=src/homecare_agent tests/
```

---

## Project Structure

```
homecare-af/
├── src/homecare_agent/
│   ├── config.py                 # Pydantic Settings, multi-tier routing, env validation
│   ├── main.py                   # Typer CLI (run, resume, web, generate, setup)
│   ├── models/                   # Pydantic schemas (features, work packages, ADRs)
│   ├── knowledge/                # Clean architecture standards, rules, templates
│   ├── llm/                      # Multi-endpoint LLM provider with OpenRouter & local LLM
│   │   ├── provider.py           # Thread-safe budget counters, model caching, Langfuse
│   │   └── prompts/              # Enterprise prompts (architecture, intake, review)
│   ├── security/                 # Sandboxing & secret detection
│   │   └── redaction.py          # SecretMaskingFilter & credential regex scrubbers
│   ├── tools/                    # File sandboxing, git ops, build runners, mermaid
│   │   ├── build_tools.py        # .NET & Node.js build/test runners
│   │   ├── file_tools.py         # validate_safe_path, atomic writes
│   │   ├── json_utils.py         # Robust JSON extractor with markdown fence stripping
│   │   └── mermaid_tools.py      # Diagram synthesis & validation
│   ├── graph/                    # LangGraph StateGraph pipeline
│   │   ├── checkpoint.py         # CheckpointManager, SHA-256 verification, resume logic
│   │   ├── state.py              # AgentState TypedDict with deduplicating reducers
│   │   ├── main_graph.py         # StateGraph assembly, sentinels & dynamic entry points
│   │   ├── edges/                # Conditional routing, wave loops & guardrail limits
│   │   └── nodes/                # Individual node implementations
│   │       ├── intake.py         # Step 1: Feature intake & wireframe parsing
│   │       ├── clarification.py  # Step 2: Technical clarification Q&A loop
│   │       ├── analyze.py        # Step 3: Deep codebase AST & symbol analysis
│   │       ├── architect.py      # Steps 4-6: Strategy, Tactical Plan, ADR generation
│   │       ├── generate_prompts.py# Step 7: Prompt generation & file ownership
│   │       ├── review_arch.py    # Step 8: Senior Architect architecture review
│   │       ├── git_ops.py        # Step 9: Safe branch checkout & git commits
│   │       ├── execute_prompt.py # Step 10: Wave-based code synthesis & tests
│   │       ├── testing.py        # Step 11: Playwright E2E & k6 load tests
│   │       ├── documentation.py  # Step 12: QA manual test guides
│   │       ├── code_review.py    # Step 13: GitHub PR creation & automated review
│   │       └── notifications.py  # Step 14: Merge notifications & review comments
│   └── ui/                       # Presentation layers
│       ├── cli.py                # Rich banners, tables, and progress display
│       ├── theme.py              # Crucible Executive Glassmorphism & Theme Bundle registry
│       └── web.py                # 3-column workstation with live metrics & streaming
├── templates/                    # Enterprise document templates (Strategy, ADR, etc.)
├── tests/                        # Comprehensive test suite (108 tests)
├── docs/                         # Architectural blueprints & code review records
│   ├── ARCHITECTURE.md           # System architecture & LangGraph topology
│   ├── CONFIGURATION.md          # Full configuration and env variable guide
│   ├── WORKFLOW.md               # 14-step SDLC automation lifecycle
│   ├── LLM_MODEL_TRADEOFF_ANALYSIS.md # Model selection & cost trade-off analysis
│   ├── CODE_REVIEW_SENIOR_ARCHITECT.md # Level 1 Senior Architect code review
│   ├── CODE_REVIEW_SENIOR_ARCHITECT_LEVEL_2.md # Level 2 Senior Architect code review
│   └── CODE_REVIEW_SENIOR_ARCHITECT_LEVEL_3.md # Level 3 Senior Architect code review
├── docker-compose.yml            # Local Langfuse & PostgreSQL tracing stack
└── pyproject.toml                # Project metadata, dependencies & tool configs
```

---

## Architecture & Design Documentation

For deep technical dives, consult the dedicated architecture documentation in `docs/`:

- [System Architecture](docs/ARCHITECTURE.md): Comprehensive system architecture, data flow, and node topology.
- [Configuration Reference](docs/CONFIGURATION.md): Complete guide to environment variables, multi-tier models, and GitHub credentials.
- [Workflow Guide](docs/WORKFLOW.md): Detailed 14-step SDLC automation lifecycle.
- [LLM Model Trade-Off Analysis](docs/LLM_MODEL_TRADEOFF_ANALYSIS.md): Comprehensive benchmark and cost trade-off evaluation.
- [Senior Architect Review Level 1](docs/CODE_REVIEW_SENIOR_ARCHITECT.md): Baseline architectural review and findings.
- [Senior Architect Review Level 2](docs/CODE_REVIEW_SENIOR_ARCHITECT_LEVEL_2.md): Concurrency, sandboxing, and security hardening review.
- [Senior Architect Review Level 3](docs/CODE_REVIEW_SENIOR_ARCHITECT_LEVEL_3.md): Resilience, state integrity, and production-readiness review.

---

## License

Enterprise Proprietary — HomeCare Platform.
