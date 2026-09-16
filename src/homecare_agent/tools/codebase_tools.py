"""Codebase analysis tools for inspecting Clean Architecture repositories.

Provides utilities for:
- Parsing .NET solution (.sln) and project (.csproj) structures
- Extracting C# domain entities and inheritance
- Extracting API controllers, routes, and HTTP methods
- Discovering Next.js frontend pages and routes
- Identifying existing architectural patterns and related modules
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from homecare_agent.tools.file_tools import list_files, read_file

logger = logging.getLogger(__name__)


def analyze_solution(repo_path: str | Path) -> dict[str, Any]:
    """Scan and analyze .NET solution files and project structure."""
    base = Path(repo_path)
    sln_files = list(base.glob("**/*.sln"))
    csproj_files = list(base.glob("**/*.csproj"))

    projects: list[dict[str, Any]] = []
    for proj in csproj_files:
        if "bin" in proj.parts or "obj" in proj.parts:
            continue
        
        # Read project references
        refs: list[str] = []
        try:
            tree = ET.parse(proj)
            root = tree.getroot()
            for elem in root.findall(".//ProjectReference"):
                inc = elem.get("Include", "")
                if inc:
                    refs.append(Path(inc).stem)
        except Exception as e:
            logger.debug("Could not parse csproj %s: %s", proj, e)

        # Categorize Clean Architecture layer
        name = proj.stem
        layer = "Unknown"
        if "Domain" in name:
            layer = "Domain"
        elif "Application" in name:
            layer = "Application"
        elif "Infrastructure" in name or "Persistence" in name:
            layer = "Infrastructure"
        elif "Api" in name or "Web" in name or "Server" in name:
            layer = "Api"
        elif "Test" in name:
            layer = "Tests"

        projects.append({
            "name": name,
            "path": str(proj.relative_to(base)),
            "layer": layer,
            "references": refs,
        })

    return {
        "solution_files": [str(s.relative_to(base)) for s in sln_files],
        "total_projects": len(projects),
        "projects": projects,
    }


def analyze_entities(domain_path: str | Path) -> list[dict[str, Any]]:
    """Extract C# entity classes, properties, and base types."""
    path = Path(domain_path)
    if not path.exists():
        return []

    entity_files = list_files(path, "*.cs")
    entities: list[dict[str, Any]] = []

    class_pattern = re.compile(
        r"public\s+(?:abstract\s+)?class\s+(\w+)(?:\s*:\s*([\w<>\s,]+))?",
        re.MULTILINE,
    )
    prop_pattern = re.compile(
        r"public\s+([\w<>?]+)\s+(\w+)\s*\{\s*get;\s*(?:set|init|private set)?;\s*\}",
        re.MULTILINE,
    )

    for f in entity_files:
        try:
            content = read_file(f)
            for class_match in class_pattern.finditer(content):
                class_name = class_match.group(1)
                base_types = [b.strip() for b in (class_match.group(2) or "").split(",") if b.strip()]
                
                props: list[dict[str, str]] = []
                for prop_match in prop_pattern.finditer(content):
                    props.append({
                        "type": prop_match.group(1),
                        "name": prop_match.group(2),
                    })

                entities.append({
                    "name": class_name,
                    "file": str(f),
                    "base_types": base_types,
                    "properties": props,
                })
        except Exception as e:
            logger.debug("Failed parsing entity in %s: %s", f, e)

    return entities


def analyze_controllers(api_path: str | Path) -> list[dict[str, Any]]:
    """Extract ASP.NET Core API controllers, route attributes, and endpoints."""
    path = Path(api_path)
    if not path.exists():
        return []

    controller_files = list_files(path, "*Controller.cs")
    controllers: list[dict[str, Any]] = []

    route_attr_re = re.compile(r'\[Route\(["\']([^"\']+)["\']\)\]')
    class_re = re.compile(r"public\s+class\s+(\w+)\s*:\s*([\w\s,]+)")
    http_method_re = re.compile(
        r'\[Http(Get|Post|Put|Delete|Patch)(?:\(["\']([^"\']*)["\']\))?\]\s*\n\s*public\s+(?:async\s+)?(?:Task<)?([\w<>?]+)>?\s+(\w+)\(',
        re.MULTILINE,
    )

    for f in controller_files:
        try:
            content = read_file(f)
            class_match = class_re.search(content)
            if not class_match:
                continue

            controller_name = class_match.group(1)
            route_match = route_attr_re.search(content)
            base_route = route_match.group(1) if route_match else "api/[controller]"

            endpoints: list[dict[str, str]] = []
            for ep_match in http_method_re.finditer(content):
                verb = ep_match.group(1).upper()
                sub_route = ep_match.group(2) or ""
                return_type = ep_match.group(3)
                method_name = ep_match.group(4)
                
                full_path = f"{base_route}/{sub_route}".strip("/").replace("//", "/")
                endpoints.append({
                    "verb": verb,
                    "path": full_path,
                    "action": method_name,
                    "return_type": return_type,
                })

            controllers.append({
                "name": controller_name,
                "file": str(f),
                "base_route": base_route,
                "endpoints": endpoints,
            })
        except Exception as e:
            logger.debug("Failed parsing controller in %s: %s", f, e)

    return controllers


def analyze_frontend_routes(frontend_path: str | Path) -> list[dict[str, Any]]:
    """Identify Next.js App Router or Pages Router routes."""
    base = Path(frontend_path)
    if not base.exists():
        return []

    routes: list[dict[str, Any]] = []
    # Next.js App router: app/**/page.tsx
    app_pages = list(base.glob("**/app/**/page.tsx")) + list(base.glob("**/app/**/page.jsx"))
    for page in app_pages:
        try:
            rel = page.relative_to(base)
            route_parts = [p for p in rel.parts if p not in ("app", "page.tsx", "page.jsx", "src")]
            route_path = "/" + "/".join(route_parts)
            routes.append({
                "type": "AppRouter",
                "route": route_path,
                "file": str(rel),
            })
        except Exception:
            pass

    return routes


def find_related_features(repo_path: str | Path, feature_keywords: list[str]) -> list[str]:
    """Find existing repository files mentioning feature keywords."""
    base = Path(repo_path)
    if not base.exists():
        return []

    matched_files: set[str] = set()
    files = list_files(base, pattern="*.cs") + list_files(base, pattern="*.ts*")
    
    lowered_keywords = [k.lower() for k in feature_keywords if len(k) > 3]
    if not lowered_keywords:
        return []

    for f in files:
        try:
            stem_lower = f.stem.lower()
            if any(k in stem_lower for k in lowered_keywords):
                matched_files.add(str(f.relative_to(base)))
                if len(matched_files) >= 30:
                    break
        except Exception:
            continue

    return sorted(matched_files)


def get_dependency_graph(repo_path: str | Path) -> dict[str, list[str]]:
    """Map inter-project dependencies in the solution."""
    analysis = analyze_solution(repo_path)
    graph: dict[str, list[str]] = {}
    for p in analysis.get("projects", []):
        graph[p["name"]] = p.get("references", [])
    return graph
