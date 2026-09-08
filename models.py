from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from itertools import count
from typing import Optional

_claim_ids = count(1)

# 모순 판정 결과 (일관/ 관점 차이/ 내부모순/ 외부모순)
class VerdictLabel(str, Enum):

    CONSISTENT = "consistent"
    PERSPECTIVE_DIVERGENCE = "perspective_divergence"
    INTRA_PERSPECTIVE_CONTRADICTION = "intra_perspective_contradiction"
    INTER_PERSPECTIVE_CONTRADICTION = "inter_perspective_contradiction"

# 최종 판정 (지지/모순/중립)
class AdjudicationLabel(str, Enum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"

# 검색 문서 (텍스트, 출처, 관점)
@dataclass
class Document:

    text: str
    source: str
    perspective: Optional[str] = None
    published_at: Optional[date] = None

    def __post_init__(self) -> None:
        if self.perspective is None:
            self.perspective = self.source

# 트리플 구조 (주어-술어-목적어)
@dataclass
class Claim:

    subject: str
    predicate: str
    object: str
    temporal_scope: Optional[str] = None
    source: str = "unknown"
    perspective: str = "default"
    confidence: float = 1.0
    extracted_from: Optional[str] = None
    scope: str = "global"
    published_at: Optional[date] = None
    id: str = field(default_factory=lambda: f"claim-{next(_claim_ids)}")

    def key(self) -> tuple:
        return self.subject, self.predicate, self.temporal_scope, self.scope

    def __repr__(self) -> str:
        return (
            f"Claim({self.subject!r} {self.predicate!r} {self.object!r} "
            f"@{self.temporal_scope}/{self.scope} src={self.source!r} "
            f"persp={self.perspective!r})"
        )

# 관점별 Claim
@dataclass
class Perspective:

    name: str
    claims: list[Claim] = field(default_factory=list)

# Rashomon 관점
@dataclass
class PossibleWorld:

    id: str
    description: str
    claims: list[Claim]
    satisfiable: Optional[bool] = None
    violations: list[str] = field(default_factory=list)

# 모순 탐지 결과
@dataclass
class ContradictionVerdict:

    label: VerdictLabel
    claims: list[Claim]
    reason: str
    ontology_rule: Optional[str] = None

# 증거 기반 최종 판정
@dataclass
class AdjudicationResult:

    claim: Claim
    label: AdjudicationLabel
    score: float
    breakdown: dict[str, float]
