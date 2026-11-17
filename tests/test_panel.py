"""The page that the integration ships."""

from __future__ import annotations

from pathlib import Path
import re

PANEL = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "guest_access"
    / "frontend"
    / "guest-access-panel.js"
)


def _language_keys(code: str, language: str) -> list[str]:
    """The keys of one language of the texts, in order, each as often as it is written."""
    start = code.index(f"\n    {language}: {{\n")
    end = code.index("\n    },", start)
    body = code[start:end]
    return re.findall(r'(?:^|", |\{ )\s*([A-Za-z_][A-Za-z0-9_]*): [\["]', body, re.MULTILINE)


def test_texts_have_each_key_once_in_both_languages() -> None:
    """A key written twice silently takes the later text; both languages have the same keys."""
    code = PANEL.read_text(encoding="utf-8")
    english = _language_keys(code, "en")
    german = _language_keys(code, "de")
    assert len(english) > 120
    for keys in (english, german):
        twice = sorted({key for key in keys if keys.count(key) > 1})
        assert not twice, twice
    assert set(english) == set(german)


def test_only_home_assistant_elements_defined_on_a_panel() -> None:
    """No element Home Assistant does not define on a custom panel without loading it."""
    code = PANEL.read_text(encoding="utf-8")
    for element in ("<ha-icon ", "<ha-icon>", "ha-menu-button", "ha-top-app-bar-fixed", "<select"):
        assert element not in code, element
