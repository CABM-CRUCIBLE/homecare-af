# Architecture Review: {{ feature_name }}

## Metadata

| Field | Value |
| --- | --- |
| **Review Date** | {{ date }} |
| **Reviewer Role** | Senior Solution Architect (20+ years) |
| **Review Type** | Pre-implementation architecture review |
| **Scope** | STRATEGY, TACTICAL PLAN, ADRs, AGENTIC PROMPTS |
| **Method** | Verification against enterprise standards, Clean Architecture rules, and codebase evidence |

---

## 1. Executive Verdict

> [!IMPORTANT]
> **Recommendation: {{ verdict }}** (APPROVED / APPROVED_WITH_RECOMMENDATIONS / REJECTED)
> {{ verdict_summary }}

---

## 2. Architectural Benchmark Scorecard

| Dimension | Score (1-10) | Evaluation & Evidence |
| --------- | ------------ | --------------------- |
| **Clean Architecture & SOLID** | {{ score_clean_arch }}/10 | {{ notes_clean_arch }} |
| **Multi-Tenant Isolation & Safety** | {{ score_multi_tenancy }}/10 | {{ notes_multi_tenancy }} |
| **Concurrency & Integrity** | {{ score_concurrency }}/10 | {{ notes_concurrency }} |
| **Security & HIPAA / PII Controls** | {{ score_security }}/10 | {{ notes_security }} |
| **Observability & Error Handling** | {{ score_observability }}/10 | {{ notes_observability }} |
| **Testability & Validation** | {{ score_testability }}/10 | {{ notes_testability }} |

---

## 3. Critical & High-Severity Findings

{{ critical_findings }}

---

## 4. Architectural Recommendations

{{ architectural_recommendations }}

---

## 5. Execution Gate Recommendation

- **Ready to proceed to Wave implementation?** {{ ready_to_proceed }}
- **Conditions / Required Action Items:**
{{ required_actions }}
