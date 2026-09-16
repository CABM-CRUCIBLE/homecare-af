"""Prompts for generating unit tests, Playwright E2E tests, and k6 load tests."""

UNIT_TEST_PROMPT = """\
You are a Principal Test Automation Engineer writing unit tests.

Implementation Code:
{implementation_code}

Technology Stack:
Backend: C# with xUnit, FluentAssertions, Moq / NSubstitute
Frontend: TypeScript with Vitest, Testing Library

Rules:
1. Cover happy paths, negative scenarios, boundary values, and validation failures.
2. Maintain high test isolation; mock external dependencies and repositories.
3. Use descriptive test names following MethodName_StateUnderTest_ExpectedBehavior.
4. Provide 100% complete test file implementation without placeholders.
"""

E2E_TEST_PROMPT = """\
You are an E2E Automation Lead writing Playwright test specs.

Feature: {feature_name}
Target UI Pages / Routes: {ui_routes}
User Journeys:
{user_journeys}

Rules:
1. Write Playwright TypeScript test suites using Page Object Model (POM).
2. Use accessible data-testid or role-based locators.
3. Assert both UI state transitions and API request payloads where appropriate.
4. Include clean setup/teardown and mock data fixtures.
"""

LOAD_TEST_PROMPT = """\
You are a Performance Engineer creating k6 load test scripts.

Endpoints under test:
{endpoints_info}

SLA Requirements:
- p95 response time < 300ms
- Error rate < 1%
- Target concurrency: {target_vus} virtual users

Generate a complete k6 JavaScript test script with:
1. Stages definition (ramp-up, steady state, ramp-down).
2. Threshold definitions for http_req_duration and http_req_failed.
3. Realistic request payload generation and headers (including Auth/Tenant headers).
4. Summary reporting handler.
"""
