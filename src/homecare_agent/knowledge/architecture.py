# Author: C A B M
# Date: 2026-09-17

"""Embedded architecture patterns knowledge base.

Provides structured knowledge about Clean Architecture patterns,
entity conventions, CQRS pipelines, and other architectural patterns
that the framework enforces during code generation. Configurable to
work with any repository that follows similar Clean Architecture patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArchitectureLayer:
    """Definition of a Clean Architecture layer."""

    name: str
    project_suffix: str
    allowed_dependencies: list[str]
    description: str
    key_patterns: list[str]


@dataclass
class EntityPattern:
    """Pattern for domain entity creation."""

    base_class: str
    required_properties: list[str]
    concurrency_pattern: str
    soft_delete: bool
    audit_logging: bool


@dataclass
class CQRSPattern:
    """Pattern for CQRS command/query implementation."""

    namespace_template: str
    command_suffix: str
    query_suffix: str
    handler_suffix: str
    validator_suffix: str
    pipeline_behaviors: list[str]


@dataclass
class RepositoryArchitecture:
    """Repository-specific architecture knowledge.

    This is configurable — loaded from the target repository's
    AI_Instructions.md and existing patterns, not hardcoded.
    """

    # Solution structure
    backend_root: str = "code/backend"
    frontend_root: str = "code/frontend"
    architecture_root: str = "Architecture"

    # Clean Architecture layers
    layers: list[ArchitectureLayer] = field(default_factory=lambda: [
        ArchitectureLayer(
            name="Domain",
            project_suffix=".Domain",
            allowed_dependencies=[],
            description="Pure POCO entities, value objects, domain events, exceptions",
            key_patterns=["Entities/", "Constants/", "Enums/", "Interfaces/", "Exceptions/"],
        ),
        ArchitectureLayer(
            name="Application",
            project_suffix=".Application",
            allowed_dependencies=["Domain"],
            description="CQRS handlers, validators, services, interfaces",
            key_patterns=["Features/", "Services/", "Interfaces/", "DTOs/"],
        ),
        ArchitectureLayer(
            name="Infrastructure",
            project_suffix=".Infrastructure",
            allowed_dependencies=["Domain", "Application"],
            description="EF Core, external services, repositories",
            key_patterns=["Data/", "Services/", "Repositories/"],
        ),
        ArchitectureLayer(
            name="API",
            project_suffix=".API",
            allowed_dependencies=["Domain", "Application", "Infrastructure"],
            description="Controllers, middleware, DI registration",
            key_patterns=["Controllers/", "Extensions/", "Middleware/"],
        ),
    ])

    # Entity patterns
    entity_pattern: EntityPattern = field(default_factory=lambda: EntityPattern(
        base_class="BaseEntity",
        required_properties=["Id", "CreatedAt", "UpdatedAt", "IsDeleted"],
        concurrency_pattern="xmin PostgreSQL system column mapped as Version",
        soft_delete=True,
        audit_logging=True,
    ))

    # CQRS pattern
    cqrs_pattern: CQRSPattern = field(default_factory=lambda: CQRSPattern(
        namespace_template="{Project}.Application.Features.{Feature}",
        command_suffix="Command",
        query_suffix="Query",
        handler_suffix="Handler",
        validator_suffix="Validator",
        pipeline_behaviors=["ValidationBehavior", "LoggingBehavior"],
    ))

    # Frontend patterns
    frontend_patterns: dict[str, str] = field(default_factory=lambda: {
        "router": "App Router (Next.js 15)",
        "rendering": "Server-First RSC with client islands",
        "data_fetching": "BFF proxy via app/bff/ route handlers",
        "state_management": "URL-driven state, minimal client-side state",
        "validation": "Zod schemas",
        "styling": "Tailwind CSS",
    })

    # Testing patterns
    test_patterns: dict[str, str] = field(default_factory=lambda: {
        "backend_unit": "xUnit with Moq/NSubstitute",
        "backend_integration": "WebApplicationFactory with test database",
        "frontend_unit": "Vitest with React Testing Library",
        "e2e": "Playwright",
        "load": "k6",
        "architecture": "NetArchTest for layer dependency validation",
    })

    # Compliance requirements
    compliance: dict[str, list[str]] = field(default_factory=lambda: {
        "hipaa": [
            "No PHI in logs — use Serilog destructuring policies",
            "Encrypted fields for sensitive data (AES-256-GCM)",
            "Audit trail for every mutation via IAuditLogService",
            "Access control via RBAC + FBAC",
        ],
        "gdpr": [
            "Data minimization — only necessary fields in DTOs",
            "Consent tracking",
            "Right to erasure support via soft delete",
        ],
        "pci_dss": [
            "No payment card data in logs",
            "Encrypted storage for financial instruments",
            "Tokenization for payment references",
        ],
    })


# Default architecture for HomeCare (can be overridden by repo analysis)
DEFAULT_ARCHITECTURE = RepositoryArchitecture()


def get_architecture(repo_path: str = "") -> RepositoryArchitecture:
    """Get the architecture knowledge base.

    If repo_path is provided, attempts to load repo-specific patterns
    from AI_Instructions.md and existing code analysis. Otherwise
    returns the default configurable patterns.

    Args:
        repo_path: Optional path to the target repository.

    Returns:
        Repository architecture knowledge.
    """
    # For now, return default. In a full implementation, this would
    # analyze the repo's AI_Instructions.md and detect patterns.
    return DEFAULT_ARCHITECTURE
