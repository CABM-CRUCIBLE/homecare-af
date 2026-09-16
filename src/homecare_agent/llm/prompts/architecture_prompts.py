# Author: C A B M
# Date: 2026-09-17

"""Prompts for generating Architecture Strategy, Tactical Plans, and ADRs."""

STRATEGY_GENERATION_PROMPT = """\
You are a distinguished Enterprise Chief Architect authoring an official Strategy Document.

Feature: {feature_name}
Description: {feature_description}
Clarifications & Decided Context: {clarification_context}
Gap Analysis: {gap_analysis}

Write a comprehensive, publication-grade STRATEGY document following the HomeCare Architecture standards:
Include:
1. Executive Summary & Problem Statement
2. Business Capabilities & Value Proposition
3. Architectural Guiding Principles (Clean Architecture, SOLID, Tenant Isolation, Auditability)
4. Target State Architecture & Layer Responsibilities
5. Domain Model & Entity Relationship (with Mermaid ER diagram)
6. CQRS Command/Query Specifications & Data Flows (with Mermaid Sequence diagram)
7. Security, Compliance & HIPAA Controls (RBAC, Encryption at rest/transit, Audit logging)
8. Resilience, Scalability & Failure Modes
9. Observability (Structured logging, Tracing, Metrics)

Write in clear, formal, rigorous Markdown.
"""

TACTICAL_PLAN_PROMPT = """\
You are a Principal Engineering Lead creating an implementation Tactical Plan.

Feature: {feature_name}
Strategy Context: {strategy_summary}
Gap Analysis: {gap_analysis}

Generate a comprehensive TACTICAL PLAN breaking down the implementation into sequenced, dependency-ordered WAVES:
Each Wave must specify:
- Wave Name & Objective
- Exact Work Packages (WP-01, WP-02...)
- For each WP:
  - Component / Layer (Domain, Application, Infrastructure, API, Frontend, Tests)
  - Target files to create or modify (with exact namespace/paths)
  - Clear prerequisites & dependencies
  - Verification checklist (dotnet build, unit tests, linters)

Wave Order:
Wave 1: Domain Entities & Enums (Zero dependencies)
Wave 2: Application Layer (Commands, Queries, Validators, DTOs)
Wave 3: Infrastructure (EF Core configurations, Repositories, Migrations)
Wave 4: API Layer (Controllers, Middlewares, Endpoints)
Wave 5: Frontend UI (Components, Hooks, Pages, API Clients)
Wave 6: Integration & E2E Tests (Playwright, k6)

Provide clear, unambiguous file paths and technical constraints.
"""

ADR_GENERATION_PROMPT = """\
You are a Software Architect writing an Architectural Decision Record (ADR).

Feature: {feature_name}
Decision Topic: {decision_topic}
Decision Context: {decision_context}
Options Considered: {options_considered}

Produce a formal ADR in standard MADR format:
# ADR-{adr_number}: {title}

## Status
{status} (Proposed / Accepted)

## Context
Describe the architectural forces, technical constraints, and business requirements.

## Decision
State the exact architectural choice made and technical justification.

## Consequences
### Positive Consequences
- ...
### Negative Consequences / Trade-offs
- ...
### Mitigations
- ...

## Compliance & Security Impact
- Detail impact on Clean Architecture compliance, tenant safety, or HIPAA regulations.
"""
