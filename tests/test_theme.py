# Author: C A B M
# Date: 2026-09-17

"""Tests for UI theming and Executive Glassmorphism (Crucible) design system."""

from __future__ import annotations

import unittest.mock as mock
from homecare_agent.config import Settings
from homecare_agent.ui.theme import (
    CrucibleTheme,
    JarvisTheme,
    get_theme_bundle,
    list_available_themes,
    THEMES,
)
from homecare_agent.ui.web import create_web_ui, launch_web_ui


def test_theme_bundle_resolution_crucible_and_jarvis() -> None:
    """Verify that 'crucible' and 'jarvis' themes resolve to CrucibleTheme with custom CSS and fonts."""
    theme_obj, css, head = get_theme_bundle("crucible")
    assert isinstance(theme_obj, CrucibleTheme)
    assert "Plus Jakarta Sans" in css
    assert "JetBrains Mono" in css
    assert "#0a0a0c" in css
    assert "crucible-header-strip" in css
    assert "<link rel=\"preconnect\"" in head

    # Backward compatibility alias
    theme_alias, _, _ = get_theme_bundle("jarvis")
    assert isinstance(theme_alias, CrucibleTheme)
    assert isinstance(theme_alias, JarvisTheme)


def test_theme_bundle_resolution_soft_and_default() -> None:
    """Verify that 'soft' and 'default' themes resolve properly for theme switching."""
    theme_soft, css_soft, _ = get_theme_bundle("soft")
    assert theme_soft is not None
    assert css_soft == ""

    theme_default, css_default, _ = get_theme_bundle("default")
    assert theme_default is not None
    assert css_default == ""


def test_theme_bundle_fallback_to_crucible() -> None:
    """Verify that unknown theme names fallback safely to the crucible theme."""
    theme_obj, css, _ = get_theme_bundle("non_existent_theme")
    assert isinstance(theme_obj, CrucibleTheme)
    assert len(css) > 0


def test_list_available_themes() -> None:
    """Verify listing available themes provides labels and valid keys."""
    themes = list_available_themes()
    assert len(themes) >= 3
    keys = [k for _, k in themes]
    assert "crucible" in keys
    assert "jarvis" in keys
    assert "soft" in keys
    assert "default" in keys


def test_settings_ui_theme_default_and_override() -> None:
    """Verify Settings includes ui_theme defaulting to 'crucible'."""
    settings = Settings(openrouter_api_key="test-key")
    assert settings.ui_theme == "crucible"

    settings_custom = Settings(openrouter_api_key="test-key", ui_theme="soft")
    assert settings_custom.ui_theme == "soft"


def test_create_web_ui_builds_blocks() -> None:
    """Verify that create_web_ui constructs Gradio Blocks with executive layout."""
    settings = Settings(openrouter_api_key="test-key")
    demo = create_web_ui(settings)
    assert demo is not None


def test_launch_web_ui_passes_theme_bundle() -> None:
    """Verify launch_web_ui passes theme, css, and head to demo.launch."""
    settings = Settings(openrouter_api_key="test-key", ui_theme="crucible")
    with mock.patch("gradio.Blocks.launch") as mock_launch:
        launch_web_ui(settings)
        assert mock_launch.called
        kwargs = mock_launch.call_args[1]
        assert "theme" in kwargs
        assert isinstance(kwargs["theme"], CrucibleTheme)
        assert "css" in kwargs
        assert "head" in kwargs
        assert kwargs["server_port"] == 7860
