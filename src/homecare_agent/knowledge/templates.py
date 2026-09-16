# Author: C A B M
# Date: 2026-09-17

"""Document template loader and renderer.

Loads markdown templates for Architecture Strategy, Tactical Plan, ADRs,
Agentic Prompts, Architecture Review, Code Review, PR Description,
Manual Testing Guide, and Standing Instructions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default templates directory relative to project root or package
_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


class TemplateManager:
    """Manages loading and rendering of document templates."""

    def __init__(self, templates_dir: Path | str | None = None) -> None:
        if templates_dir is not None:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = _DEFAULT_TEMPLATES_DIR

    def get_template_path(self, template_name: str) -> Path:
        """Get the full path to a template file."""
        if not template_name.endswith(".md"):
            template_name = f"{template_name}.md"
        return self.templates_dir / template_name

    def load_template(self, template_name: str) -> str:
        """Load a template file as string.

        Falls back to built-in defaults if file does not exist on disk.
        """
        path = self.get_template_path(template_name)
        if path.exists():
            return path.read_text(encoding="utf-8")
        
        # Fallback to built-in minimal template if disk template not yet populated
        logger.warning("Template %s not found on disk at %s; using built-in fallback", template_name, path)
        return self._get_fallback_template(template_name)

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with variable substitution.

        Replaces placeholders like {{ variable_name }} or {variable_name}.
        """
        content = self.load_template(template_name)
        for key, value in kwargs.items():
            content = content.replace(f"{{{{ {key} }}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    def _get_fallback_template(self, template_name: str) -> str:
        """Provide standard fallback templates if disk files are missing."""
        name = template_name.upper().replace(".MD", "")
        if "STRATEGY" in name:
            return "# STRATEGY: {{ feature_name }}\n\n## 1. Executive Summary\n{{ summary }}\n\n## 2. Business Context\n{{ business_context }}\n"
        elif "TACTICAL" in name:
            return "# TACTICAL PLAN: {{ feature_name }}\n\n## Execution Waves\n{{ execution_waves }}\n"
        elif "ADR" in name:
            return "# ADR-{{ adr_number }}: {{ title }}\n\n## Status\n{{ status }}\n\n## Context\n{{ context }}\n\n## Decision\n{{ decision }}\n\n## Consequences\n{{ consequences }}\n"
        elif "STANDING" in name:
            return "# STANDING INSTRUCTIONS\n\n- Follow Clean Architecture\n- Complete file implementations without truncation\n- Include unit tests\n"
        return f"# {template_name}\n\n{{{{ content }}}}\n"
