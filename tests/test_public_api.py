from font_splitter import FontCssSource, UnicodeBlockSource
from font_splitter.css_source import FontCssSource as FontCssSourceModule
from font_splitter.unicode_blocks import UnicodeBlockSource as UnicodeBlockSourceModule


def test_range_sources_are_top_level_public_api():
    assert FontCssSource is FontCssSourceModule
    assert UnicodeBlockSource is UnicodeBlockSourceModule
