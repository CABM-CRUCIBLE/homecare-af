# Strategy: {{ feature_name }}

**Document type:** Strategy plan  
**Author:** Enterprise Solution Architecture  
**Date:** {{ date }}  
**Status:** Proposed  

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Current-State Assessment](#2-current-state-assessment)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Constraints](#5-constraints)
6. [Assumptions](#6-assumptions)
7. [Strategic Position & Architecture](#7-strategic-position--architecture)
8. [Domain Model & Entity Relationships](#8-domain-model--entity-relationships)
9. [Sequence Diagrams & Workflows](#9-sequence-diagrams--workflows)
10. [C4 Component & Container View](#10-c4-component--container-view)
11. [Security, Privacy & HIPAA Controls](#11-security-privacy--hipaa-controls)
12. [Open Questions & Trade-offs](#12-open-questions--trade-offs)
13. [Risk Register & Mitigations](#13-risk-register--mitigations)
14. [Execution Gate](#14-execution-gate)

---

## 1. Purpose and Scope

### 1.1 Business Objective
{{ business_objective }}

### 1.2 In Scope
{{ in_scope_items }}

### 1.3 Out of Scope
{{ out_of_scope_items }}

---

## 2. Current-State Assessment

### 2.1 Existing Solution Context
{{ current_state_analysis }}

### 2.2 Reusable Assets and Gaps
{{ reusable_assets_and_gaps }}

---

## 3. Functional Requirements

{{ functional_requirements }}

---

## 4. Non-Functional Requirements

- **Performance & Latency:** p95 response time < 250ms for API endpoints; sub-second page rendering via RSC.
- **Scalability & Concurrency:** Pessimistic/Optimistic row-level locking with concurrency tokens for state transitions.
- **Availability:** 99.9% uptime with graceful degradation on third-party service outages.
- **Auditability:** Complete, tamper-evident audit logs capturing User ID, Tenant ID, Timestamp, and State Delta.

---

## 5. Constraints

- **Architecture:** Must adhere to Clean Architecture with strict inward dependency flow (`Domain` <- `Application` <- `Infrastructure` / `Api`).
- **Platform:** Backend (.NET 8/9, EF Core, MediatR, FluentValidation), Frontend (Next.js App Router, TypeScript, React Server Components).
- **Multi-Tenancy:** Hard multi-tenant isolation; cross-tenant data leaks constitute critical compliance violations.

---

## 6. Assumptions

{{ assumptions }}

---

## 7. Strategic Position & Architecture

{{ architectural_principles }}

---

## 8. Domain Model & Entity Relationships

```mermaid
{{ mermaid_er_diagram }}
```

---

## 9. Sequence Diagrams & Workflows

```mermaid
{{ mermaid_sequence_diagram }}
```

---

## 10. C4 Component & Container View

{{ c4_diagrams }}

---

## 11. Security, Privacy & HIPAA Controls

- **Authentication & RBAC:** JWT claim validation; role and permission policies enforced on all endpoints.
- **Tenant Isolation:** Enforced via scoped DbContext global query filters keyed to `TenantId`.
- **Encryption:** AES-256 for sensitive PII data at rest; TLS 1.3 in transit.
- **Audit Trail:** Immutable audit records stored with non-repudiation.

---

## 12. Open Questions & Trade-offs

{{ open_questions }}

---

## 13. Risk Register & Mitigations

| Risk ID | Description | Impact | Probability | Mitigation |
| ------- | ----------- | ------ | ----------- | ---------- |
{{ risk_register_rows }}

---

## 14. Execution Gate

- [ ] All architectural decisions documented in ADRs
- [ ] Tactical implementation plan approved
- [ ] Schema migration strategy verified
- [ ] Test strategy aligned
