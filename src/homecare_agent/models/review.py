# Author: C A B M
# Date: 2026-09-17

"""Test result and code review data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Test Results ────────────────────────────────────────────────────────────

class TestFramework(str, Enum):
    """Supported test frameworks."""

    XUNIT = "xunit"
    VITEST = "vitest"
    PLAYWRIGHT = "playwright"
    K6 = "k6"


class TestStatus(str, Enum):
    """Individual test case status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCase(BaseModel):
    """An individual test case result."""

    name: str
    status: TestStatus
    duration_ms: float = Field(default=0.0)
    error_message: str = Field(default="")
    stack_trace: str = Field(default="")


class TestSuiteResult(BaseModel):
    """Results from a test suite execution."""

    framework: TestFramework
    suite_name: str = Field(default="")
    test_cases: list[TestCase] = Field(default_factory=list)
    total: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)
    duration_ms: float = Field(default=0.0)
    raw_output: str = Field(default="")
    executed_at: datetime = Field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """Whether all tests passed."""
        return self.failed == 0


class LoadTestResult(BaseModel):
    """Results from a k6 load test execution."""

    scenario: str = Field(default="")
    vus: int = Field(default=0, description="Virtual users.")
    duration_seconds: int = Field(default=0)
    requests_total: int = Field(default=0)
    requests_per_second: float = Field(default=0.0)
    p95_response_ms: float = Field(default=0.0)
    p99_response_ms: float = Field(default=0.0)
    error_rate: float = Field(default=0.0)
    thresholds_passed: bool = Field(default=True)
    raw_output: str = Field(default="")


# ─── Code Review ─────────────────────────────────────────────────────────────

class ReviewSeverity(str, Enum):
    """Code review finding severity."""

    BLOCKING = "blocking"
    CRITICAL = "critical"
    MAJOR = "major"
    MEDIUM = "medium"
    MINOR = "minor"
    OBSERVATION = "observation"


class ReviewGrade(str, Enum):
    """Review category grade."""

    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    C = "C"
    F = "F"


class ReviewCategory(BaseModel):
    """A scored category in the review scorecard."""

    category: str = Field(..., description="e.g., 'SOLID Principles', 'Clean Architecture', 'Security'.")
    grade: ReviewGrade
    notes: str = Field(default="")


class ReviewFinding(BaseModel):
    """A single code review finding."""

    id: str = Field(..., description="Finding ID (e.g., F-01).")
    severity: ReviewSeverity
    category: str = Field(..., description="e.g., 'security', 'architecture', 'type_safety', 'testing'.")
    title: str
    description: str
    file_path: str = Field(default="", description="Affected file path.")
    line_range: str = Field(default="", description="Affected line range (e.g., 'L42-L58').")
    suggestion: str = Field(default="", description="Suggested fix.")
    auto_fixable: bool = Field(default=False, description="Whether the framework can auto-fix this.")


class ReviewVerdict(str, Enum):
    """Overall review verdict."""

    APPROVE = "approve"
    APPROVE_WITH_OBSERVATIONS = "approve_with_observations"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class ArchitectureReview(BaseModel):
    """Architecture review result — pre-implementation review.

    Following the format from Architecture_Review.md:
    - Executive Verdict
    - Prior Review Disposition (traceability)
    - Detailed section reviews
    - Findings with severity
    - Scorecard
    """

    review_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    reviewer_role: str = Field(default="Senior Solution Architect (20+ years)")
    review_type: str = Field(default="Pre-implementation architecture review")
    scope: str = Field(default="")

    verdict: ReviewVerdict = Field(default=ReviewVerdict.APPROVE)
    executive_summary: str = Field(default="")
    scorecard: list[ReviewCategory] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    prior_review_disposition: str = Field(default="", description="Traceability to prior review findings.")

    rendered_markdown: str = Field(default="")


class CodeReview(BaseModel):
    """Code review result — post-implementation review.

    Following the format from Code_Review.md:
    - Executive Summary & Verdict
    - Review Scorecard (graded categories)
    - Section-by-section analysis
    - Findings with severity and auto-fix suggestions
    """

    branch: str = Field(default="")
    review_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    reviewer_role: str = Field(default="Senior Software Architect (20+ years)")
    standards_reference: str = Field(default="AI_Instructions.md — Enterprise Code Quality Standards")
    scope: str = Field(default="", description="Files changed summary.")

    verdict: ReviewVerdict = Field(default=ReviewVerdict.APPROVE)
    executive_summary: str = Field(default="")
    scorecard: list[ReviewCategory] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    changes_needed: bool = Field(default=False)

    rendered_markdown: str = Field(default="")

    @property
    def blocking_count(self) -> int:
        """Number of blocking/critical findings."""
        return sum(
            1 for f in self.findings
            if f.severity in (ReviewSeverity.BLOCKING, ReviewSeverity.CRITICAL)
        )
