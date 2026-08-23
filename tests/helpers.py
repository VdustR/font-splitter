from io import BytesIO
from collections.abc import Iterable

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


def build_test_font() -> bytes:
    return _build_font([0x20, 0x41, 0x42, 0x43], family_name="POC Test")


def build_test_font_with_family_name(family_name: str) -> bytes:
    return _build_font([0x41], family_name=family_name)


def build_multiblock_test_font() -> bytes:
    return _build_font(
        [0x20, 0x41, 0x0100, 0x2600, 0x4E00],
        family_name="Fixture Test",
    )


def build_variation_sequence_test_font() -> bytes:
    raw = _build_font(
        [0x41, 0x42, 0xE000],
        family_name="Variation Sequence Test",
    )
    font = TTFont(BytesIO(raw))
    glyph_order = font.getGlyphOrder()
    variant_glyph = "A.var"
    glyph_order.append(variant_glyph)
    font.setGlyphOrder(glyph_order)
    pen = TTGlyphPen(None)
    font["glyf"][variant_glyph] = pen.glyph()
    font["hmtx"][variant_glyph] = (600, 0)
    font["maxp"].numGlyphs = len(glyph_order)

    variation_cmap = CmapSubtable.newSubtable(14)
    variation_cmap.platformID = 0
    variation_cmap.platEncID = 5
    variation_cmap.language = 0
    variation_cmap.cmap = {}
    variation_cmap.uvsDict = {0xE0100: [(0x41, variant_glyph), (0x42, None)]}
    font["cmap"].tables.append(variation_cmap)

    out = BytesIO()
    font.save(out)
    return out.getvalue()


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
