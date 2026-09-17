# AI Coding Instructions: Enterprise Standards

**CRITICAL INSTRUCTION: RESPONSE FORMAT**
1. **NO TRUNCATION:** You must provide the **FULL code block** for every file requested. Do not use placeholders like `// ... rest of code` or `// ... implementation here`.
2. **ARCHITECTURAL RATIONALE:** Immediately following each major code block, you must include a brief **"Architectural Decision"** summary. Explain *why* a specific pattern, library, or structure was chosen (e.g., "Why use Strategy Pattern for Payments?", "Why specific indexing on this Entity?").

---

## 1. Code Quality & Patterns
* **SOLID Principles:** Strictly enforce Single Responsibility and Dependency Inversion.
* **Design Patterns:** Use appropriate patterns (Repository Pattern for DB access, Factory Pattern for Payments/Notification services, Strategy Pattern for distinct algorithm variants).
* **Clean Architecture:** Structure the backend into layers: `Domain` (Entities), `Application` (Interfaces/Logic), `Infrastructure` (DB/External Services), and `API` (Controllers).

## 2. Developer Experience (DX)
* **Comments:** Add XML comments (`/// <summary>`) for all public API endpoints and Interfaces. Add inline comments explaining *why* complex logic exists, not just *what* it does.
* **Naming Conventions:**
    * C#: `PascalCase` for classes/methods, `_camelCase` for private fields.
    * TypeScript: `camelCase` for variables/functions, `PascalCase` for React components.
* **Typing:** No `any` types in TypeScript. Use strict interfaces/types.

## 3. Security-First Implementation
* **Secrets Management:** Never hardcode keys. Use `appsettings.json` (and `UserSecrets` for dev) patterns.
* **Input Validation:** Use FluentValidation on the backend and Zod/Yup on the frontend.
* **Exception Handling:** Implement a Global Exception Handling Middleware that returns RFC 7807 (Problem Details) responses. Do not expose stack traces in Production.

## 4. Observability & Logging
* **Logging:** Use structured logging (e.g., Serilog).
* **HIPAA/GDPR Constraint:** Ensure logs **NEVER** contain PII (Personally Identifiable Information) or sensitive health data.
* **Health Checks:** Include `/health` endpoints for DB and External Services connectivity.

## 5. Testing Strategy
* **Mocking:** All external dependencies (DbContext, EmailService, PaymentGateway) must be injected via Interfaces (`IInterface`) to facilitate mocking in Unit Tests.
* **Test Coverage:** Aim for high coverage on Business Logic services.

## 6. Frontend Specifics (Next.js App Router)
* **Server-First Paradigm:** Default to React Server Components (RSC) for performance and SEO. Only use the `"use client"` directive when browser APIs, interactivity (e.g., `onClick`), or React state/hooks are required.
* **Data Fetching & BFF:** Leverage Server Components for data fetching where possible. Use Next.js Route Handlers (`app/bff/...`) as a secure Backend-For-Frontend (BFF) proxy to communicate with the ASP.NET API, keeping auth tokens server-side.
* **State Management:** Because Server Components handle data fetching, restrict global client state (e.g., Zustand, Context API) strictly to UI state (like theme) or authentication context.
* **Hooks:** Continue to extract reusable client-side logic into Custom Hooks.