from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RangeBucket:
    id: str
    label: str | None
    codepoints: set[int]


class RangeSource(Protocol):
    def buckets(self) -> list[RangeBucket]:
        ...
