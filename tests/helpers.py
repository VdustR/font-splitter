from io import BytesIO
from collections.abc import Iterable

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def build_test_font() -> bytes:
    return _build_font([0x20, 0x41, 0x42, 0x43], family_name="POC Test")


def build_multiblock_test_font() -> bytes:
    return _build_font(
        [0x20, 0x41, 0x0100, 0x2600, 0x4E00],
        family_name="Fixture Test",
    )


def _build_font(codepoints: Iterable[int], *, family_name: str) -> bytes:
    cmap = {
        codepoint: _glyph_name(codepoint)
        for codepoint in sorted(set(codepoints))
    }
    glyph_order = [".notdef", *dict.fromkeys(cmap.values())]
    advance_widths = {glyph: (600, 0) for glyph in glyph_order}

    glyphs = {}
    for glyph_name in glyph_order:
        pen = TTGlyphPen(None)
        glyphs[glyph_name] = pen.glyph()

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(advance_widths)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupOS2()
    fb.setupNameTable({"familyName": family_name, "styleName": "Regular"})
    fb.setupPost()
    fb.setupMaxp()

    out = BytesIO()
    fb.save(out)
    return out.getvalue()


def _glyph_name(codepoint: int) -> str:
    if codepoint == 0x20:
        return "space"
    return f"uni{codepoint:04X}"
