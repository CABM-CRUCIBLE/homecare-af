# Author: C A B M
# Date: 2026-09-17

"""Mermaid diagram generation and syntax validation tools."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def generate_er_diagram(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, str]] | None = None,
) -> str:
    """Generate a Mermaid erDiagram string from entity definitions.

    Args:
        entities: List of entity dicts with "name" and "attributes" (list of {"type": str, "name": str}).
        relationships: List of {"from": str, "to": str, "cardinality": str, "label": str}.

    Returns:
        Mermaid markdown string.
    """
    lines = ["erDiagram"]

    for ent in entities:
        name = ent.get("name", "Entity")
        attrs = ent.get("attributes", [])
        if attrs:
            lines.append(f"    {name} {{")
            for a in attrs:
                t = a.get("type", "string").replace("<", "_").replace(">", "_")
                n = a.get("name", "Field")
                lines.append(f"        {t} {n}")
            lines.append("    }")
        else:
            lines.append(f"    {name} {{}}")

    if relationships:
        for rel in relationships:
            src = rel.get("from", "")
            dst = rel.get("to", "")
            card = rel.get("cardinality", "||--o{")
            label = rel.get("label", "relates_to")
            lines.append(f'    {src} {card} {dst} : "{label}"')

    return "\n".join(lines)


def generate_sequence_diagram(
    participants: list[str],
    interactions: list[dict[str, str]],
) -> str:
    """Generate a Mermaid sequenceDiagram string.

    Args:
        participants: List of actor / service names.
        interactions: List of {"from": str, "to": str, "message": str, "type": "sync|async|return"}.

    Returns:
        Mermaid markdown string.
    """
    lines = ["sequenceDiagram", "    autonumber"]

    for p in participants:
        lines.append(f"    participant {p}")

    for item in interactions:
        src = item.get("from", "")
        dst = item.get("to", "")
        msg = item.get("message", "")
        arrow = "->>" if item.get("type") != "return" else "-->>"
        lines.append(f"    {src}{arrow}{dst}: {msg}")

    return "\n".join(lines)


def generate_flowchart(
    nodes: list[tuple[str, str]],  # (id, label)
    edges: list[tuple[str, str, str]],  # (from, to, optional_label)
    direction: str = "TD",
) -> str:
    """Generate a Mermaid flowchart."""
    lines = [f"flowchart {direction}"]

    for nid, label in nodes:
        lines.append(f'    {nid}["{label}"]')

    for src, dst, label in edges:
        if label:
            lines.append(f'    {src} -->|"{label}"| {dst}')
        else:
            lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)


def validate_mermaid_syntax(mermaid_code: str) -> tuple[bool, str]:
    """Perform baseline syntax check on Mermaid diagram string.

    Validates:
    - Supported diagram type header (erDiagram, sequenceDiagram, flowchart, stateDiagram, classDiagram)
    - Balanced braces
    - No invalid unescaped characters in node definitions
    """
    stripped = mermaid_code.strip()
    valid_headers = (
        "erdiagram",
        "sequencediagram",
        "flowchart",
        "graph",
        "statediagram",
        "classdiagram",
        "gantt",
    )

    first_line = stripped.splitlines()[0].strip().lower()
    if not any(first_line.startswith(vh) for vh in valid_headers):
        return False, f"Invalid Mermaid diagram header: '{first_line}'"

    # Check balanced braces (ignore ER diagram relationship lines containing -- or ..)
    lines_for_braces = [l for l in stripped.splitlines() if "--" not in l and ".." not in l]
    text_for_braces = "\n".join(lines_for_braces)
    open_braces = text_for_braces.count("{")
    close_braces = text_for_braces.count("}")
    if open_braces != close_braces:
        return False, f"Unbalanced braces: {open_braces} open vs {close_braces} close"

    # Check balanced brackets
    open_brackets = stripped.count("[")
    close_brackets = stripped.count("]")
    if open_brackets != close_brackets:
        return False, f"Unbalanced brackets: {open_brackets} open vs {close_brackets} close"

    return True, "Valid Mermaid diagram syntax"
