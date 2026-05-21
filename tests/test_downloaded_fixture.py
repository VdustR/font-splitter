import hashlib
import os
import urllib.request
from io import BytesIO

import pytest
from fontTools.ttLib import TTFont

from font_splitter import split_font_to_memory


def test_checksum_verified_downloaded_font_fixture_roundtrips():
    url = os.environ.get("FONT_SPLITTER_FIXTURE_URL")
    expected_sha256 = os.environ.get("FONT_SPLITTER_FIXTURE_SHA256")
    if not url or not expected_sha256:
        pytest.skip("FONT_SPLITTER_FIXTURE_URL and FONT_SPLITTER_FIXTURE_SHA256 are not set")

    with urllib.request.urlopen(url, timeout=30) as response:
        font_bytes = response.read()

    actual_sha256 = hashlib.sha256(font_bytes).hexdigest()
    assert actual_sha256 == expected_sha256

    result = split_font_to_memory(
        font_bytes,
        max_codepoints=128,
        local_src="none",
    )

    font_asset_name = next(
        name for name in result.stats.estimated_files
        if name.endswith(".woff2")
    )
    TTFont(BytesIO(result.assets[font_asset_name]))
    assert result.stats.total_codepoint_count > 0
