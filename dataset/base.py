from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models import VerdictLabel

TAXONOMY_LABELS = tuple(label.value for label in VerdictLabel)

@dataclass
class GoldExample:

    id: str
    query: str
    documents: list[dict[str, str]]
    gold_label: str
    source_dataset: str
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.gold_label not in TAXONOMY_LABELS:
            raise ValueError(
                f"gold_label {self.gold_label!r} is not one of {TAXONOMY_LABELS}"
            )
