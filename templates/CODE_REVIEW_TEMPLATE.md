# Code Review: Pull Request #{{ pr_number }} — {{ pr_title }}

## Review Metadata

| Field | Value |
| --- | --- |
| **Review Date** | {{ date }} |
| **Reviewer** | Senior Automated Code Reviewer (Clean Architecture Specialist) |
| **Feature Branch** | `{{ branch_name }}` |
| **Base Branch** | `{{ base_branch }}` |
| **Total Files Changed** | {{ total_files }} |

---

## 1. Executive Summary & Verdict

> [!NOTE]
> **Verdict: {{ verdict }}** (APPROVED / CHANGES_REQUESTED)
> {{ summary }}

---

## 2. Standards Checklist

- [ ] **Clean Architecture:** Strict boundary adherence (Domain has no outer deps, Application only references Domain).
- [ ] **Completeness:** 100% full implementation without placeholder comments (`// TODO`, `// ... rest of code`).
- [ ] **Type Safety:** Nullable reference types enabled in C#; strictly zero `any` types in TypeScript.
- [ ] **Documentation:** XML documentation on all public C# types/methods; TSDoc comments on exported frontend components/hooks.
- [ ] **Security:** Input validated with FluentValidation/Zod; tenant isolation applied in all queries.
- [ ] **Error Handling:** Global exception handling middleware compliant with RFC 7807 Problem Details.
- [ ] **Observability:** Structured logging with no PII exposure.
- [ ] **Testing:** Unit tests cover happy path, negative path, and boundary conditions.

---

## 3. Detailed Findings

{{ findings_table_or_list }}

---

## 4. Remediation Instructions

{{ remediation_instructions }}
