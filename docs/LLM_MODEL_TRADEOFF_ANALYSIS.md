# LLM Model Selection & Trade-Off Analysis

**Document Type:** Architectural Evaluation & Cost-Benefit Study  
**System:** HomeCare Agentic Framework  
**Target Architecture:** Clean Architecture, .NET 8/9, Next.js App Router, PostgreSQL  
**Routing Mechanism:** OpenRouter (BYOK) with Langfuse Tracing  

---

## Executive Summary

The **HomeCare Agentic Framework** divides the software engineering lifecycle into two distinct computational workloads with fundamentally differing requirements:

1. **Architecture & Design Stage (High Cognitive Load, Low Token Volume):** Involves deep codebase AST analysis, domain entity synthesis, CQRS pipeline design, multi-tenant security boundary enforcement, Mermaid ER/sequence diagram generation, and formal Architectural Decision Records (ADRs).
2. **Code Generation & Test Implementation Stage (Moderate Cognitive Load, High Token Volume):** Involves synthesizing 100% complete source code files across Domain, Application, Infrastructure, API, and Frontend layers, followed by xUnit, Vitest, Playwright, and k6 test suites.

Using a single model for both workloads results in either **inferior architectural coherence** (if using a low-cost code model for design) or **untenable API costs and latency** (if using a flagship reasoning model for full-file code generation).

This document presents a comprehensive, multi-dimensional trade-off matrix evaluating frontier and open-weight models across reasoning depth, coding benchmark accuracy, instruction compliance (particularly the non-negotiable **zero-truncation invariant**), context windows, token pricing, and throughput.

---

## 1. Workload Profiles & Evaluation Criteria

| Dimension | Architecture Analysis & Review | Code Generation & Testing |
| :--- | :--- | :--- |
| **Workflow Nodes** | `intake_feature`, `analyze_codebase`, `generate_strategy`, `generate_tactical_plan`, `generate_adrs`, `review_architecture` | `execute_wave`, `run_unit_tests`, `run_e2e_tests`, `run_load_tests`, `generate_manual_test_doc`, `apply_review_fixes` |
| **Typical In/Out Tokens** | 40,000 input tokens / 8,000 output tokens | 15,000 input tokens / 25,000 output tokens per wave |
| **Frequency per Feature** | 1–2 iterations | 3–6 waves (multiple concurrent work packages) |
| **Primary Requirement** | Conceptual integrity, structural reasoning, trade-off evaluation | Syntax completeness, strict type adherence, zero truncation, framework idiom compliance |
| **Failure Mode** | Flawed boundaries, leaky multi-tenancy, security oversights | Compilation error, truncated `// ... rest of code`, missing imports |
| **Tolerance for Latency** | High (quality > speed) | Low (developers waiting for wave compilation) |

---

## 2. Comprehensive Model Trade-Off Matrix

The following models are evaluated across key dimensions on OpenRouter as of Q1 2026:

| Model Identifier | Provider | Primary Strength | Context Window | Input Cost ($ / 1M tokens) | Output Cost ($ / 1M tokens) | Speed (tokens/sec) | SWE-bench / Coding Grade | Recommended Tier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`anthropic/claude-sonnet-4`** | Anthropic | Architectural reasoning, Clean Arch adherence, Vision | 200k | $3.00 | $15.00 | ~70 t/s | **S+ (Exceptional)** | **Architecture & Review (Primary)** |
| **`anthropic/claude-opus-4`** | Anthropic | Peak nuanced reasoning, safety & compliance | 200k | $15.00 | $75.00 | ~30 t/s | **S+ (Peak)** | **Architecture Review (High-Stakes)** |
| **`openai/gpt-4o`** | OpenAI | Rapid multimodal vision, structured JSON | 128k | $2.50 | $10.00 | ~95 t/s | **S (Excellent)** | **Vision & Intake / Fast Arch** |
| **`openai/o3-mini`** | OpenAI | Chain-of-thought algorithmic validation | 128k | $1.10 | $4.40 | ~60 t/s | **S (High Logic)** | **Algorithm / State Machine Design** |
| **`deepseek/deepseek-coder`** (V2/V3) | DeepSeek | Unbeatable cost-to-performance, complete C#/TS | 64k–128k | $0.14 | $0.28 | ~80 t/s | **A+ (Near S-tier code)** | **Code Generation (Primary)** |
| **`anthropic/claude-3.5-haiku`** | Anthropic | Speed, strict instruction following | 200k | $0.80 | $4.00 | ~120 t/s | **A (Very Solid)** | **Code Generation (Fast / Medium Cost)** |
| **`meta-llama/llama-3.3-70b-instruct`** | Meta / Open | Open weight, self-hostable, strong syntax | 128k | $0.12 | $0.30 | ~90 t/s | **A- (Good)** | **Code Generation (Open-Weight)** |
| **`qwen/qwen-2.5-coder-32b-instruct`** | Alibaba / Open | Exceptional code completion for size | 32k–128k | $0.07 | $0.16 | ~100 t/s | **A (Strong Code)** | **High-Throughput Unit Tests** |
| **`google/gemini-2.5-pro`** | Google | Enormous 2M context, whole-repo ingestion | 2M | $1.25 | $5.00 | ~65 t/s | **S- (Great)** | **Whole-Repo Analysis** |

