from io import BytesIO
import logging

from fontTools import subset
from fontTools.ttLib import TTFont

from font_splitter.subsetter import subset_font, subset_font_to_bytes
from tests.helpers import build_test_font, build_variation_sequence_test_font


def test_subset_to_woff2_bytes_roundtrips():
    raw = build_test_font()
    out = subset_font_to_bytes(raw, {0x41, 0x42}, flavor="woff2")
    assert out[:4] == b"wOF2"
    font = TTFont(BytesIO(out))
    assert set(font.getBestCmap()) == {0x41, 0x42}


def test_subset_to_woff_bytes_roundtrips():
    raw = build_test_font()
    out = subset_font_to_bytes(raw, {0x41}, flavor="woff")
    assert out[:4] == b"wOFF"
    font = TTFont(BytesIO(out))
    assert set(font.getBestCmap()) == {0x41}


def test_subset_preserves_only_variation_sequences_for_included_bases():
    raw = build_variation_sequence_test_font()

    out = subset_font_to_bytes(raw, {0x41}, flavor="woff2")

    font = TTFont(BytesIO(out))
    variation_cmap = next(table for table in font["cmap"].tables if table.format == 14)
    assert set(variation_cmap.uvsDict) == {0xE0100}
    assert len(variation_cmap.uvsDict[0xE0100]) == 1
    base, variant_glyph = variation_cmap.uvsDict[0xE0100][0]
    assert base == 0x41
    assert variant_glyph is not None
    assert variant_glyph != font.getBestCmap()[0x41]
    assert set(font.getBestCmap()) == {0x41}
    assert len(font.getGlyphOrder()) == 3

    default_out = subset_font_to_bytes(raw, {0x42}, flavor="woff2")
    default_font = TTFont(BytesIO(default_out))
    default_variation_cmap = next(
        table for table in default_font["cmap"].tables if table.format == 14
    )
    assert default_variation_cmap.uvsDict == {0xE0100: [(0x42, None)]}


def test_subset_captures_fonttools_warnings(monkeypatch):
    raw = build_test_font()
    original_subset = subset.Subsetter.subset

    def subset_with_warning(self, font):
        logging.getLogger("fontTools.subset").warning("synthetic subset warning")
        return original_subset(self, font)

    monkeypatch.setattr(subset.Subsetter, "subset", subset_with_warning)

    result = subset_font(raw, {0x41}, flavor="woff2")

    assert result.data[:4] == b"wOF2"
    assert result.warnings == ["fontTools.subset: synthetic subset warning"]
