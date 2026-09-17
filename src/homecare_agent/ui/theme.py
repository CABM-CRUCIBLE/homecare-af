# Author: C A B M
# Date: 2026-09-17

"""Theme management and Executive Glassmorphism (Crucible) styling.

Provides easily swappable themes for the Gradio Web UI, featuring
the 'Professional Futurist' Executive Glassmorphism design system
(Crucible) with optimal readability, high contrast,
and breathable executive layouts.
"""

from __future__ import annotations

import inspect
from typing import Any
import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class CrucibleTheme(Base):
    """Crucible Executive Glassmorphism Theme.

    Deep navy-charcoal background (#080c14), translucent glass panels
    (rgba(15, 23, 42, 0.8)), crisp sky-blue accents (#38bdf8), and
    ultra-legible typography combining Plus Jakarta Sans with JetBrains Mono.
    """

    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.sky,
        secondary_hue: colors.Color | str = colors.slate,
        neutral_hue: colors.Color | str = colors.slate,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_lg,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | list[fonts.Font | str] = (
            fonts.GoogleFont("Plus Jakarta Sans"),
            "system-ui",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | list[fonts.Font | str] = (
            fonts.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )

        valid_params = set(inspect.signature(Base.set).parameters.keys())

        raw_props = dict(
            # Backgrounds — Rich deep navy-charcoal with clear contrast
            body_background_fill="#080c14",
            body_background_fill_dark="#080c14",
            block_background_fill="rgba(15, 23, 42, 0.7)",
            block_background_fill_dark="rgba(15, 23, 42, 0.7)",
            panel_background_fill="rgba(15, 23, 42, 0.8)",
            panel_background_fill_dark="rgba(15, 23, 42, 0.8)",
            # Borders — Crisp, well-defined boundaries
            block_border_color="rgba(148, 163, 184, 0.16)",
            block_border_color_dark="rgba(148, 163, 184, 0.16)",
            block_border_width="1px",
            panel_border_color="rgba(148, 163, 184, 0.16)",
            panel_border_color_dark="rgba(148, 163, 184, 0.16)",
            panel_border_width="1px",
            border_color_primary="rgba(56, 189, 248, 0.25)",
            border_color_primary_dark="rgba(56, 189, 248, 0.25)",
            # Radii
            block_radius="16px",
            container_radius="20px",
            # Shadows
            block_shadow="0 8px 30px rgba(0, 0, 0, 0.4)",
            block_shadow_dark="0 8px 30px rgba(0, 0, 0, 0.4)",
            # Typography & text — Pure white & bright slate for effortless reading
            body_text_color="#f8fafc",
            body_text_color_dark="#f8fafc",
            body_text_color_subdued="#94a3b8",
            body_text_color_subdued_dark="#94a3b8",
            block_title_text_color="#ffffff",
            block_title_text_color_dark="#ffffff",
            block_label_text_color="#f1f5f9",
            block_label_text_color_dark="#f1f5f9",
            # Inputs
            input_background_fill="rgba(11, 17, 32, 0.9)",
            input_background_fill_dark="rgba(11, 17, 32, 0.9)",
            input_border_color="rgba(148, 163, 184, 0.24)",
            input_border_color_dark="rgba(148, 163, 184, 0.24)",
            input_border_color_focus="#38bdf8",
            input_border_color_focus_dark="#38bdf8",
            input_radius="12px",
            # Buttons
            button_primary_background_fill="linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
            button_primary_background_fill_dark="linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
            button_primary_text_color="#ffffff",
            button_primary_text_color_dark="#ffffff",
            button_primary_border_color="rgba(56, 189, 248, 0.4)",
            button_primary_border_color_dark="rgba(56, 189, 248, 0.4)",
            button_secondary_background_fill="rgba(30, 41, 59, 0.8)",
            button_secondary_background_fill_dark="rgba(30, 41, 59, 0.8)",
            button_secondary_text_color="#f8fafc",
            button_secondary_text_color_dark="#f8fafc",
            button_secondary_border_color="rgba(148, 163, 184, 0.2)",
            button_secondary_border_color_dark="rgba(148, 163, 184, 0.2)",
            # Sliders & Progress
            slider_color="#38bdf8",
            slider_color_dark="#38bdf8",
        )
        safe_props = {k: v for k, v in raw_props.items() if k in valid_params}
        self.set(**safe_props)


# Backward-compatible alias
JarvisTheme = CrucibleTheme


CRUCIBLE_CSS = """
/* ==========================================================================
   CRUCIBLE — Executive Glassmorphism (High-Legibility Edition)
   Clean Contrast, Elevated Glass Surfaces, Breathable Typography
   ========================================================================== */

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --bg-deep: #080c14;
  --bg-core: #0a0a0c;
  --glass-card: rgba(15, 23, 42, 0.82);
  --glass-panel: rgba(15, 23, 42, 0.9);
  --glass-border: 1px solid rgba(148, 163, 184, 0.24);
  --glass-border-cyan: 1px solid rgba(56, 189, 248, 0.4);
  --cyan-accent: #38bdf8;
  --cyan-glow: rgba(56, 189, 248, 0.25);
  --emerald-accent: #4ade80;
  --text-pure: #ffffff;
  --text-high: #f8fafc;
  --text-medium: #e2e8f0;
  --text-muted: #cbd5e1;
  --font-main: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}

html, body {
  background-color: var(--bg-deep) !important;
  margin: 0 !important;
  padding: 0 !important;
  min-height: 100vh !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

.gradio-container {
  background-color: var(--bg-deep) !important;
  background-image: radial-gradient(circle at 50% 0%, rgba(14, 165, 233, 0.1) 0%, transparent 60%) !important;
  color: var(--text-high) !important;
  font-family: var(--font-main) !important;
  padding: 14px 24px 46px 24px !important;
  box-sizing: border-box !important;
  min-height: 100vh !important;
  width: 100% !important;
  max-width: 100% !important;
  overflow-y: visible !important;
}

/* ==========================================================================
   High-Contrast Typography & Label Hierarchy
   ========================================================================== */

/* Universal Form Labels */
.gradio-container label,
.gradio-container label span,
.gradio-container .block-title,
.gradio-container span.label-text,
.gradio-container .accordion-title,
.gradio-container summary {
  color: #ffffff !important;
  font-size: 0.98rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em !important;
  margin-bottom: 6px !important;
}

/* Helper / Info Text below inputs */
.gradio-container span[data-testid="block-info"],
.gradio-container .info,
.gradio-container .subdued {
  color: #93c5fd !important;
  font-size: 0.88rem !important;
  font-weight: 500 !important;
  line-height: 1.45 !important;
  opacity: 1 !important;
  margin-top: 4px !important;
}

/* Headings */
h1, h2, h3, h4, .gradio-container h1, .gradio-container h2, .gradio-container h3 {
  color: var(--text-pure) !important;
  font-family: var(--font-main) !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
}

p, li, .gradio-container p, .gradio-container li {
  color: var(--text-medium) !important;
  font-size: 0.98rem !important;
  line-height: 1.65 !important;
}

/* ==========================================================================
   Elevated Glass Cards & Tab Panels (Comfortable Padding, Zero Border Clutter)
   ========================================================================== */

/* Universal Tab Item Panels — 34px horizontal & 30px vertical padding prevents any text cut-off */
.gradio-container .tabitem,
.gradio-container div[role="tabpanel"],
div.tabitem {
  background: var(--glass-card) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 20px !important;
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.45) !important;
  padding: 30px 36px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}

/* Remove all ugly nested borders, outlines, and box backgrounds from markdown/blocks inside tabs */
.gradio-container .tabitem .block,
.gradio-container .tabitem .markdown,
.gradio-container .tabitem .prose,
.gradio-container .tabitem div[data-testid="markdown"],
.gradio-container .tabitem .output-markdown,
.gradio-container .tabitem .form,
.tabitem .block:has(.prose),
.tabitem .block:has(.markdown) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  padding: 0 !important;
}

/* Give all prose and markdown text generous indentation and high readability */
.gradio-container .tabitem .prose,
.gradio-container .tabitem .markdown,
.gradio-container .tabitem div[data-testid="markdown"] {
  padding: 6px 8px !important;
  margin-bottom: 16px !important;
}

.gradio-container .tabitem .prose h1,
.gradio-container .tabitem .prose h2,
.gradio-container .tabitem .prose h3,
.gradio-container .tabitem .markdown h3 {
  margin-top: 0 !important;
  margin-bottom: 12px !important;
  padding-left: 0 !important;
  font-size: 1.25rem !important;
  font-weight: 800 !important;
  color: #ffffff !important;
  letter-spacing: -0.01em !important;
}

.gradio-container .tabitem .prose p,
.gradio-container .tabitem .markdown p,
.gradio-container .tabitem .prose em,
.gradio-container .tabitem .markdown em {
  font-size: 1.02rem !important;
  line-height: 1.65 !important;
  color: #e2e8f0 !important;
}

/* Clean, modern tables without harsh border grids */
.gradio-container table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  background: rgba(11, 18, 34, 0.5) !important;
  margin: 16px 0 !important;
}

.gradio-container th {
  background: rgba(30, 41, 59, 0.75) !important;
  color: #ffffff !important;
  font-size: 0.88rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  padding: 12px 18px !important;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-left: none !important;
  border-right: none !important;
  border-top: none !important;
}

.gradio-container td {
  padding: 12px 18px !important;
  font-size: 0.93rem !important;
  color: var(--text-medium) !important;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12) !important;
  border-left: none !important;
  border-right: none !important;
  border-top: none !important;
}

.gradio-container tr:last-child td {
  border-bottom: none !important;
}

.gradio-container tr:hover td {
  background: rgba(56, 189, 248, 0.04) !important;
}

/* Sliders inside Execution tab */
.tabitem .slider,
.tabitem [data-testid="slider"] {
  background: rgba(11, 18, 34, 0.65) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 14px !important;
  padding: 16px 20px !important;
  margin-top: 16px !important;
}

/* ==========================================================================
   Clean, High-Readability Form Inputs & Textareas
   ========================================================================== */

.gradio-container input,
.gradio-container textarea,
.gradio-container select,
.gradio-container .dropdown-container,
.gradio-container .gr-box {
  background-color: #0b1222 !important;
  border: 1.5px solid rgba(148, 163, 184, 0.3) !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  font-family: var(--font-main) !important;
  font-size: 1rem !important;
  font-weight: 500 !important;
  padding: 12px 16px !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder,
.gradio-container .placeholder {
  color: #94a3b8 !important;
  font-size: 0.95rem !important;
  opacity: 1 !important;
}

.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
  background-color: #0d1629 !important;
  border-color: var(--cyan-accent) !important;
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.3) !important;
  outline: none !important;
}

/* Dropdown Menu Items */
.gradio-container ul.options,
.gradio-container .dropdown-list {
  background-color: #0b1222 !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
}

.gradio-container ul.options li,
.gradio-container .dropdown-list li {
  color: #f8fafc !important;
  font-size: 0.95rem !important;
}

.gradio-container ul.options li:hover,
.gradio-container .dropdown-list li:hover {
  background-color: #0284c7 !important;
  color: #ffffff !important;
}

/* Accordions */
.gradio-container .accordion,
.gradio-container details {
  background: rgba(15, 23, 42, 0.8) !important;
  border: 1px solid rgba(148, 163, 184, 0.25) !important;
  border-radius: 14px !important;
  margin-bottom: 14px !important;
  overflow: hidden !important;
}

.gradio-container summary {
  padding: 14px 18px !important;
  color: #ffffff !important;
  font-weight: 700 !important;
  font-size: 0.98rem !important;
  cursor: pointer !important;
  background: rgba(15, 23, 42, 0.6) !important;
  transition: background-color 0.2s ease !important;
}

.gradio-container summary:hover {
  background: rgba(56, 189, 248, 0.1) !important;
  color: #38bdf8 !important;
}

/* Fix File Upload Dropzone */
.gradio-container [data-testid="file-upload"],
.gradio-container .file-upload,
.gradio-container .upload-container,
.gradio-container .file-preview-holder {
  background: rgba(15, 23, 42, 0.75) !important;
  border: 1.5px dashed rgba(56, 189, 248, 0.45) !important;
  border-radius: 14px !important;
  padding: 24px !important;
}

.gradio-container [data-testid="file-upload"] *,
.gradio-container .upload-container * {
  background-color: transparent !important;
  color: #ffffff !important;
}

/* ==========================================================================
   Modern Segmented Navigation Tabs (Crucible Main Tabs - Fully Rounded & Neon Green)
   ========================================================================== */

.crucible-main-tabs,
.gradio-container .tabs {
  margin-bottom: 22px !important;
}

.crucible-main-tabs > .tab-nav,
.crucible-main-tabs > div[role="tablist"],
.gradio-container .tabs > .tab-nav,
.gradio-container .tabs > div[role="tablist"],
.gradio-container .tab-nav,
.gradio-container div[role="tablist"],
div.tabs > div.tab-nav {
  background: transparent !important;
  border: none !important;
  border-bottom: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  margin-bottom: 20px !important;
  display: flex !important;
  gap: 0 !important;
  width: 100% !important;
  box-sizing: border-box !important;
  box-shadow: none !important;
}

/* Remove any Gradio pseudo-elements that create square lines or artifacts */
.crucible-main-tabs button::before,
.crucible-main-tabs button::after,
.tab-nav button::before,
.tab-nav button::after,
button[role="tab"]::before,
button[role="tab"]::after {
  display: none !important;
  content: none !important;
}

/* Tab buttons: Contiguous segmented bar, 54px height, crisp text */
.crucible-main-tabs > .tab-nav button,
.crucible-main-tabs > div[role="tablist"] button,
.crucible-main-tabs button[role="tab"],
.gradio-container .tabs > .tab-nav button,
.gradio-container .tabs > div[role="tablist"] button,
.gradio-container .tab-nav button,
.gradio-container button[role="tab"],
div.tabs > div.tab-nav > button {
  min-height: 54px !important;
  height: 54px !important;
  padding: 0 16px !important;
  flex: 1 1 0 !important;
  min-width: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  cursor: pointer !important;
  box-sizing: border-box !important;
  margin: 0 !important;

  /* Crisp typography */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
  font-weight: 700 !important;
  font-size: 1.02rem !important;
  letter-spacing: normal !important;
  color: #f1f5f9 !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
  text-rendering: geometricPrecision !important;
  text-shadow: none !important;
  filter: none !important;

  /* Contiguous segmented style: straight in middle, single border divider */
  border-radius: 0 !important;
  -webkit-border-radius: 0 !important;
  border: 1.5px solid rgba(148, 163, 184, 0.28) !important;
  border-right: none !important;
  background: rgba(15, 23, 42, 0.85) !important;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease !important;
  transform: none !important;
  position: relative !important;
}

/* Rounded off at the outer left end (first tab) */
.crucible-main-tabs > .tab-nav button:first-child,
.crucible-main-tabs > .tab-nav button:first-of-type,
.crucible-main-tabs > div[role="tablist"] button:first-child,
.crucible-main-tabs > div[role="tablist"] button:first-of-type,
.gradio-container .tab-nav button:first-child,
.gradio-container .tab-nav button:first-of-type,
div.tabs > div.tab-nav > button:first-child,
div.tabs > div.tab-nav > button:first-of-type {
  border-top-left-radius: 9999px !important;
  border-bottom-left-radius: 9999px !important;
  -webkit-border-top-left-radius: 9999px !important;
  -webkit-border-bottom-left-radius: 9999px !important;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  -webkit-border-top-right-radius: 0 !important;
  -webkit-border-bottom-right-radius: 0 !important;
}

/* Rounded off at the outer right end (last tab) */
.crucible-main-tabs > .tab-nav button:last-child,
.crucible-main-tabs > .tab-nav button:last-of-type,
.crucible-main-tabs > div[role="tablist"] button:last-child,
.crucible-main-tabs > div[role="tablist"] button:last-of-type,
.gradio-container .tab-nav button:last-child,
.gradio-container .tab-nav button:last-of-type,
div.tabs > div.tab-nav > button:last-child,
div.tabs > div.tab-nav > button:last-of-type {
  border-top-right-radius: 9999px !important;
  border-bottom-right-radius: 9999px !important;
  -webkit-border-top-right-radius: 9999px !important;
  -webkit-border-bottom-right-radius: 9999px !important;
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  -webkit-border-top-left-radius: 0 !important;
  -webkit-border-bottom-left-radius: 0 !important;
  border-right: 1.5px solid rgba(148, 163, 184, 0.28) !important;
}

.crucible-main-tabs > .tab-nav button:hover,
.crucible-main-tabs > div[role="tablist"] button:hover,
.gradio-container button[role="tab"]:hover,
div.tabs > div.tab-nav > button:hover {
  color: #ffffff !important;
  background: rgba(30, 41, 59, 0.95) !important;
  z-index: 1 !important;
}

/* Tab Selected Active State: ONLINE Badge Color Scheme in contiguous bar */
.crucible-main-tabs > .tab-nav button.selected,
.crucible-main-tabs > div[role="tablist"] button.selected,
.crucible-main-tabs button[role="tab"][aria-selected="true"],
.gradio-container button[role="tab"][aria-selected="true"],
.gradio-container .tab-nav button.selected,
div.tabs > div.tab-nav > button.selected,
div.tabs > div.tab-nav > button[aria-selected="true"] {
  color: #4ade80 !important;
  background: rgba(74, 222, 128, 0.15) !important;
  border: 1.5px solid rgba(74, 222, 128, 0.5) !important;
  border-right: 1.5px solid rgba(74, 222, 128, 0.5) !important;
  font-weight: 700 !important;
  font-size: 1.02rem !important;
  letter-spacing: normal !important;
  box-shadow: 0 0 14px rgba(74, 222, 128, 0.25) !important;
  text-shadow: none !important;
  transform: none !important;
  z-index: 2 !important;
  margin-right: -1px !important;
}

/* Ensure active tab preserves outer rounded ends if first or last */
.crucible-main-tabs > .tab-nav button:first-child.selected,
.crucible-main-tabs > .tab-nav button:first-of-type.selected,
.crucible-main-tabs > div[role="tablist"] button:first-child.selected,
.crucible-main-tabs > div[role="tablist"] button:first-of-type.selected,
.gradio-container .tab-nav button:first-child.selected,
.gradio-container .tab-nav button:first-of-type.selected,
div.tabs > div.tab-nav > button:first-child.selected,
div.tabs > div.tab-nav > button:first-of-type.selected {
  border-top-left-radius: 9999px !important;
  border-bottom-left-radius: 9999px !important;
  -webkit-border-top-left-radius: 9999px !important;
  -webkit-border-bottom-left-radius: 9999px !important;
}

.crucible-main-tabs > .tab-nav button:last-child.selected,
.crucible-main-tabs > .tab-nav button:last-of-type.selected,
.crucible-main-tabs > div[role="tablist"] button:last-child.selected,
.crucible-main-tabs > div[role="tablist"] button:last-of-type.selected,
.gradio-container .tab-nav button:last-child.selected,
.gradio-container .tab-nav button:last-of-type.selected,
div.tabs > div.tab-nav > button:last-child.selected,
div.tabs > div.tab-nav > button:last-of-type.selected {
  border-top-right-radius: 9999px !important;
  border-bottom-right-radius: 9999px !important;
  -webkit-border-top-right-radius: 9999px !important;
  -webkit-border-bottom-right-radius: 9999px !important;
  margin-right: 0 !important;
}

/* Nested Subtabs inside Architecture Tab (Strategy, Tactical Plan, ADRs, Review) */
.tabitem .tabs,
.tabitem div.tabs {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  margin-bottom: 16px !important;
}

.tabitem .tabs > .tab-nav,
.tabitem .tabs > div[role="tablist"] {
  background: transparent !important;
  border: none !important;
  border-bottom: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  margin-bottom: 18px !important;
  gap: 0 !important;
  box-shadow: none !important;
  display: flex !important;
  width: 100% !important;
}

.tabitem .tabs > .tab-nav button,
.tabitem .tabs > div[role="tablist"] button {
  min-height: 44px !important;
  height: 44px !important;
  padding: 0 16px !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  border-radius: 0 !important;
  -webkit-border-radius: 0 !important;
  border: 1.5px solid rgba(148, 163, 184, 0.22) !important;
  border-right: none !important;
  background: rgba(15, 23, 42, 0.8) !important;
  color: #f1f5f9 !important;
  flex: 1 1 0 !important;
  min-width: 0 !important;
  margin: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
  position: relative !important;
  transform: none !important;
}

.tabitem .tabs > .tab-nav button:first-child,
.tabitem .tabs > .tab-nav button:first-of-type,
.tabitem .tabs > div[role="tablist"] button:first-child,
.tabitem .tabs > div[role="tablist"] button:first-of-type {
  border-top-left-radius: 9999px !important;
  border-bottom-left-radius: 9999px !important;
  -webkit-border-top-left-radius: 9999px !important;
  -webkit-border-bottom-left-radius: 9999px !important;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.tabitem .tabs > .tab-nav button:last-child,
.tabitem .tabs > .tab-nav button:last-of-type,
.tabitem .tabs > div[role="tablist"] button:last-child,
.tabitem .tabs > div[role="tablist"] button:last-of-type {
  border-top-right-radius: 9999px !important;
  border-bottom-right-radius: 9999px !important;
  -webkit-border-top-right-radius: 9999px !important;
  -webkit-border-bottom-right-radius: 9999px !important;
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  border-right: 1.5px solid rgba(148, 163, 184, 0.22) !important;
}

.tabitem .tabs > .tab-nav button:hover,
.tabitem .tabs > div[role="tablist"] button:hover {
  color: #ffffff !important;
  background: rgba(30, 41, 59, 0.9) !important;
  z-index: 1 !important;
}

.tabitem .tabs > .tab-nav button.selected,
.tabitem .tabs > div[role="tablist"] button.selected {
  background: rgba(74, 222, 128, 0.15) !important;
  color: #4ade80 !important;
  font-weight: 700 !important;
  letter-spacing: normal !important;
  border: 1.5px solid rgba(74, 222, 128, 0.5) !important;
  border-right: 1.5px solid rgba(74, 222, 128, 0.5) !important;
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.25) !important;
  text-shadow: none !important;
  z-index: 2 !important;
  margin-right: -1px !important;
  transform: none !important;
}

.tabitem .tabs > .tab-nav button:first-child.selected,
.tabitem .tabs > .tab-nav button:first-of-type.selected,
.tabitem .tabs > div[role="tablist"] button:first-child.selected,
.tabitem .tabs > div[role="tablist"] button:first-of-type.selected {
  border-top-left-radius: 9999px !important;
  border-bottom-left-radius: 9999px !important;
  -webkit-border-top-left-radius: 9999px !important;
  -webkit-border-bottom-left-radius: 9999px !important;
}

.tabitem .tabs > .tab-nav button:last-child.selected,
.tabitem .tabs > .tab-nav button:last-of-type.selected,
.tabitem .tabs > div[role="tablist"] button:last-child.selected,
.tabitem .tabs > div[role="tablist"] button:last-of-type.selected {
  border-top-right-radius: 9999px !important;
  border-bottom-right-radius: 9999px !important;
  -webkit-border-top-right-radius: 9999px !important;
  -webkit-border-bottom-right-radius: 9999px !important;
  margin-right: 0 !important;
}

/* Sub-tab content panels have 0 outer box borders */
.tabitem .tabitem {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 8px 0 0 0 !important;
}

/* ==========================================================================
   Executive Top Bar / Header Strip
   ========================================================================== */

.crucible-header-strip,
.jarvis-top-bar {
  background: rgba(15, 23, 42, 0.85) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 14px !important;
  padding: 10px 20px !important;
  margin-bottom: 14px !important;
  backdrop-filter: blur(16px) !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35) !important;
}

.crucible-brand,
.jarvis-brand {
  font-size: 1.25rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em !important;
  color: #ffffff !important;
}

.crucible-clock-text,
.jarvis-clock-text {
  font-family: var(--font-mono) !important;
  font-size: 1.2rem !important;
  font-weight: 700 !important;
  color: var(--cyan-accent) !important;
  letter-spacing: 0.05em !important;
}

.crucible-status-bar,
.jarvis-status-bar {
  background: rgba(15, 23, 42, 0.85) !important;
  border: 1px solid rgba(148, 163, 184, 0.25) !important;
  border-radius: 14px !important;
  padding: 10px 18px !important;
}

/* Compact Metric Pills */
.metric-pill {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 4px 12px !important;
  border-radius: 20px !important;
  background: rgba(11, 18, 34, 0.8) !important;
  border: 1px solid rgba(148, 163, 184, 0.24) !important;
  font-family: var(--font-mono) !important;
  font-size: 0.82rem !important;
}

/* ==========================================================================
   Crucible Hero Form (Highlighted & Large Center Workspace)
   ========================================================================== */

.crucible-hero-form {
  background: rgba(15, 23, 42, 0.9) !important;
  border: 1.5px solid rgba(56, 189, 248, 0.45) !important;
  border-radius: 18px !important;
  padding: 24px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(56, 189, 248, 0.14) !important;
}

.crucible-hero-form input {
  font-size: 1.1rem !important;
  padding: 14px 18px !important;
  background-color: #0b1222 !important;
  border: 1.5px solid rgba(56, 189, 248, 0.35) !important;
}

.crucible-hero-form textarea {
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
  padding: 14px 18px !important;
  background-color: #0b1222 !important;
  border: 1.5px solid rgba(56, 189, 248, 0.35) !important;
}

/* Prominent CTA Button */
.crucible-launch-btn {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
  font-size: 1.15rem !important;
  letter-spacing: 0.03em !important;
  border-radius: 14px !important;
  border: 1.5px solid rgba(56, 189, 248, 0.6) !important;
  box-shadow: 0 6px 24px rgba(2, 132, 199, 0.5), 0 0 16px rgba(56, 189, 248, 0.3) !important;
  padding: 16px 32px !important;
  transition: all 0.2s ease !important;
}

.crucible-launch-btn:hover {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
  box-shadow: 0 8px 30px rgba(56, 189, 248, 0.6) !important;
  transform: translateY(-2px) !important;
}

/* ==========================================================================
   Intelligence Cards
   ========================================================================== */

.kpi-card {
  background: rgba(15, 23, 42, 0.85) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 16px !important;
  padding: 20px 22px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35) !important;
}

.kpi-card-cyan {
  border-left: 4px solid var(--cyan-accent) !important;
}

.kpi-card-green {
  border-left: 4px solid var(--emerald-accent) !important;
}

.kpi-title {
  font-size: 0.85rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  color: #93c5fd !important;
}

.kpi-value {
  font-family: var(--font-mono) !important;
  font-size: 1.85rem !important;
  font-weight: 800 !important;
  color: #ffffff !important;
  margin-top: 6px !important;
  margin-bottom: 8px !important;
}

.kpi-sub {
  font-size: 0.88rem !important;
  color: #cbd5e1 !important;
  line-height: 1.5 !important;
}

.kpi-sub strong {
  font-weight: 700 !important;
}

.badge-green {
  background: rgba(74, 222, 128, 0.18) !important;
  color: #4ade80 !important;
  border: 1px solid rgba(74, 222, 128, 0.4) !important;
  padding: 3px 10px !important;
  border-radius: 6px !important;
  font-family: var(--font-mono) !important;
  font-size: 0.76rem !important;
  font-weight: 700 !important;
}

.badge-cyan {
  background: rgba(56, 189, 248, 0.18) !important;
  color: #38bdf8 !important;
  border: 1px solid rgba(56, 189, 248, 0.4) !important;
  padding: 3px 10px !important;
  border-radius: 6px !important;
  font-family: var(--font-mono) !important;
  font-size: 0.76rem !important;
  font-weight: 700 !important;
}

/* ==========================================================================
   Primary Actions & Buttons
   ========================================================================== */

button.primary,
button.variant-primary,
.primary-btn {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
  color: #ffffff !important;
  font-weight: 700 !important;
  font-size: 1.05rem !important;
  letter-spacing: 0.02em !important;
  border-radius: 12px !important;
  border: 1px solid rgba(56, 189, 248, 0.45) !important;
  box-shadow: 0 4px 18px rgba(2, 132, 199, 0.4) !important;
  padding: 14px 28px !important;
  transition: all 0.2s ease !important;
}

button.primary:hover,
button.variant-primary:hover,
.primary-btn:hover {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
  box-shadow: 0 6px 22px rgba(56, 189, 248, 0.5) !important;
  transform: translateY(-1px) !important;
}

/* ==========================================================================
   Markdown Prose and Content Visibility
   ========================================================================== */

.gradio-container .markdown,
.gradio-container .prose {
  color: #e2e8f0 !important;
  font-size: 0.98rem !important;
  line-height: 1.65 !important;
}

.gradio-container .markdown h1,
.gradio-container .markdown h2,
.gradio-container .markdown h3,
.gradio-container .markdown h4 {
  color: #ffffff !important;
  font-weight: 700 !important;
  margin-top: 12px !important;
  margin-bottom: 8px !important;
}

.gradio-container .markdown code {
  color: #38bdf8 !important;
  background: rgba(11, 18, 34, 0.9) !important;
  border: 1px solid rgba(56, 189, 248, 0.25) !important;
  padding: 2px 6px !important;
  border-radius: 5px !important;
  font-family: var(--font-mono) !important;
}

.gradio-container .markdown blockquote {
  border-left: 3px solid #38bdf8 !important;
  background: rgba(15, 23, 42, 0.7) !important;
  padding: 12px 18px !important;
  color: #cbd5e1 !important;
  border-radius: 0 10px 10px 0 !important;
  margin: 12px 0 !important;
}

/* Chatbot Messages */
.gradio-container .message.user {
  background-color: #0284c7 !important;
  color: #ffffff !important;
  border-radius: 12px 12px 2px 12px !important;
}

.gradio-container .message.bot {
  background-color: #0f172a !important;
  color: #f8fafc !important;
  border: 1px solid rgba(148, 163, 184, 0.25) !important;
  border-radius: 12px 12px 12px 2px !important;
}

/* ==========================================================================
   Status Dots & Pulses
   ========================================================================== */

.pulse-dot-green {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--emerald-accent);
  box-shadow: 0 0 10px var(--emerald-accent);
  display: inline-block;
}

.pulse-dot-cyan {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--cyan-accent);
  box-shadow: 0 0 10px var(--cyan-accent);
  display: inline-block;
}

/* Scrollbars */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: rgba(8, 12, 20, 0.8);
}
::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 6px;
}
::-webkit-scrollbar-thumb:hover {
  background: #38bdf8;
}

/* ==========================================================================
   Viewport-Bottom Docked Footer (Zero Wasted Space)
   ========================================================================== */

footer, .gradio-container footer, .gradio-container > footer, footer.svelte-zxu34v {
  position: fixed !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  width: 100% !important;
  height: 34px !important;
  min-height: 34px !important;
  margin: 0 !important;
  padding: 4px 24px !important;
  background: rgba(8, 12, 20, 0.95) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border-top: 1px solid rgba(148, 163, 184, 0.18) !important;
  z-index: 9999 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  gap: 16px !important;
  font-size: 0.8rem !important;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.6) !important;
  box-sizing: border-box !important;
}

footer *, .gradio-container footer * {
  font-size: 0.8rem !important;
  color: #64748b !important;
}

footer a, .gradio-container footer a {
  color: #94a3b8 !important;
  text-decoration: none !important;
  transition: color 0.2s ease !important;
}

footer a:hover, .gradio-container footer a:hover {
  color: #38bdf8 !important;
}
"""

CRUCIBLE_HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style id="crucible-head-overrides">
  /* Executive Tab Nav: Contiguous bar without parent container outline */
  .gradio-container .tab-nav,
  div.tabs > div.tab-nav {
    background: transparent !important;
    border: none !important;
    border-bottom: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    box-shadow: none !important;
  }
  .gradio-container .tab-nav button,
  div.tabs > div.tab-nav > button {
    border-radius: 0 !important;
    -webkit-border-radius: 0 !important;
    margin: 0 !important;
    border-right: none !important;
  }
  .gradio-container .tab-nav button:first-child,
  .gradio-container .tab-nav button:first-of-type,
  div.tabs > div.tab-nav > button:first-child,
  div.tabs > div.tab-nav > button:first-of-type {
    border-top-left-radius: 9999px !important;
    border-bottom-left-radius: 9999px !important;
    -webkit-border-top-left-radius: 9999px !important;
    -webkit-border-bottom-left-radius: 9999px !important;
  }
  .gradio-container .tab-nav button:last-child,
  .gradio-container .tab-nav button:last-of-type,
  div.tabs > div.tab-nav > button:last-child,
  div.tabs > div.tab-nav > button:last-of-type {
    border-top-right-radius: 9999px !important;
    border-bottom-right-radius: 9999px !important;
    -webkit-border-top-right-radius: 9999px !important;
    -webkit-border-bottom-right-radius: 9999px !important;
    border-right: 1.5px solid rgba(148, 163, 184, 0.28) !important;
  }
  /* Neon Greenish Active Tab Selection (ONLINE Badge Color Scheme) */
  .gradio-container .tab-nav button.selected,
  .gradio-container button[role="tab"][aria-selected="true"],
  div.tabs > div.tab-nav > button.selected,
  div.tabs > div.tab-nav > button[aria-selected="true"] {
    background: rgba(74, 222, 128, 0.15) !important;
    border: 1.5px solid rgba(74, 222, 128, 0.5) !important;
    border-right: 1.5px solid rgba(74, 222, 128, 0.5) !important;
    color: #4ade80 !important;
    font-weight: 700 !important;
    letter-spacing: normal !important;
    box-shadow: 0 0 14px rgba(74, 222, 128, 0.25) !important;
    text-shadow: none !important;
    z-index: 2 !important;
  }
  .gradio-container .tab-nav button:first-child.selected,
  .gradio-container .tab-nav button:first-of-type.selected,
  div.tabs > div.tab-nav > button:first-child.selected,
  div.tabs > div.tab-nav > button:first-of-type.selected {
    border-top-left-radius: 9999px !important;
    border-bottom-left-radius: 9999px !important;
    -webkit-border-top-left-radius: 9999px !important;
    -webkit-border-bottom-left-radius: 9999px !important;
  }
  .gradio-container .tab-nav button:last-child.selected,
  .gradio-container .tab-nav button:last-of-type.selected,
  div.tabs > div.tab-nav > button:last-child.selected,
  div.tabs > div.tab-nav > button:last-of-type.selected {
    border-top-right-radius: 9999px !important;
    border-bottom-right-radius: 9999px !important;
    -webkit-border-top-right-radius: 9999px !important;
    -webkit-border-bottom-right-radius: 9999px !important;
  }
  /* Remove borders from markdown text blocks inside tabs */
  .gradio-container .tabitem .block:has(.prose),
  .gradio-container .tabitem .block:has(.markdown),
  .gradio-container .tabitem .markdown,
  .gradio-container .tabitem .prose {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }
</style>
<script>
  document.documentElement.classList.add('dark');
  if (document.body) document.body.classList.add('dark');
  window.addEventListener('DOMContentLoaded', () => {
    document.documentElement.classList.add('dark');
    if (document.body) document.body.classList.add('dark');
  });
</script>
"""

JARVIS_HEAD = CRUCIBLE_HEAD
JARVIS_CSS = CRUCIBLE_CSS


class DefaultSoftTheme(gr.themes.Soft):
    """Fallback standard Gradio Soft Theme."""

    def __init__(self) -> None:
        super().__init__(
            primary_hue="teal",
            secondary_hue="cyan",
        )


THEMES: dict[str, dict[str, Any]] = {
    "crucible": {
        "name": "Crucible (Executive Glassmorphism)",
        "theme": CrucibleTheme(),
        "css": CRUCIBLE_CSS,
        "head": CRUCIBLE_HEAD,
        "description": "Crucible Executive Glassmorphism with deep navy surfaces, highlighted intake workstation, and cyan accents.",
    },
    "jarvis": {
        "name": "Crucible (Executive Glassmorphism)",
        "theme": CrucibleTheme(),
        "css": CRUCIBLE_CSS,
        "head": CRUCIBLE_HEAD,
        "description": "Crucible Executive Glassmorphism (alias).",
    },
    "soft": {
        "name": "Gradio Soft (Teal/Cyan)",
        "theme": DefaultSoftTheme(),
        "css": "",
        "head": "",
        "description": "Standard modern Gradio light/dark adaptive soft theme.",
    },
    "default": {
        "name": "Gradio Default",
        "theme": gr.themes.Default(),
        "css": "",
        "head": "",
        "description": "Vanilla Gradio theme with standard styling.",
    },
}


def get_theme_bundle(theme_name: str = "crucible") -> tuple[gr.Theme, str, str]:
    """Retrieve theme object, custom CSS, and head HTML by theme name."""
    key = (theme_name or "crucible").strip().lower()
    bundle = THEMES.get(key) or THEMES.get("crucible") or THEMES.get("jarvis", {})
    return (
        bundle.get("theme", CrucibleTheme()),
        bundle.get("css", CRUCIBLE_CSS),
        bundle.get("head", CRUCIBLE_HEAD),
    )


def list_available_themes() -> list[tuple[str, str]]:
    """List available themes as (label, key) tuples for UI dropdowns."""
    return [(v["name"], k) for k, v in THEMES.items()]


CRUCIBLE_LOGIN_CSS = """
<style id="crucible-login-theme-css">
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  :root {
    --bg-deep: #080c14;
    --card-surface: rgba(15, 23, 42, 0.88);
    --card-border: rgba(148, 163, 184, 0.22);
    --input-bg: rgba(11, 18, 34, 0.95);
    --input-border: rgba(148, 163, 184, 0.28);
    --cyan-primary: #38bdf8;
    --cyan-glow: rgba(56, 189, 248, 0.28);
  }

  /* Scoped exclusively to the unauthenticated login screen */
  html.crucible-login-page,
  html.crucible-login-page body {
    background-color: var(--bg-deep) !important;
    background: radial-gradient(circle at 50% 28%, rgba(56, 189, 248, 0.12) 0%, rgba(8, 12, 20, 1) 75%) !important;
    color: #f8fafc !important;
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-y: auto !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }

  /* Full viewport centering container on login page only */
  html.crucible-login-page gradio-app,
  html.crucible-login-page .gradio-container {
    background: transparent !important;
    background-color: transparent !important;
    min-height: 100vh !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 20px 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }

  /* Eradicate the stark white bar / background */
  html.crucible-login-page .wrap,
  html.crucible-login-page div[class*="wrap"] {
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    border: none !important;
    width: 100% !important;
    max-width: 440px !important;
    margin: 0 auto !important;
    padding: 24px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
  }

  /* Executive Glassmorphism Login Card */
  html.crucible-login-page .wrap > div,
  html.crucible-login-page .wrap .panel,
  html.crucible-login-page div[class*="panel"] {
    background: var(--card-surface) !important;
    backdrop-filter: blur(28px) saturate(190%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(190%) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 24px !important;
    box-shadow: 0 30px 70px -10px rgba(0, 0, 0, 0.85), 0 0 45px rgba(56, 189, 248, 0.15) !important;
    padding: 40px 36px !important;
    width: 100% !important;
    max-width: 440px !important;
    box-sizing: border-box !important;
    position: relative !important;
  }

  /* Hide plain browser default H2 */
  html.crucible-login-page .wrap h2,
  html.crucible-login-page div[class*="panel"] h2 {
    display: none !important;
  }

  /* Executive Brand Header */
  .crucible-brand-header {
    text-align: center;
    margin-bottom: 26px;
  }

  .crucible-brand-header .brand-icon-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(2, 132, 199, 0.35) 100%);
    border: 1px solid rgba(56, 189, 248, 0.5);
    box-shadow: 0 0 24px rgba(56, 189, 248, 0.3);
    margin-bottom: 12px;
  }

  .crucible-brand-header .brand-icon {
    font-size: 28px;
    line-height: 1;
  }

  .crucible-brand-header .brand-title {
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    background: linear-gradient(135deg, #ffffff 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 4px 0;
    text-transform: uppercase;
  }

  .crucible-brand-header .brand-subtitle {
    font-size: 0.85rem;
    color: #94a3b8;
    margin: 0;
    letter-spacing: 0.02em;
    font-weight: 500;
  }

  .crucible-brand-header .brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.22);
    border-radius: 9999px;
    padding: 4px 12px;
    font-size: 0.72rem;
    color: #7dd3fc;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-top: 10px;
  }

  /* Form Labels */
  html.crucible-login-page .wrap label,
  html.crucible-login-page div[class*="panel"] label {
    margin-bottom: 16px !important;
    display: block !important;
  }

  html.crucible-login-page .wrap label span,
  html.crucible-login-page div[class*="panel"] label span {
    color: #cbd5e1 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 6px !important;
    display: block !important;
  }

  /* Inputs */
  html.crucible-login-page .wrap input[type="text"],
  html.crucible-login-page .wrap input[type="password"],
  html.crucible-login-page div[class*="panel"] input {
    background: var(--input-bg) !important;
    background-color: var(--input-bg) !important;
    border: 1.5px solid var(--input-border) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
    width: 100% !important;
    box-sizing: border-box !important;
    transition: all 0.2s ease !important;
  }

  html.crucible-login-page .wrap input[type="text"]:focus,
  html.crucible-login-page .wrap input[type="password"]:focus,
  html.crucible-login-page div[class*="panel"] input:focus {
    border-color: var(--cyan-primary) !important;
    box-shadow: 0 0 0 3px var(--cyan-glow) !important;
    outline: none !important;
  }

  /* Submit Button */
  html.crucible-login-page .wrap button.primary,
  html.crucible-login-page .wrap button[type="submit"],
  html.crucible-login-page div[class*="panel"] button {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.5) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 14px 20px !important;
    width: 100% !important;
    margin-top: 14px !important;
    cursor: pointer !important;
    box-shadow: 0 4px 20px rgba(2, 132, 199, 0.4) !important;
    transition: all 0.2s ease !important;
  }

  html.crucible-login-page .wrap button.primary:hover,
  html.crucible-login-page .wrap button[type="submit"]:hover,
  html.crucible-login-page div[class*="panel"] button:hover {
    background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%) !important;
    box-shadow: 0 6px 28px rgba(56, 189, 248, 0.55) !important;
    transform: translateY(-1px) !important;
  }

  /* Incorrect Credentials Warning */
  html.crucible-login-page .creds,
  html.crucible-login-page p[class*="creds"] {
    background: rgba(239, 68, 68, 0.15) !important;
    border: 1px solid rgba(239, 68, 68, 0.35) !important;
    border-radius: 10px !important;
    color: #fca5a5 !important;
    padding: 10px 14px !important;
    text-align: center !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    margin: 12px 0 !important;
  }
