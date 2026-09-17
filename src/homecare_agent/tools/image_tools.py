# Author: C A B M
# Date: 2026-09-17

"""Image processing tools for UI wireframe and screenshot analysis."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_image_metadata(image_path: str | Path) -> dict[str, Any]:
    """Extract basic dimensions and format using PIL."""
    from PIL import Image

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    with Image.open(path) as img:
        return {
            "path": str(path),
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": path.stat().st_size,
        }


def encode_image_to_base64(image_path: str | Path) -> str:
    """Encode an image file to a base64 data string."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_data_uri(image_path: str | Path) -> str:
    """Get a data URI string (e.g. data:image/png;base64,...) for LLM vision input."""
    path = Path(image_path)
    ext = path.suffix.lower().lstrip(".")
    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    b64 = encode_image_to_base64(path)
    return f"data:{mime_type};base64,{b64}"


async def analyze_wireframe(
    image_path: str | Path,
    llm_provider: Any = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Analyze a UI wireframe/screenshot using multimodal vision LLM.

    Extracts:
    - Detected components (forms, tables, buttons, navigation, modals)
    - Data fields and validations
    - Layout hierarchy and user flow
    """
    metadata = get_image_metadata(image_path)
    
    if llm_provider is None:
        # Return metadata summary if no LLM provider provided
        return {
            "metadata": metadata,
            "detected_components": ["Navigation", "Data Table", "Action Buttons", "Filter Bar"],
            "notes": "Vision model not invoked; default metadata returned.",
        }

    user_prompt = prompt or (
        "Analyze this UI wireframe for an enterprise healthcare platform. "
        "List all interactive UI components, tables, form fields, actions, and user flows shown. "
        "Return structured findings."
    )

    data_uri = get_image_data_uri(image_path)
    
    # LangChain ChatOpenAI multimodal message format
    from langchain_core.messages import HumanMessage

    content: list[dict[str, Any]] = [
        {"type": "text", "text": user_prompt},
        {"type": "image_url", "image_url": {"url": data_uri}},
    ]
    
    try:
        response = await llm_provider.ainvoke_vision([HumanMessage(content=content)])
        return {
            "metadata": metadata,
            "analysis": response.content if hasattr(response, "content") else str(response),
        }
    except Exception as e:
        logger.error("Failed to analyze wireframe %s: %s", image_path, e, exc_info=True)
        return {
            "metadata": metadata,
            "error": str(e),
            "notes": f"Vision analysis failed: {e}",
        }
