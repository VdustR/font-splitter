from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from os import PathLike
from typing import BinaryIO

from fontTools import subset
from fontTools.ttLib import TTFont

FontInput = str | PathLike[str] | bytes | BinaryIO


@dataclass(frozen=True)
class SubsetResult:
    data: bytes
    warnings: list[str]


def load_font(font: FontInput) -> TTFont:
    if isinstance(font, bytes):
        return TTFont(BytesIO(font))
    return TTFont(font)


def subset_font(font: FontInput, codepoints: set[int], *, flavor: str) -> SubsetResult:
    ttfont = load_font(font)
    options = subset.Options()
    options.flavor = flavor
    options.set(layout_features="*")
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(codepoints))
    warnings: list[str] = []
    handler = _WarningCaptureHandler(warnings)
    logger = logging.getLogger("fontTools")
    logger.addHandler(handler)
    out = BytesIO()
    try:
        # FontTools reports many recoverable subsetting issues through logging,
        # not Python warnings, so capture those messages alongside the bytes.
        subsetter.subset(ttfont)
        ttfont.flavor = flavor
        ttfont.save(out)
    finally:
        logger.removeHandler(handler)
    return SubsetResult(data=out.getvalue(), warnings=warnings)


def subset_font_to_bytes(font: FontInput, codepoints: set[int], *, flavor: str) -> bytes:
    return subset_font(font, codepoints, flavor=flavor).data


class _WarningCaptureHandler(logging.Handler):
    def __init__(self, warnings: list[str]) -> None:
        super().__init__(level=logging.WARNING)
        self._warnings = warnings

    def emit(self, record: logging.LogRecord) -> None:
        self._warnings.append(f"{record.name}: {record.getMessage()}")
