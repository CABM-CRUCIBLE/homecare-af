# Author: C A B M
# Date: 2026-09-17

"""Codebase analysis node.

Deeply scans the target repository to understand its architecture,
existing patterns, entities, controllers, and conventions. This
produces the current-state assessment that informs the strategy.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """\
You are a Senior Software Architect performing a deep analysis of an enterprise codebase.
You must produce a thorough current-state assessment covering:

1. **Solution Structure**: Projects, layers, naming conventions
2. **Domain Entities**: Entity classes, base classes, inheritance patterns
3. **Architecture Patterns**: Clean Architecture layers, CQRS/MediatR, Repository+UoW
4. **API Surface**: Controllers, endpoints, versioning, authorization
5. **Frontend Architecture**: App Router routes, components, BFF patterns
6. **Database**: EF Core configurations, migrations, indexes, constraints
7. **Testing**: Test projects, frameworks, coverage patterns
8. **Security**: Auth patterns, tenant isolation, PII handling
9. **Compliance**: Audit logging, HIPAA patterns, encryption
10. **Conventions**: Naming, file organization, coding standards

For each area, cite specific file paths and code evidence.
Output as a structured JSON with the section names as keys.
"""


async def analyze_codebase(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Perform deep analysis of the target repository.

    This node:
    1. Scans the repository directory structure
    2. Identifies solution/project files
    3. Analyzes key architectural files
    4. Extracts entity patterns, API surface, frontend routes
    5. Detects conventions and coding standards
    6. Produces a gap analysis: what exists vs. what's needed

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates with codebase analysis and detected patterns.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    repo_path = Path(state.get("repo_path", settings.repo_path))
    logger.info("[START:analyze_codebase][trace_id=%s] Starting codebase analysis for '%s' at: %s", trace_id, feature_name, repo_path)

    updates: dict[str, Any] = {
        "current_step": "analyze_codebase",
    }

    if not repo_path.exists():
        logger.error("[ERROR:analyze_codebase][trace_id=%s] Target repository path does not exist: %s", trace_id, repo_path)
        updates["errors"] = [{"step": "analyze_codebase", "trace_id": trace_id, "message": f"Repository not found: {repo_path}"}]
        updates["completed_steps"] = ["analyze_codebase"]
        return updates

    # Step 1: Scan directory structure
    logger.debug("[analyze_codebase][trace_id=%s] Scanning directory structure...", trace_id)
    structure_summary = _scan_directory_structure(repo_path)

    # Step 2: Read key architectural files
    logger.debug("[analyze_codebase][trace_id=%s] Reading key architectural files...", trace_id)
    key_files_content = _read_key_files(repo_path)

    # Step 3: Identify entities and patterns
    logger.debug("[analyze_codebase][trace_id=%s] Scanning Domain entities...", trace_id)
    entity_summary = _scan_entities(repo_path)

    # Step 4: Identify API controllers
    logger.debug("[analyze_codebase][trace_id=%s] Scanning API controllers...", trace_id)
    api_summary = _scan_controllers(repo_path)

    # Step 5: Identify frontend routes
    logger.debug("[analyze_codebase][trace_id=%s] Scanning frontend routes...", trace_id)
    frontend_summary = _scan_frontend_routes(repo_path)

    # Step 6: Ask LLM to synthesize the analysis
    analysis_prompt = f"""Analyze the following enterprise codebase structure and files.
Produce a comprehensive current-state assessment.

**Feature being built:** {feature_name}
**Feature description:** {state.get("feature_description", "")}

**Repository Structure:**
{structure_summary}

**Key Architectural Files:**
{key_files_content}

**Domain Entities Found:**
{entity_summary}

**API Controllers Found:**
{api_summary}

**Frontend Routes Found:**
{frontend_summary}

Based on this analysis:
1. Identify what already exists and is reusable for the new feature
2. Identify blocking defects that must be fixed first
3. Identify what doesn't exist and must be built new
4. Detect the architecture patterns and conventions to follow
5. Map integration points between the new feature and existing modules

