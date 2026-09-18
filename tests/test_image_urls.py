# Author: C A B M
# Date: 2026-09-17

"""Tests for Image URL functionality across vision, image tools, documentation, and web UI."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.nodes.documentation import save_architecture_documents
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider
from homecare_agent.tools.image_tools import (
    encode_image_to_base64,
    get_image_data_uri,
    get_image_metadata,
)


def _create_minimal_png_bytes() -> bytes:
    """Return valid 1x1 PNG bytes."""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


def test_image_tools_with_data_uri() -> None:
    """Verify image tools handle data: URIs directly."""
    png_bytes = _create_minimal_png_bytes()
    b64_str = base64.b64encode(png_bytes).decode()
    data_uri = f"data:image/png;base64,{b64_str}"

    meta = get_image_metadata(data_uri)
    assert meta["width"] == 1
    assert meta["height"] == 1
    assert meta["size_bytes"] == len(png_bytes)

    assert encode_image_to_base64(data_uri) == b64_str
    assert get_image_data_uri(data_uri) == data_uri


def test_image_tools_with_http_url() -> None:
    """Verify image tools download and parse remote image URLs."""
    png_bytes = _create_minimal_png_bytes()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = png_bytes
    mock_resp.headers = {"content-type": "image/png"}

    with patch("httpx.Client.get", return_value=mock_resp):
        url = "https://example.com/test_wireframe.png"
        meta = get_image_metadata(url)
        assert meta["width"] == 1
        assert meta["height"] == 1
        assert meta["format"] in ("PNG", "image/png")

        b64 = encode_image_to_base64(url)
        assert b64 == base64.b64encode(png_bytes).decode()

        uri = get_image_data_uri(url)
        assert uri.startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_ainvoke_with_vision_converts_http_urls_to_base64() -> None:
    """Verify provider.ainvoke_with_vision pre-fetches HTTP URLs into base64 data URIs."""
    settings = Settings(openrouter_api_key="sk-test", langfuse_enabled=False)
    provider = LLMProvider(settings)

    png_bytes = _create_minimal_png_bytes()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = png_bytes
    mock_resp.headers = {"content-type": "image/png"}

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Wireframe analysis successful"))
    provider._vision_llm = mock_llm

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        
        result = await provider.ainvoke_with_vision(
            prompt="Analyze this screen",
            image_urls=["https://example.com/dashboard_mockup.png"],
        )
        assert result == "Wireframe analysis successful"

        # Check call args to verify image_url converted to base64 data URI
        call_args = mock_llm.ainvoke.call_args[0][0]
        human_message = call_args[0]
        content_items = human_message.content
        assert len(content_items) == 2
        assert content_items[0]["type"] == "text"
        assert content_items[1]["type"] == "image_url"
        url_sent = content_items[1]["image_url"]["url"]
        assert url_sent.startswith("data:image/png;base64,")


def test_documentation_archives_wireframe_urls(tmp_path: Path) -> None:
    """Verify save_architecture_documents records wireframe URLs in Resources/WIREFRAMES.md."""
    state: AgentState = {
        "repo_path": str(tmp_path),
        "feature_name": "Telehealth Video Consultation",
        "strategy_document": "# Telehealth Strategy",
        "wireframe_urls": [
            "https://mockups.example.com/video_room.png",
            "https://mockups.example.com/waiting_area.png",
        ],
    }
    settings = Settings(repo_path=str(tmp_path))

    png_bytes = _create_minimal_png_bytes()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = png_bytes
    mock_resp.headers = {"content-type": "image/png"}

    with patch("httpx.Client.get", return_value=mock_resp):
        written = save_architecture_documents(state, settings)

    target_dir = tmp_path / "docs" / "architecture" / "telehealth-video-consultation"
    links_file = target_dir / "Resources" / "WIREFRAMES.md"
    assert links_file.exists()
    content = links_file.read_text(encoding="utf-8")
    assert "https://mockups.example.com/video_room.png" in content
    assert "https://mockups.example.com/waiting_area.png" in content

    # Verify downloaded image copies
    img1 = target_dir / "Resources" / "wireframe_url_1.png"
    assert img1.exists()
    assert img1.read_bytes() == png_bytes
