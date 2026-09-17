# Author: C A B M
# Date: 2026-09-17

"""Feature request data models.

Defines the structured schema for feature requests that flow through the
agentic pipeline, including wireframe references, acceptance criteria, and
clarification tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FeaturePriority(str, Enum):
    """Feature priority classification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WireframeSource(str, Enum):
    """How a wireframe was provided."""

    LOCAL_FILE = "local_file"
    URL = "url"


class Wireframe(BaseModel):
    """A wireframe or screenshot reference."""

    source: WireframeSource
    path_or_url: str = Field(..., description="Local file path or URL to the wireframe image.")
    description: str = Field(default="", description="Optional description of what this wireframe shows.")
    extracted_requirements: list[str] = Field(
        default_factory=list,
        description="Requirements extracted from vision analysis of this wireframe.",
    )


class ClarificationQuestion(BaseModel):
    """A question posed to the user for requirement clarification."""

    id: str = Field(..., description="Unique identifier for the question.")
    category: str = Field(..., description="Category: 'functional', 'non_functional', 'security', 'integration', 'ux'.")
    question: str = Field(..., description="The question text.")
    context: str = Field(default="", description="Why this question matters.")
    options: list[str] = Field(default_factory=list, description="Suggested options, if applicable.")
    is_critical: bool = Field(default=False, description="Whether this blocks architecture generation.")
    answer: str | None = Field(default=None, description="The user's answer, once provided.")


class FunctionalRequirement(BaseModel):
    """A functional requirement extracted from the feature request."""

    id: str = Field(..., description="Requirement ID (e.g., FR-01).")
    title: str = Field(..., description="Short descriptive title.")
    description: str = Field(..., description="Full requirement description.")
    priority: FeaturePriority = Field(default=FeaturePriority.MEDIUM)
    acceptance_criteria: list[str] = Field(default_factory=list)
    source: str = Field(default="description", description="Where this requirement originated: 'description', 'wireframe', 'clarification'.")


class NonFunctionalRequirement(BaseModel):
    """A non-functional requirement."""

    id: str = Field(..., description="Requirement ID (e.g., NFR-01).")
    category: str = Field(..., description="Category: 'performance', 'security', 'compliance', 'usability', 'scalability'.")
    description: str
    target_metric: str = Field(default="", description="Measurable target (e.g., 'p95 < 300ms').")


class FeatureRequest(BaseModel):
    """Complete feature request input to the agentic pipeline."""

    # Core identification
    name: str = Field(..., description="Feature name (e.g., 'Order Service Request Fulfillment Workflow').")
    description: str = Field(..., description="Natural language description of the feature.")
    module_name: str = Field(default="", description="Target module/bounded context in the codebase.")

    # Visual inputs
    wireframes: list[Wireframe] = Field(default_factory=list)

    # Requirements (populated during intake and clarification)
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list, description="Technical or business constraints.")
    assumptions: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)

    # Clarification
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    clarification_complete: bool = Field(default=False)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    priority: FeaturePriority = Field(default=FeaturePriority.MEDIUM)
    related_features: list[str] = Field(default_factory=list, description="Names of related existing features.")
    related_adrs: list[str] = Field(default_factory=list, description="Related ADR numbers.")
