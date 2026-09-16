# Tactical Plan: {{ feature_name }}

**Document type:** Tactical plan  
**Author:** Enterprise Solution Architecture  
**Date:** {{ date }}  
**Status:** Proposed  
**Companion:** [STRATEGY-{{ feature_slug }}.md](STRATEGY-{{ feature_slug }}.md)  

---

## Table of Contents

1. [Entity Relationship Diagram](#1-entity-relationship-diagram)
2. [Database Schema Details](#2-database-schema-details)
3. [Status Vocabularies and State Machines](#3-status-vocabularies-and-state-machines)
4. [Migration Plan](#4-migration-plan)
5. [High-Level Design & Component Architecture](#5-high-level-design--component-architecture)
6. [API Endpoints & Contracts](#6-api-endpoints--contracts)
7. [Data Transfer Objects (DTOs)](#7-data-transfer-objects-dtos)
8. [Frontend Route and Component Map](#8-frontend-route-and-component-map)
9. [Work Package Breakdown by Waves](#9-work-package-breakdown-by-waves)
10. [Test Strategy & Test Suites](#10-test-strategy--test-suites)
11. [Observability & Error Handling](#11-observability--error-handling)
12. [Definition of Done](#12-definition-of-done)

---

## 1. Entity Relationship Diagram

```mermaid
{{ mermaid_er_diagram }}
```

---

## 2. Database Schema Details

{{ database_schema_tables }}

---

## 3. Status Vocabularies and State Machines

{{ state_machine_diagrams }}

---

## 4. Migration Plan

- **Framework:** EF Core Migrations
- **Naming Convention:** `Add{{ feature_pascal }}`
- **Rollback Strategy:** Down() migration scripts verified for zero data loss

---

## 5. High-Level Design & Component Architecture

{{ component_design }}

---

## 6. API Endpoints & Contracts

| Verb | Path | Controller | Authorization | Description |
| ---- | ---- | ---------- | ------------- | ----------- |
{{ api_endpoints_rows }}

---

## 7. Data Transfer Objects (DTOs)

{{ dtos_summary }}

---

## 8. Frontend Route and Component Map

| Route | Component / Page | Type | Description |
| ----- | ---------------- | ---- | ----------- |
{{ frontend_routes_rows }}

---

## 9. Work Package Breakdown by Waves

{{ work_packages_breakdown }}

---

## 10. Test Strategy & Test Suites

- **Unit Tests:** xUnit + FluentAssertions for backend; Vitest for frontend
- **E2E Tests:** Playwright POM test suites
- **Load Tests:** k6 threshold scripts for new endpoints

---

## 11. Observability & Error Handling

- Structured logs with `TenantId`, `UserId`, `TraceId`
- Global Exception Handler mapping domain errors to RFC 7807 Problem Details

---

## 12. Definition of Done

- [ ] All Work Packages in Waves executed and passing builds
- [ ] 100% unit tests pass with required coverage
- [ ] Clean Architecture layer boundaries strictly maintained
- [ ] Code review completed by automated Senior Architect agent with zero critical findings
- [ ] Pull request opened with comprehensive release notes
