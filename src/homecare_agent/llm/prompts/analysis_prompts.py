"""Prompts for codebase and gap analysis."""

CODEBASE_ANALYSIS_PROMPT = """\
You are a Principal Software Architect analyzing an enterprise repository for an upcoming feature implementation.

Codebase Overview:
{codebase_summary}

Target Feature:
{feature_name}: {feature_description}

Provide a deep technical assessment covering:
1. Solution and module breakdown (Clean Architecture layers, project references).
2. Existing domain entities and DB mappings relevant to this domain.
3. Relevant CQRS Commands, Queries, Handlers, and MediatR pipelines.
4. Controllers, API route patterns, and DTO contracts.
5. Frontend route patterns, state management, and reusable UI components.
6. Established conventions for validation (FluentValidation), logging (Serilog), and exceptions.

Output valid JSON matching:
{{
  "affected_layers": ["Domain", "Application", "Infrastructure", "Api", "Frontend"],
  "existing_related_entities": ["Entity1", "Entity2"],
  "existing_patterns": {{
    "cqrs": true,
    "repository_pattern": true,
    "tenant_isolation": "Header-based X-Tenant-Id"
  }},
  "reuse_opportunities": ["ServiceA", "SharedComponentB"]
}}
"""

GAP_ANALYSIS_PROMPT = """\
You are a Senior Architect evaluating what new components must be created versus modified.

Feature Name: {feature_name}
Existing Codebase State:
{codebase_analysis}

Requirements & Answers:
{requirements_and_answers}

Produce a detailed Gap Analysis identifying:
1. Brand new entities, value objects, and enums needed in Domain.
2. New CQRS commands/queries and validators needed in Application.
3. EF Core configurations, DB migrations, or external client adapters needed in Infrastructure.
4. API controllers, endpoints, and DTOs in API layer.
5. Pages, routes, hooks, and UI components needed in Frontend.
6. Testing suites needed (Unit, Integration, E2E, Load).

Output your response as structured JSON with keys:
"domain_gaps", "application_gaps", "infrastructure_gaps", "api_gaps", "frontend_gaps", "testing_gaps".
"""
