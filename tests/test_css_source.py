import pytest

from font_splitter.css_source import CssAmbiguityError, FontCssSource


CSS = """
/* latin */
@font-face {
  font-family: 'Demo Sans';
  font-style: normal;
  font-weight: 400;
  src: url(demo-latin.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}

/* symbols */
@font-face {
  font-family: 'Demo Sans';
  font-style: normal;
  font-weight: 400;
  src: url(demo-symbols.woff2) format('woff2');
  unicode-range: U+2600-2602, U+4??;
}
"""


def test_parse_font_css_rules_in_order():
    source = FontCssSource.from_css(CSS, family="Demo Sans", weight="400")
    buckets = source.buckets()
    assert [bucket.id for bucket in buckets] == ["font-css-001", "font-css-002"]
    assert buckets[0].label == "latin"
    assert 0x41 in buckets[0].codepoints
    assert 0x2601 in buckets[1].codepoints
    assert 0x4FF in buckets[1].codepoints


def test_requires_filter_when_descriptor_groups_are_ambiguous():
    css = CSS + """
@font-face {
  font-family: 'Other Sans';
  font-style: normal;
  font-weight: 400;
  unicode-range: U+0100-017F;
}
"""
    with pytest.raises(CssAmbiguityError):
        FontCssSource.from_css(css)


def test_partial_filter_must_resolve_to_one_descriptor_group():
    css = CSS + """
@font-face {
  font-family: 'Demo Sans';
  font-style: normal;
  font-weight: 700;
  unicode-range: U+0100-017F;
}
"""
    with pytest.raises(CssAmbiguityError, match="still match multiple"):
        FontCssSource.from_css(css, family="Demo Sans")


def test_ignores_rules_without_unicode_range():
    css = """
@font-face {
  font-family: 'Demo Sans';
  font-weight: 400;
  src: url(all.woff2);
}
"""
    source = FontCssSource.from_css(css)
    assert source.buckets() == []