---

## 3. In-Depth Architectural Evaluation

### 3.1 Tier 1: Architecture & Design Models

#### 1. Anthropic Claude Sonnet 4 / 3.5 Sonnet (`anthropic/claude-sonnet-4`)
* **Why it excels for Architecture:**
  - **Clean Architecture Adherence:** Demonstrates unmatched respect for architectural layers. It strictly prevents `Domain` from referencing outer projects and isolates MediatR queries from persistence details.
  - **Mermaid Generation:** Produces syntactically valid `erDiagram`, `sequenceDiagram`, and `flowchart` definitions without markdown hallucinations or unescaped bracket errors.
  - **Defect Detection:** Capable of diagnosing subtle architectural smells such as dual-write aggregate divergence, fail-open tenant resolution, and missing optimistic concurrency tokens (`xmin`).
  - **Vision:** Flawlessly reads complex multi-column wireframes, identifying navigation sidebars, data tables, filter toolbars, and modal actions.
* **Trade-offs:** Output token cost ($15/M) is prohibitive if used to generate boilerplate C# entities or repetitive test cases across multiple waves.

#### 2. OpenAI GPT-4o (`openai/gpt-4o`)
* **Why it excels for Intake & Vision:**
  - Fast response times (~95 t/s) with exceptional structured JSON schema output adherence.
  - High accuracy in OCR and spatial comprehension for wireframes and screenshot mockups.
* **Trade-offs:** Can occasionally generate overly generic code designs if not steered with rigorous standing instructions. Tends to omit complete boilerplate unless explicitly instructed.

#### 3. Google Gemini 2.5 Pro (`google/gemini-2.5-pro`)
* **Why it excels for Large-Scale Codebase Ingestion:**
  - Its **2 Million token context window** enables ingesting the entire backend and frontend codebase in a single prompt without chunking or search approximations.
* **Trade-offs:** Higher variability in Mermaid diagram formatting compared to Claude Sonnet; occasionally misses fine-grained C# naming guidelines (e.g. private field `_camelCase`).

---

### 3.2 Tier 2: Code Generation & Test Implementation Models

#### 1. DeepSeek-Coder / DeepSeek-V3 (`deepseek/deepseek-coder`)
* **Why it excels for Work Package Synthesis:**
  - **Economics:** At **$0.14 / $0.28 per 1M tokens**, it is approximately **50x cheaper** than Claude Sonnet for output generation.
  - **Code Completeness:** Uncannily compliant with "NO TRUNCATION" instructions. Writes complete 600-line C# files with full properties, FluentValidation rules, and EF Core configurations without substituting `// ... rest of implementation`.
  - **Syntax Accuracy:** Exceptional understanding of modern C# 12 / .NET 8 (records, primary constructors, collection expressions, nullable reference types) and TypeScript / Next.js 15 App Router conventions.
* **Trade-offs:** Context window is 64k–128k (sufficient for individual work packages, but not suited for multi-project architectural context). Slower reasoning on non-coding domain modeling.

#### 2. Anthropic Claude 3.5 Haiku (`anthropic/claude-3.5-haiku`)
* **Why it excels as a Balanced Alternative:**
  - Blazing generation speed (~120 tokens/sec) with strong adherence to enterprise prompt constraints.
  - 200k context window allows providing substantial surrounding context alongside the work package prompt.
  - Cost ($0.80 / $4.00) is reasonable for enterprise automated workflows.
* **Trade-offs:** More expensive than DeepSeek; slightly more prone to brevity in large files unless repeatedly reinforced with `no_truncation` instructions.

#### 3. Qwen 2.5 Coder 32B Instruct (`qwen/qwen-2.5-coder-32b-instruct`)
* **Why it excels for Test Suite Generation:**
  - Specifically fine-tuned on test generation, mocking, and assertion libraries (xUnit, Moq, Vitest).
  - Extremely cost effective ($0.07 / $0.16) for high-volume automated test synthesis across waves.
* **Trade-offs:** Smaller active parameter count means it can occasionally hallucinate method names from external services if not explicitly provided in the prompt context.

---

## 4. Financial & Latency Impact Model (Dual-Tier vs. Single-Tier)

To understand the concrete operational savings, we model a typical enterprise feature implementation:
- **Feature Scope:** e.g., *Vendor Payouts & Accounting Architecture*
- **Architecture Workload:** ~120k input tokens, ~18k output tokens (Intake, Codebase Scan, Strategy, Tactical Plan, 4 ADRs, Review)
- **Code Generation Workload:** 4 Waves × 4 Work Packages = 16 Work Packages.
  - Average prompt context: ~12k input tokens × 16 = 192k input tokens.
  - Average generated files: ~2,500 lines per wave = 45k output tokens × 4 waves = 180k output tokens.

### Strategy Comparison:

