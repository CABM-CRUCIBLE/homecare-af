# Author: C A B M
# Date: 2026-09-17

"""Enterprise coding conventions and standards.

Codifies the enterprise coding standards from AI_Instructions.md
and makes them available as structured data for prompt injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NamingConventions:
    """Naming conventions for the codebase."""

    csharp: dict[str, str] = field(default_factory=lambda: {
        "classes": "PascalCase",
        "methods": "PascalCase",
        "private_fields": "_camelCase",
        "properties": "PascalCase",
        "interfaces": "IPascalCase",
        "constants": "PascalCase",
        "enums": "PascalCase",
    })

    typescript: dict[str, str] = field(default_factory=lambda: {
        "variables": "camelCase",
        "functions": "camelCase",
        "components": "PascalCase",
        "interfaces": "PascalCase",
        "types": "PascalCase",
        "hooks": "useCamelCase",
    })


@dataclass
class CodeQualityRules:
    """Code quality rules from AI_Instructions.md."""

    # Type safety
    no_any_typescript: bool = True
    strict_null_checks: bool = True

    # Documentation
    xml_comments_on_public: bool = True
    inline_why_comments: bool = True

    # Validation
    backend_validation: str = "FluentValidation"
    frontend_validation: str = "Zod"

    # Error handling
    error_format: str = "RFC 7807 ProblemDetails"
    no_stack_traces_in_production: bool = True

    # Logging
    logging_framework: str = "Serilog"
    structured_logging: bool = True
    no_pii_in_logs: bool = True
    pii_fields: list[str] = field(default_factory=lambda: [
        "bank account numbers", "routing/IFSC codes", "GSTIN", "PAN",
        "patient names", "SSN", "email addresses", "phone numbers",
        "credit card numbers", "health records", "PHI",
    ])

    # Money
    money_as_integer_minor_units: bool = True
    money_currency_field: str = "ISO 4217 CurrencyCode"
    no_float_for_money: bool = True

    # Security
    secrets_in_env_only: bool = True
    interface_based_di: bool = True
    audit_every_mutation: bool = True
    vendor_identity_from_jwt_only: bool = True

    # Code completeness
    no_truncation: bool = True
    no_mock_data_in_runtime: bool = True
    no_fallback_data: bool = True


@dataclass
class EnterpriseStandards:
    """Complete enterprise standards bundle."""

    naming: NamingConventions = field(default_factory=NamingConventions)
    quality: CodeQualityRules = field(default_factory=CodeQualityRules)

    def to_standing_instructions(self) -> str:
        """Render standards as standing instructions text for prompts.

        Returns:
            Formatted standing instructions string.
        """
        return f"""\
NON-NEGOTIABLE ENTERPRISE STANDARDS:

TYPE SAFETY:
- No `any` types in TypeScript — use strict interfaces/types
- Strict null checks enabled

DOCUMENTATION:
- XML doc comments (/// <summary>) on all public types, members, and interfaces
- Inline comments explaining WHY complex logic exists, not just WHAT

VALIDATION:
- Backend: FluentValidation (every command/query must have a validator)
- Frontend: Zod schemas (every form input must be validated)

ERROR HANDLING:
- RFC 7807 ProblemDetails via global exception middleware
- Never expose stack traces in production

LOGGING:
- Serilog structured logging
- NEVER log PII: {', '.join(self.quality.pii_fields[:5])}...
- Log identifiers only (IDs, correlation IDs)

MONEY:
- Integer minor units (long/bigint) + ISO 4217 currency code
- NEVER float or decimal for money
- NEVER hard-code currency symbols

SECURITY:
- All external dependencies via interface-based DI
- Audit every mutation via IAuditLogService
- Vendor identity from JWT claims only (IVendorIdentityResolver)
- No secrets in source code — environment variables only

CODE COMPLETENESS:
- FULL file contents — no "// ... rest of code" placeholders
- No mock/fixture/fallback data in production paths
"""


# Default standards instance
DEFAULT_STANDARDS = EnterpriseStandards()
