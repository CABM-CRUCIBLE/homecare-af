# Author: C A B M
# Date: 2026-09-17

"""Unit tests for knowledge base and template manager."""

from homecare_agent.knowledge.architecture import (
    ArchitectureLayer,
    CQRSPattern,
    EntityPattern,
    RepositoryArchitecture,
)
from homecare_agent.knowledge.conventions import (
    DEFAULT_STANDARDS,
    CodeQualityRules,
    EnterpriseStandards,
    NamingConventions,
)
from homecare_agent.knowledge.templates import TemplateManager


def test_clean_architecture_layers():
    repo_arch = RepositoryArchitecture()
    layer_names = [l.name for l in repo_arch.layers]
    assert "Domain" in layer_names
    assert "Application" in layer_names
    assert "Infrastructure" in layer_names
    assert "API" in layer_names

    domain_layer = next(l for l in repo_arch.layers if l.name == "Domain")
    assert domain_layer.allowed_dependencies == []  # Zero dependencies


def test_conventions():
    standards = DEFAULT_STANDARDS
    assert standards.quality.no_any_typescript is True
    assert standards.quality.no_truncation is True
    assert standards.naming.csharp["classes"] == "PascalCase"
    
    standing = standards.to_standing_instructions()
    assert "NON-NEGOTIABLE ENTERPRISE STANDARDS" in standing
    assert "RFC 7807" in standing


def test_template_manager_render():
    tm = TemplateManager()
    rendered = tm.render("STRATEGY_TEMPLATE.md", feature_name="Payment Processing", date="2026-09-16")
    assert "Strategy: Payment Processing" in rendered
    assert "2026-09-16" in rendered


def test_template_manager_adr():
    tm = TemplateManager()
    rendered = tm.render(
        "ADR_TEMPLATE.md",
        adr_number="001",
        title="Use Clean Architecture",
        status="Accepted",
        context="Separation of concerns",
        decision="Adopt Clean Architecture",
        positive_consequences="High maintainability",
        negative_consequences="Initial overhead",
        mitigations="Scaffolding",
        clean_architecture_impact="Enforces layers",
        tenant_isolation_impact="Global filters",
        compliance_impact="Full auditability",
    )
    assert "ADR-001: Use Clean Architecture" in rendered
    assert "Status" in rendered
    assert "Accepted" in rendered
