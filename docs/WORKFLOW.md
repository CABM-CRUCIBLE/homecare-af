# Workflow: 18-Step Enterprise Feature Delivery

This document describes the complete 18-step automated engineering workflow orchestrated by the HomeCare Agentic Framework.

---

## 1. Feature Intake (`intake_feature`)
- Ingests natural language feature description and optional UI wireframe images.
- Invokes vision model to identify UI components, interactions, and data fields.
- Formulates initial requirements and determines if human clarification is needed.

## 2. Interactive Clarification (`ask_clarifications`)
- Presents targeted questions covering business rules, state machines, and data models.
- Collects answers via Rich CLI interactive prompts or Gradio web forms.
- Re-evaluates requirements completeness.

## 3. Deep Codebase Analysis (`analyze_codebase`)
- Scans .NET solution, projects, and Clean Architecture layers.
- Discovers existing domain entities, base classes, and DbContext configurations.
- Maps API controllers, route attributes, and MediatR handlers.
- Detects frontend routes (Next.js App Router) and shared UI components.

## 4. Gap Analysis
- Contrasts existing codebase assets against new feature requirements.
- Catalogs gaps in Domain, Application, Infrastructure, API, and Frontend.

## 5. Architecture Strategy Generation (`generate_strategy`)
- Produces publication-grade `STRATEGY.md`.
- Generates Mermaid ER diagrams and Sequence diagrams.
- Documents C4 container/component views and compliance controls.

## 6. Tactical Plan Generation (`generate_tactical_plan`)
- Produces `TACTICAL-PLAN.md`.
- Groups changes into dependency-ordered execution Waves:
  - **Wave 1:** Domain Entities & Enums (zero outer dependencies)
  - **Wave 2:** Application CQRS (Commands, Queries, Handlers, Validators)
  - **Wave 3:** Infrastructure (EF Core Configurations, Repositories, Migrations)
  - **Wave 4:** API Layer (Controllers, Route Middlewares)
  - **Wave 5:** Frontend UI (Components, Hooks, Server/Client Pages)
  - **Wave 6:** Test Suites (Integration, E2E, Load)

## 7. Architectural Decision Records (`generate_adrs`)
- Produces formal MADR-format ADRs for all significant architectural choices.

## 8. Architecture Review (`review_architecture`)
- Evaluates documents with a 20+ year Senior Architect persona.
- Scores Clean Architecture, Multi-tenancy, Security, and Error Handling.
- If rejected, triggers revision loop with actionable feedback.

## 9. Branch Creation (`create_branch`)
- Derives branch name `feature/<kebab-name>`.
- Creates and pushes branch to remote repository.

## 10. Wave-Based Code Generation (`execute_wave`)
- For each Work Package in the current wave:
  - Injects Standing Instructions (no truncation, strict typing, Clean Architecture).
  - Synthesizes 100% complete files.
  - Writes files to disk.
  - Runs `dotnet build` / `npm run build` to validate syntax and compilation.
  - Retries on compilation failure up to 3 times with compiler error feedback.

## 11. Unit Test Generation & Validation (`run_unit_tests`)
- Generates xUnit tests for backend business logic.
- Generates Vitest tests for frontend components.
- Executes tests (`dotnet test`, `npm test`) and asserts 100% pass rate.

## 12. Incremental Wave Commit (`commit_wave`)
- Stages all changes for the completed wave.
- Commits with structured message referencing the Work Package.
- Pushes to remote feature branch.

## 13. E2E Test Suite Generation (`run_e2e_tests`)
- Produces Playwright test specs using Page Object Model (POM).

## 14. Performance Load Test Generation (`run_load_tests`)
- Produces k6 load testing scripts with p95 response time and error rate thresholds.

## 15. Manual Testing Guide Generation (`generate_manual_test_doc`)
- Produces step-by-step instructions for developers and QA engineers.

## 16. Documentation Commit (`commit_documentation`)
- Commits all generated architectural documentation, test specs, and guides.

## 17. Pull Request Creation (`create_pull_request`)
- Opens GitHub PR against main branch.
- Generates rich markdown description with test results and architecture references.

## 18. Senior Architect Code Review & Merge Gate (`perform_code_review`)
- Reviews line-by-line PR diff against enterprise code quality guidelines.
- Checks type safety (no `any`), exception handling (RFC 7807), and HIPAA compliance.
- Submits review comments.
- Notifies team that PR is ready for final human sign-off.
