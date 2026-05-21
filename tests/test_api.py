from io import BytesIO
import logging
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from font_splitter.api import split_font, split_font_to_memory
from font_splitter.css_source import FontCssSource
from font_splitter.unicode_blocks import UnicodeBlockSource
from tests.helpers import build_multiblock_test_font, build_test_font


def test_split_font_to_memory_defaults_to_unicode_blocks_and_auto_local_names():
    result = split_font_to_memory(build_test_font())

    assert "POC-Test.Basic-Latin.woff2" in result.assets
    css_asset = result.assets["POC-Test.css"].decode("utf-8")
    assert "local('POC Test Regular')" in css_asset
    assert "format('woff2')" in css_asset


def test_split_font_to_memory_accepts_file_like_input():
    result = split_font_to_memory(BytesIO(build_test_font()), local_src="none")

    assert "POC-Test.Basic-Latin.woff2" in result.assets


def test_split_font_to_memory_escapes_css_strings_and_outputs_metadata():
    result = split_font_to_memory(
        build_test_font(),
        family="Acme's Font",
        style="italic",
        weight=700,
        stretch="condensed",
        local_src=["Acme's Local"],
    )

    css_asset = result.assets["Acme-s-Font.css"].decode("utf-8")
    assert "font-family: 'Acme\\'s Font';" in css_asset
    assert "font-style: italic;" in css_asset
    assert "font-weight: 700;" in css_asset
    assert "font-stretch: condensed;" in css_asset
    assert "local('Acme\\'s Local')" in css_asset


def test_split_font_to_memory_generates_css_and_woff2_assets():
    font = build_test_font()
    css = """
@font-face {
  font-family: 'POC Test';
  font-weight: 400;
  unicode-range: U+0041;
}
"""
    result = split_font_to_memory(
        font,
        sources=[FontCssSource.from_css(css, family="POC Test", weight="400")],
        fallback=UnicodeBlockSource(),
        max_codepoints=10,
        flavor="woff2",
        family="POC Test",
        local_src="none",
    )
    assert "POC-Test.font-css-001.woff2" in result.assets
    assert "POC-Test.Basic-Latin.woff2" in result.assets
    css_asset = result.assets["POC-Test.css"].decode("utf-8")
    assert "unicode-range: U+41;" in css_asset
    assert "local(" not in css_asset
    assert result.stats.matched_source_count == 1
    assert result.stats.fallback_codepoint_count == 3
    assert result.stats.total_codepoint_count == 4
    assert result.stats.estimated_files == [
        "POC-Test.font-css-001.woff2",
        "POC-Test.Basic-Latin.woff2",
        "POC-Test.css",
    ]


def test_split_font_to_memory_covers_generated_multiblock_fixture():
    font = build_multiblock_test_font()
    result = split_font_to_memory(
        font,
        max_codepoints=None,
        family="Fixture Test",
        local_src="none",
    )

    assert set(result.assets) >= {
        "Fixture-Test.Basic-Latin.woff2",
        "Fixture-Test.Latin-Extended-A.woff2",
        "Fixture-Test.Miscellaneous-Symbols.woff2",
        "Fixture-Test.CJK-Unified-Ideographs.woff2",
        "Fixture-Test.css",
    }
    assert result.assets["Fixture-Test.Basic-Latin.woff2"][:4] == b"wOF2"
    assert result.assets["Fixture-Test.CJK-Unified-Ideographs.woff2"][:4] == b"wOF2"


def test_split_font_writes_assets_to_disk(tmp_path: Path):
    font = build_test_font()
    result = split_font(
        font,
        output_dir=tmp_path,
        sources=[],
        fallback=UnicodeBlockSource(),
        max_codepoints=None,
        flavor="woff",
        family="POC Test",
        local_src="auto",
    )
    assert (tmp_path / "POC-Test.Basic-Latin.woff").exists()
    assert (tmp_path / "POC-Test.css").exists()
    TTFont(tmp_path / "POC-Test.Basic-Latin.woff")
    css = (tmp_path / "POC-Test.css").read_text(encoding="utf-8")
    assert "local('POC Test Regular')" in css
    assert result.assets == {}
    assert result.assets_written


def test_split_font_to_memory_aggregates_subset_warnings(monkeypatch):
    original_subset = subset.Subsetter.subset

    def subset_with_warning(self, font):
        logging.getLogger("fontTools.subset").warning("synthetic API warning")
        return original_subset(self, font)

    monkeypatch.setattr(subset.Subsetter, "subset", subset_with_warning)

    result = split_font_to_memory(
        build_test_font(),
        max_codepoints=None,
        local_src="none",
    )

    assert result.warnings == ["fontTools.subset: synthetic API warning"]
