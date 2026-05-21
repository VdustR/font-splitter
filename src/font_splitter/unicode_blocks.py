from __future__ import annotations

import re
from dataclasses import dataclass

from fontTools.unicodedata import Blocks

from .sources import RangeBucket


@dataclass(frozen=True)
class UnicodeBlock:
    id: str
    start: int
    end: int


UNICODE_BLOCKS_SOURCE = "fontTools.unicodedata.Blocks"


class UnicodeBlockSource:
    def __init__(self, blocks: list[UnicodeBlock] | None = None) -> None:
        self._blocks = blocks or _fonttools_blocks()

    def buckets(self) -> list[RangeBucket]:
        return [
            RangeBucket(block.id, block.id, set(range(block.start, block.end + 1)))
            for block in self._blocks
        ]


def _fonttools_blocks() -> list[UnicodeBlock]:
    starts = Blocks.RANGES
    names = Blocks.VALUES
    blocks: list[UnicodeBlock] = []
    for index, (start, name) in enumerate(zip(starts, names, strict=True)):
        if name == "No_Block":
            continue
        end = starts[index + 1] - 1 if index + 1 < len(starts) else 0x10FFFF
        blocks.append(UnicodeBlock(_slug_block_name(name), start, end))
    return blocks


def _slug_block_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
