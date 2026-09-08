"""API 키 없이 동작하는 규칙 기반 Claim 추출기.

각 데이터셋이 이미 제공하는 구조화된 필드(질문, 정답 등)를 최대한 활용하고,
일반 자유 텍스트에 대해서는 :mod:`ontology.schema` 의 통제 어휘 사전을 이용한
키워드 기반 추세(trend)/극성(polarity) 탐지로 대체한다.

정밀한 의미 파싱이 필요하다면 :class:`extraction.llm.LLMClaimExtractor` (LLM
기반, 연구 설계서 2단계·RQ1)를 사용한다. 이 추출기는 오프라인에서 파이프라인
(추출 -> 온톨로지 적재)을 검증하기 위한 베이스라인이다.
"""

from __future__ import annotations

import re

from dataset.base import GoldExample
from extraction.base import ClaimExtractor, ExtractedClaim
from models import Claim
from ontology.schema import normalize_concept

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class HeuristicClaimExtractor(ClaimExtractor):
    def extract(self, example: GoldExample) -> list[ExtractedClaim]:
        if example.source_dataset == "wikicontradict":
            return self._extract_wikicontradict(example)
        if example.source_dataset == "google_conflicts":
            return self._extract_google_conflicts(example)
        return self._extract_generic(example)

    # WikiContradict: context1/context2 + answer1/answer2 를 직접 활용한다.
    def _extract_wikicontradict(self, example: GoldExample) -> list[ExtractedClaim]:
        subject = example.raw.get("WikipediaArticleTitle") or example.query
        predicate = _slug_predicate(example.query)
        results: list[ExtractedClaim] = []
        for idx, doc in enumerate(example.documents):
            answer = (doc.get("answer") or "").strip()
            text = doc.get("text", "")
            object_value = answer if answer else _truncate(text)
            if not object_value:
                continue
            claim = Claim(
                subject=subject,
                predicate=predicate,
                object=object_value,
                temporal_scope=None,
                source=doc.get("source", f"doc-{idx}"),
                perspective=doc.get("source", f"doc-{idx}"),
                confidence=0.9 if answer else 0.5,
                extracted_from=_truncate(text),
            )
            results.append((idx, claim))
        return results

    # google/rag_conflicts: search_results 자유 텍스트에서 추세/사실을 탐지한다.
    def _extract_google_conflicts(self, example: GoldExample) -> list[ExtractedClaim]:
        subject = example.query.strip() or "unknown"
        results: list[ExtractedClaim] = []
        for idx, doc in enumerate(example.documents):
            text = doc.get("text", "")
            if not text.strip():
                continue
            concept = normalize_concept(text)
            year_match = _YEAR_RE.search(text)
            claim = Claim(
                subject=subject,
                predicate="Trend" if concept else "Assertion",
                object=concept if concept else _truncate(text, 160),
                temporal_scope=year_match.group(0) if year_match else None,
                source=doc.get("source", f"doc-{idx}"),
                perspective=doc.get("source", f"doc-{idx}"),
                confidence=0.7 if concept else 0.3,
                extracted_from=_truncate(text),
            )
            results.append((idx, claim))
        return results

    # 알 수 없는 데이터셋: 문서 텍스트를 그대로(또는 정규화하여) Claim화한다.
    def _extract_generic(self, example: GoldExample) -> list[ExtractedClaim]:
        subject = example.query.strip() or "unknown"
        results: list[ExtractedClaim] = []
        for idx, doc in enumerate(example.documents):
            text = doc.get("text", "")
            if not text.strip():
                continue
            concept = normalize_concept(text)
            claim = Claim(
                subject=subject,
                predicate="Assertion",
                object=concept if concept else _truncate(text, 160),
                source=doc.get("source", f"doc-{idx}"),
                perspective=doc.get("source", f"doc-{idx}"),
                confidence=0.5,
                extracted_from=_truncate(text),
            )
            results.append((idx, claim))
        return results


def _slug_predicate(question: str) -> str:
    words = re.findall(r"[A-Za-z0-9가-힣]+", question)[:6]
    return "".join(w.capitalize() for w in words) or "Assertion"


def _truncate(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
