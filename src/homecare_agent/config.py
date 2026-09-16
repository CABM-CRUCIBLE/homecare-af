# Author: C A B M
# Date: 2026-09-17

"""Configuration and environment management for the HomeCare Agentic Framework.

Provides validated configuration via pydantic-settings, supporting both
environment variables and .env files. All secrets are loaded from env vars
and never hardcoded.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    """GitHub authentication mode."""

    PAT = "pat"
    GITHUB_APP = "github_app"


class ExecutionMode(str, Enum):
    """Work package execution strategy."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class ClarificationMode(str, Enum):
    """How clarification questions are presented to the user."""

    CLI = "cli"
    WEB = "web"


class Settings(BaseSettings):
    """Central configuration for the HomeCare Agentic Framework.

    All values can be set via environment variables or a .env file.
    Required fields must be provided; optional fields have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── LLM Provider (OpenRouter BYOK) ─────────────────────────────────
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key (BYOK). Required.",
    )
    openrouter_model: str = Field(
        default="",
        description="Default LLM model on OpenRouter. User is prompted during setup if empty.",
    )
    openrouter_vision_model: str = Field(
        default="",
        description="Vision-capable model for wireframe analysis. Defaults to openrouter_model if empty.",
    )
    model_architecture: str = Field(
        default="",
        description="High-reasoning model for architecture analysis, strategy, tactical plan, and ADRs.",
    )
    model_code: str = Field(
        default="",
        description="Cost-effective model for work package code generation and test synthesis.",
    )
    model_review: str = Field(
        default="",
        description="High-reasoning model for architecture reviews and PR code reviews.",
    )
    model_intake: str = Field(
        default="",
        description="Model for feature intake and clarification loops.",
    )
    node_models: dict[str, str] = Field(
        default_factory=dict,
        description="Granular mapping of specific LangGraph node names to OpenRouter models.",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL.",
    )
    max_tokens: int = Field(
        default=16384,
        description="Maximum tokens per LLM response.",
    )
    temperature: float = Field(
        default=0.1,
        description="LLM temperature. Low for deterministic code generation.",
    )

    # ─── Langfuse Observability ──────────────────────────────────────────
    langfuse_public_key: str = Field(
        default="",
        description="Langfuse public key for tracing.",
    )
    langfuse_secret_key: str = Field(
        default="",
        description="Langfuse secret key for tracing.",
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host URL.",
    )
    langfuse_enabled: bool = Field(
        default=False,
        description="Enable Langfuse tracing. Auto-enabled when keys are provided.",
    )
    langfuse_init_project_id: str = Field(
        default="homecare",
        description="Langfuse initial project ID.",
    )
    langfuse_init_user_email: str = Field(
        default="admin@homecare.local",
        description="Langfuse initial admin user email.",
    )
    langfuse_init_user_password: str = Field(
        default="HomeCareAdmin123!",
        description="Langfuse initial admin user password.",
    )

    # ─── GitHub ──────────────────────────────────────────────────────────
    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token.",
    )
    github_app_id: int = Field(
        default=0,
        description="GitHub App ID (alternative to PAT).",
    )
    github_app_private_key_path: str = Field(
        default="",
        description="Path to GitHub App private key PEM file.",
    )
    github_app_installation_id: int = Field(
        default=0,
        description="GitHub App Installation ID.",
    )
    github_auth_mode: AuthMode = Field(
        default=AuthMode.PAT,
        description="GitHub authentication mode: 'pat' or 'github_app'.",
    )

    # ─── Target Repository ───────────────────────────────────────────────
    repo_path: str = Field(
        default="",
        description="Absolute path to the local repository clone.",
    )
    repo_url: str = Field(
        default="",
        description="GitHub repository URL (e.g., https://github.com/org/repo).",
    )
    repo_default_branch: str = Field(
        default="main",
        description="Default branch name.",
    )

    # ─── Execution ───────────────────────────────────────────────────────
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.PARALLEL,
        description="Work package execution: 'parallel' (within waves) or 'sequential'.",
    )
    max_parallel_workers: int = Field(
        default=5,
        description="Maximum concurrent LLM calls during parallel wave execution.",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retries for failed operations (build, test, LLM calls).",
    )
    max_review_iterations: int = Field(
        default=3,
        description="Maximum code review → fix → re-review cycles.",
    )

    # ─── UI ──────────────────────────────────────────────────────────────
    clarification_mode: ClarificationMode = Field(
        default=ClarificationMode.CLI,
        description="How clarification questions are presented: 'cli' or 'web'.",
    )
    web_ui_port: int = Field(
        default=7860,
        description="Port for the Gradio web UI.",
    )

    # ─── Logging ─────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR.",
    )

    # ─── Paths ───────────────────────────────────────────────────────────
    output_dir: str = Field(
        default="output",
        description="Directory for generated architecture documents and artifacts.",
    )
    templates_dir: str = Field(
        default="templates",
        description="Directory containing document generation templates.",
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure the API key is not empty."""
        if not v or not v.strip():
            raise ValueError("OPENROUTER_API_KEY is required. Set it in .env or as an environment variable.")
        return v.strip()

    @field_validator("langfuse_enabled", mode="before")
    @classmethod
    def auto_enable_langfuse(cls, v: Any, info: object) -> bool:
        """Auto-enable Langfuse when both keys are provided and not explicitly disabled."""
        if v in (False, "false", "False", "0", "no"):
            return False
        if v in (True, "true", "True", "1", "yes"):
            return True
        data = getattr(info, "data", {})
        if data.get("langfuse_public_key") and data.get("langfuse_secret_key"):
            return True
        return False

    @property
    def effective_vision_model(self) -> str:
        """Return the vision model, falling back to the primary model."""
        return self.openrouter_vision_model or self.openrouter_model

    @property
    def output_path(self) -> Path:
        """Return the output directory as a Path object."""
        return Path(self.output_dir)

    @property
    def templates_path(self) -> Path:
        """Return the templates directory as a Path object."""
        return Path(self.templates_dir)

    @property
    def has_github_credentials(self) -> bool:
        """Check if GitHub credentials are configured."""
        if self.github_auth_mode == AuthMode.PAT:
            return bool(self.github_token)
        return bool(
            self.github_app_id
            and self.github_app_private_key_path
            and self.github_app_installation_id
        )

    def get_model_for_node(
        self,
        node_name: str,
        state_overrides: dict[str, Any] | None = None,
    ) -> str:
        """Resolve the effective model for a specific LangGraph node.

        Priority order:
        1. Node-specific match in state_overrides['node_models']
        2. Node-specific match in self.node_models
        3. Role/tier categorized match:
           - Architecture/Analysis -> model_architecture
           - Code Gen/Tests -> model_code
           - Reviews -> model_review
           - Intake/Clarification -> model_intake
        4. self.openrouter_model (default fallback)
        """
        overrides = state_overrides or {}

        # 1. Direct node match in state overrides
        state_node_models = overrides.get("node_models") or {}
        if node_name in state_node_models and state_node_models[node_name]:
            return state_node_models[node_name]

        # 2. Direct node match in settings
        if node_name in self.node_models and self.node_models[node_name]:
            return self.node_models[node_name]

        # 3. Categorized mapping
        arch_nodes = {
            "analyze_codebase",
            "generate_strategy",
            "generate_tactical_plan",
            "generate_adrs",
            "generate_agentic_prompts",
            "revise_architecture",
        }
        code_nodes = {
            "execute_wave",
            "run_unit_tests",
            "run_e2e_tests",
            "run_load_tests",
            "generate_manual_test_doc",
            "write_files",
        }
        review_nodes = {
            "review_architecture",
            "perform_code_review",
            "apply_review_fixes",
        }
        intake_nodes = {
            "intake_feature",
            "ask_clarifications",
        }

        if node_name in code_nodes:
            model = overrides.get("model_code") or self.model_code
            if model:
                return model
        elif node_name in arch_nodes:
            model = overrides.get("model_architecture") or self.model_architecture
            if model:
                return model
        elif node_name in review_nodes:
            model = (
                overrides.get("model_review")
                or self.model_review
                or overrides.get("model_architecture")
                or self.model_architecture
            )
            if model:
                return model
        elif node_name in intake_nodes:
            model = (
                overrides.get("model_intake")
                or self.model_intake
                or overrides.get("model_architecture")
                or self.model_architecture
            )
            if model:
                return model

        return (
            overrides.get("openrouter_model")
            or self.openrouter_model
            or "anthropic/claude-sonnet-4"
        )


def get_settings(**overrides: object) -> Settings:
    """Create a Settings instance with optional overrides.

    Args:
        **overrides: Key-value pairs to override default/env settings.

    Returns:
        A validated Settings instance.
    """
    return Settings(**overrides)  # type: ignore[arg-type]
