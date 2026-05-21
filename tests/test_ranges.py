import pytest

from font_splitter.ranges import compress_codepoints, parse_unicode_range_list


def test_parse_single_codepoint():
    assert parse_unicode_range_list("U+41") == {0x41}


def test_parse_range():
    assert parse_unicode_range_list("U+0041-0043") == {0x41, 0x42, 0x43}


def test_parse_wildcard():
    assert parse_unicode_range_list("U+4??") == set(range(0x400, 0x500))


def test_parse_comma_list_case_insensitive():
    assert parse_unicode_range_list("u+41, U+43-44") == {0x41, 0x43, 0x44}


def test_reject_invalid_range():
    with pytest.raises(ValueError, match="Invalid unicode-range"):
        parse_unicode_range_list("not-a-range")


def test_reject_codepoints_outside_unicode_range():
    with pytest.raises(ValueError, match="outside Unicode range"):
        parse_unicode_range_list("U+110000")


def test_compress_codepoints():
    assert compress_codepoints({0x41, 0x42, 0x44}) == ["U+41-42", "U+44"]
