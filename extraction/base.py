from __future__ import annotations

from abc import ABC, abstractmethod

from dataset.base import GoldExample
from models import Claim

# (문서 인덱스, 그 문서에서 추출된 Claim)
ExtractedClaim = tuple[int, Claim]


class ClaimExtractor(ABC):
    """자연어 문서를 구조화된 Claim(RDF triple 후보)으로 변환하는 인터페이스."""

    @abstractmethod
    def extract(self, example: GoldExample) -> list[ExtractedClaim]:
        """example.documents 각각으로부터 Claim을 추출한다."""
