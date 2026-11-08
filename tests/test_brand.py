"""The brand images Home Assistant shows for the integration."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

BRAND = Path(__file__).resolve().parent.parent / "custom_components" / "guest_access" / "brand"


@pytest.mark.parametrize(("name", "size"), [("icon.png", 256), ("icon@2x.png", 512)])
def test_icon(name: str, size: int) -> None:
    """Square, transparent, in the two sizes the brands repository asks for."""
    with Image.open(BRAND / name) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"
        assert image.size == (size, size)
        # Transparent corners, the ring of the key drawn opaque
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((size * 150 // 512, size * 330 // 512))[3] == 255