| Strategy | Architecture Model | Code Gen Model | Estimated API Cost | Generation Time | Architectural Rigor | Code Quality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy A: Pure Flagship** | Claude Sonnet 4 | Claude Sonnet 4 | **$3.89** | 52 mins | **S+ (Peak)** | **S+** |
| **Strategy B: Pure Budget** | DeepSeek-Coder | DeepSeek-Coder | **$0.09** | 24 mins | **B (Risky)** | **A** |
| **Strategy C: Dual-Tier (Recommended)** | **Claude Sonnet 4** | **DeepSeek-Coder** | **$0.68** | **29 mins** | **S+ (Peak)** | **S+ / A+** |
| **Strategy D: Anthropic-Only Tier** | **Claude Sonnet 4** | **Claude 3.5 Haiku** | **$1.41** | **26 mins** | **S+ (Peak)** | **S+ / A** |

> [!TIP]
> **Key Finding:** Strategy C (**Dual-Tier: Sonnet 4 for Architecture + DeepSeek for Code**) delivers **82.5% cost reduction** compared to pure flagship execution while maintaining **100% of the architectural rigor, Clean Architecture compliance, and security review depth**.

---

## 5. Decision Matrix & Recommended Deployment Profiles

### Profile 1: Enterprise Production Default (Best Value & Rigor)
* **Architecture & Review:** `anthropic/claude-sonnet-4`
* **Code Generation:** `deepseek/deepseek-coder`
* **Wireframe Vision:** `anthropic/claude-sonnet-4`
* **Configuration:**
  ```env
  MODEL_ARCHITECTURE=anthropic/claude-sonnet-4
  MODEL_CODE=deepseek/deepseek-coder
  MODEL_REVIEW=anthropic/claude-sonnet-4
  OPENROUTER_VISION_MODEL=anthropic/claude-sonnet-4
  ```

### Profile 2: Single-Vendor Anthropic Stack (Maximum Predictability)
* Ideal for enterprise environments with existing Anthropic compliance agreements or strict OpenRouter routing rules.
* **Architecture & Review:** `anthropic/claude-sonnet-4`
* **Code Generation:** `anthropic/claude-3.5-haiku`
* **Configuration:**
  ```env
  MODEL_ARCHITECTURE=anthropic/claude-sonnet-4
  MODEL_CODE=anthropic/claude-3.5-haiku
  MODEL_REVIEW=anthropic/claude-sonnet-4
  ```

### Profile 3: Critical System-Level Refactoring (Highest Cognitive Assurance)
* Ideal for core payment gateways, HIPAA patient record encryption, or complex state machine migrations.
* **Architecture:** `anthropic/claude-opus-4`
* **Review:** `anthropic/claude-opus-4`
* **Code Generation:** `anthropic/claude-sonnet-4`
* **Configuration:**
  ```env
  MODEL_ARCHITECTURE=anthropic/claude-opus-4
  MODEL_CODE=anthropic/claude-sonnet-4
  MODEL_REVIEW=anthropic/claude-opus-4
  ```

### Profile 4: Offline / Self-Hosted / Sovereign Cloud
* Ideal for environments requiring on-premise execution with vLLM or Ollama.
* **Architecture & Strategy:** `meta-llama/llama-3.3-70b-instruct`
* **Code Generation:** `qwen/qwen-2.5-coder-32b-instruct`

---

## 6. How to Configure Model Tiers in the Framework

### Via Environment Variables (`.env`)
```bash
MODEL_ARCHITECTURE=anthropic/claude-sonnet-4
MODEL_CODE=deepseek/deepseek-coder
MODEL_REVIEW=anthropic/claude-sonnet-4
```

### Via CLI Execution
```bash
homecare-agent run \
  --name "Vendor Payouts Workflow" \
  --model-arch "anthropic/claude-sonnet-4" \
  --model-code "deepseek/deepseek-coder" \
  --model-review "anthropic/claude-sonnet-4"
```

### Via Granular Node Overrides (Code or Environment)
```json
NODE_MODELS={
  "analyze_codebase": "google/gemini-2.5-pro",
  "generate_strategy": "anthropic/claude-sonnet-4",
  "review_architecture": "anthropic/claude-opus-4",
  "execute_wave": "deepseek/deepseek-coder",
  "run_unit_tests": "qwen/qwen-2.5-coder-32b-instruct",
  "perform_code_review": "anthropic/claude-sonnet-4"
}
```

---

## 7. Conclusion & Governance Recommendation

1. **Enforce Dual-Tier Routing as Standard:** All developers should default to Profile 1 (`MODEL_ARCHITECTURE=anthropic/claude-sonnet-4` and `MODEL_CODE=deepseek/deepseek-coder`).
2. **Never Compromise Architecture Tier:** Do not downgrade `MODEL_ARCHITECTURE` below Claude Sonnet or GPT-4o. Flawed architecture decisions cause systemic refactoring costs that far exceed API savings.
3. **Automate Build-Break Guardrails:** Because lower-cost code models may occasionally misname a namespace or class member, the framework's automated `dotnet build` and `npm test` retry loops provide the deterministic safety net needed to run budget code models with high confidence.