Output as structured JSON with keys:
- "reusable_capabilities": list of {{capability, evidence, verdict}}
- "blocking_defects": list of {{id, defect, evidence}}
- "new_builds": list of strings
- "architecture_patterns": dict of detected patterns
- "conventions": dict of coding conventions
- "integration_points": list of strings
"""

    try:
        logger.debug("[analyze_codebase][trace_id=%s] Requesting architectural synthesis from LLM...", trace_id)
        response = await llm.ainvoke(
            prompt=analysis_prompt,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            node_name="analyze_codebase",
            state_overrides=state,
            trace_name="codebase_analysis",
            trace_metadata={"repo_path": str(repo_path), "feature_name": feature_name, "trace_id": trace_id},
        )

        from homecare_agent.tools.json_utils import extract_json

        parsed = extract_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            updates["codebase_analysis"] = parsed
            updates["existing_patterns"] = parsed.get("architecture_patterns", {})
            logger.info(
                "[COMPLETED:analyze_codebase][trace_id=%s] Analysis parsed successfully — reusable=%d, blocking_defects=%d, new_builds=%d",
                trace_id,
                len(parsed.get("reusable_capabilities", [])),
                len(parsed.get("blocking_defects", [])),
                len(parsed.get("new_builds", [])),
            )
        else:
            logger.warning("[WARN:analyze_codebase][trace_id=%s] Failed to extract JSON object from analysis response", trace_id)
            updates["codebase_analysis"] = {"raw_analysis": response}

    except Exception as e:
        logger.error(
            "[ERROR:analyze_codebase][trace_id=%s] Codebase analysis LLM call failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        updates["errors"] = [{"step": "analyze_codebase", "trace_id": trace_id, "message": f"Analysis LLM call failed: {e}"}]
        updates["codebase_analysis"] = {"raw_structure": structure_summary}

    updates["completed_steps"] = ["analyze_codebase"]
    return updates


def _scan_directory_structure(repo_path: Path, max_depth: int = 4) -> str:
    """Scan the repository directory structure up to a given depth.

    Args:
        repo_path: Root path to scan.
        max_depth: Maximum directory depth.

    Returns:
        A tree-like string representation of the directory structure.
    """
    lines: list[str] = []
    skip_dirs = {".git", "node_modules", "bin", "obj", ".next", ".nuget", "__pycache__", ".vs", "dist"}

    def _walk(path: Path, depth: int, prefix: str = "") -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in skip_dirs]
        files = [e for e in entries if e.is_file()]

        # Show files at this level (limit to important ones)
        important_exts = {".cs", ".ts", ".tsx", ".json", ".csproj", ".sln", ".md", ".yml", ".yaml"}
        for f in files[:20]:
            if f.suffix in important_exts or f.name in {"Dockerfile", "docker-compose.yml", "package.json", ".env.example"}:
                lines.append(f"{prefix}{f.name}")

        for d in dirs:
            lines.append(f"{prefix}{d.name}/")
            _walk(d, depth + 1, prefix + "  ")

    _walk(repo_path, 0)
    return "\n".join(lines[:500])  # Cap at 500 lines


def _read_key_files(repo_path: Path) -> str:
    """Read key architectural files from the repository.

    Args:
        repo_path: Root path.

    Returns:
        Concatenated content of key files.
    """
    key_file_patterns = [
        "AI_Instructions.md",
        "*.sln",
        "**/Program.cs",
        "**/ServiceCollectionExtensions.cs",
        "**/HomeCareDbContext.cs",
        "**/UnitOfWork.cs",
        "code/frontend/package.json",
        "code/frontend/next.config.*",
        "ARCHITECTURE.md",
    ]

    content_parts: list[str] = []
    for pattern in key_file_patterns:
        matches = list(repo_path.glob(pattern))
        for match in matches[:2]:  # Limit to 2 matches per pattern
            try:
                text = match.read_text(encoding="utf-8", errors="replace")
                # Truncate large files
                if len(text) > 5000:
                    text = text[:5000] + "\n... [truncated]"
                content_parts.append(f"\n### {match.relative_to(repo_path)}\n```\n{text}\n```")
            except Exception:
                pass

    return "\n".join(content_parts[:20])  # Cap at 20 files


def _scan_entities(repo_path: Path) -> str:
    """Scan for C# entity classes in the Domain layer.

    Args:
        repo_path: Root path.

    Returns:
        Summary of detected entities.
    """
    entity_dirs = list(repo_path.glob("**/Domain/Entities"))
    entities: list[str] = []
    for entity_dir in entity_dirs:
        for cs_file in entity_dir.glob("*.cs"):
            entities.append(cs_file.stem)
    return ", ".join(entities[:50]) if entities else "No entities found"


def _scan_controllers(repo_path: Path) -> str:
    """Scan for ASP.NET API controllers.

    Args:
        repo_path: Root path.

    Returns:
        Summary of detected controllers.
    """
    controller_dirs = list(repo_path.glob("**/Controllers"))
    controllers: list[str] = []
    for ctrl_dir in controller_dirs:
        for cs_file in ctrl_dir.glob("*Controller.cs"):
            controllers.append(cs_file.stem)
    return ", ".join(controllers[:30]) if controllers else "No controllers found"


def _scan_frontend_routes(repo_path: Path) -> str:
    """Scan for Next.js App Router routes.

    Args:
        repo_path: Root path.

    Returns:
        Summary of detected frontend routes.
    """
    app_dirs = list(repo_path.glob("**/app"))
    routes: list[str] = []
    for app_dir in app_dirs:
        for page_file in app_dir.glob("**/page.tsx"):
            route = str(page_file.parent.relative_to(app_dir)).replace("\\", "/")
            routes.append(f"/{route}")
    return "\n".join(routes[:30]) if routes else "No frontend routes found"
