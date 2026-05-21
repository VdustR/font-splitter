from __future__ import annotations

import re
from collections.abc import Iterable

_PART_RE = re.compile(r"^U\+([0-9A-F?]+)(?:-([0-9A-F]+))?$", re.IGNORECASE)
UNICODE_MAX = 0x10FFFF


def parse_unicode_range_list(value: str) -> set[int]:
    codepoints: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        codepoints.update(_parse_unicode_range_part(part))
    return codepoints


def _parse_unicode_range_part(part: str) -> set[int]:
    match = _PART_RE.match(part)
    if not match:
        raise ValueError(f"Invalid unicode-range: {part}")

    start_raw, end_raw = match.groups()
    if "?" in start_raw:
        if end_raw is not None:
            raise ValueError(f"Invalid unicode-range wildcard with explicit end: {part}")
        start = int(start_raw.replace("?", "0"), 16)
        end = int(start_raw.replace("?", "F"), 16)
        _validate_unicode_bounds(part, start, end)
        return set(range(start, end + 1))

    start = int(start_raw, 16)
    end = int(end_raw, 16) if end_raw is not None else start
    if end < start:
        raise ValueError(f"Invalid unicode-range end before start: {part}")
    _validate_unicode_bounds(part, start, end)
    return set(range(start, end + 1))


def _validate_unicode_bounds(part: str, start: int, end: int) -> None:
    if start > UNICODE_MAX or end > UNICODE_MAX:
        raise ValueError(f"Invalid unicode-range outside Unicode range: {part}")


def compress_codepoints(codepoints: Iterable[int]) -> list[str]:
    ordered = sorted(set(codepoints))
    if not ordered:
        return []

    ranges: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for codepoint in ordered[1:]:
        if codepoint == previous + 1:
            previous = codepoint
            continue
        ranges.append((start, previous))
        start = previous = codepoint
    ranges.append((start, previous))

    return [
        f"U+{start:X}" if start == end else f"U+{start:X}-{end:X}"
        for start, end in ranges
    ]
