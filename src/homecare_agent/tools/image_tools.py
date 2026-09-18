# Author: C A B M
# Date: 2026-09-17

"""Image processing tools for UI wireframe and screenshot analysis."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _fetch_image_bytes(image_path: str | Path) -> tuple[bytes, str]:
    """Fetch bytes and content type from local file or remote URL."""
    str_path = str(image_path).strip()
    if str_path.startswith("data:"):
        header, b64_part = str_path.split(",", 1)
        mime = header.split(";")[0].replace("data:", "") or "image/png"
        return base64.b64decode(b64_part), mime
    if str_path.startswith(("http://", "https://")):
        import httpx
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(str_path)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            return resp.content, (ctype if ctype.startswith("image/") else "image/png")
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    ext = path.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return path.read_bytes(), mime


def get_image_metadata(image_path: str | Path) -> dict[str, Any]:
    """Extract basic dimensions and format using PIL (supports local files and URLs)."""
    import io
    from PIL import Image

    img_bytes, mime = _fetch_image_bytes(image_path)
    with Image.open(io.BytesIO(img_bytes)) as img:
        return {
            "path": str(image_path),
            "format": img.format or mime.split("/")[-1].upper(),
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": len(img_bytes),
        }


def encode_image_to_base64(image_path: str | Path) -> str:
    """Encode an image file or remote URL to a base64 data string."""
    img_bytes, _ = _fetch_image_bytes(image_path)
    return base64.b64encode(img_bytes).decode("utf-8")


def get_image_data_uri(image_path: str | Path) -> str:
    """Get a data URI string (e.g. data:image/png;base64,...) for LLM vision input."""
    str_path = str(image_path).strip()
    if str_path.startswith("data:"):
        return str_path
    img_bytes, mime = _fetch_image_bytes(image_path)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


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
