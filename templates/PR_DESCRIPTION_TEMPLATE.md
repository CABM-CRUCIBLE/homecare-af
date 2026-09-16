# Pull Request: {{ feature_name }}

## Overview

{{ overview }}

## Architecture Reference

- **Strategy Document:** [STRATEGY-{{ feature_slug }}.md]({{ strategy_doc_path }})
- **Tactical Plan:** [TACTICAL-PLAN-{{ feature_slug }}.md]({{ tactical_plan_path }})
- **Architectural Review:** [Architecture_Review.md]({{ architecture_review_path }})

## Key Changes

### Backend (.NET Clean Architecture)
- **Domain:** {{ domain_changes }}
- **Application (CQRS / MediatR):** {{ application_changes }}
- **Infrastructure (EF Core / Persistence):** {{ infrastructure_changes }}
- **API (Controllers / Contracts):** {{ api_changes }}

### Frontend (Next.js App Router)
- **Routes & Pages:** {{ frontend_pages }}
- **Components & Hooks:** {{ frontend_components }}

## Verification & Test Results

| Test Type | Status | Passed | Failed | Details |
| --------- | ------ | ------ | ------ | ------- |
| **Backend Unit Tests (dotnet test)** | {{ backend_test_status }} | {{ backend_passed }} | {{ backend_failed }} | {{ backend_details }} |
| **Frontend Unit Tests (vitest)** | {{ frontend_test_status }} | {{ frontend_passed }} | {{ frontend_failed }} | {{ frontend_details }} |
| **E2E Tests (Playwright)** | {{ e2e_test_status }} | {{ e2e_passed }} | {{ e2e_failed }} | {{ e2e_details }} |
| **Load Tests (k6)** | {{ load_test_status }} | - | - | {{ load_test_details }} |

## Security & Compliance Checklist

- [x] Hard multi-tenant isolation enforced in all queries
- [x] No PII in logs (HIPAA compliant)
- [x] Input validation via FluentValidation / Zod
- [x] RFC 7807 problem details error handling
- [x] Zero `any` types in TypeScript
- [x] Full code implementations (no placeholders)