</style>

<script>
  // Ensure dark mode class is applied immediately
  document.documentElement.classList.add('dark');
  document.documentElement.classList.add('crucible-login-page');
  if (document.body) document.body.classList.add('dark');

  // Inject the Executive Brand Header into the login card once DOM is ready
  function mountCrucibleBrand() {
    const wrap = document.querySelector('.wrap') || document.querySelector('div[class*="wrap"]');
    if (!wrap) return false;
    
    // Find panel container
    const panel = wrap.querySelector('.panel') || wrap.querySelector('div[class*="panel"]') || wrap.firstElementChild;
    if (!panel || panel.querySelector('.crucible-brand-header')) return false;

    const brandEl = document.createElement('div');
    brandEl.className = 'crucible-brand-header';
    brandEl.innerHTML = `
      <div class="brand-icon-wrap">
        <span class="brand-icon">⚗️</span>
      </div>
      <h1 class="brand-title">Crucible</h1>
      <p class="brand-subtitle">Autonomous Agentic Framework</p>
      <div class="brand-badge">
        <span>🔒</span>
        <span>Security Clearance Required</span>
      </div>
    `;

    panel.insertBefore(brandEl, panel.firstChild);
    return true;
  }

  // Poll until Svelte mounts the login card
  const brandInterval = setInterval(() => {
    if (mountCrucibleBrand()) {
      clearInterval(brandInterval);
    }
  }, 30);
  setTimeout(() => clearInterval(brandInterval), 5000);
</script>
"""


def inject_crucible_login_theme(html: str) -> str:
    """Inject high-contrast, executive Crucible dark theme into unauthenticated login page."""
    html = html.replace('<html\n\tlang="en"', '<html\n\tlang="en" class="dark crucible-login-page"')
    html = html.replace('<html lang="en"', '<html lang="en" class="dark crucible-login-page"')
    html = html.replace('--bg: white;', '--bg: #080c14;')
    html = html.replace('--col:   #1f2937;', '--col: #f8fafc;')
    html = html.replace('--bg-dark: #0b0f19;', '--bg-dark: #080c14;')
    html = html.replace('--col-dark: #f3f4f6;', '--col-dark: #f8fafc;')
    return html.replace("</head>", CRUCIBLE_LOGIN_CSS + "</head>")

