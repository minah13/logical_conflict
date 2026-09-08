"""LLM(Anthropic API) 기반 Claim 추출기.

연구 설계서 2단계("LLM을 활용하여 자연어 문서에서 주장을 추출") 및
RQ1(다중 관점 자연어 서사를 온톨로지 기반 논리 명제로 변환하는 정확도)
실험을 위한 구현체. ``anthropic`` 패키지와 ``ANTHROPIC_API_KEY``가 필요하다.
"""

from __future__ import annotations

import json
import os

from dataset.base import GoldExample
from extraction.base import ClaimExtractor, ExtractedClaim
from models import Claim

DEFAULT_MODEL = "claude-sonnet-5"

_PROMPT_TEMPLATE = """You extract structured factual claims from a passage that was \
retrieved to help answer a question.

Question: {query}
Passage source: {source}
Passage:
\"\"\"{text}\"\"\"

Return ONLY a JSON array (no prose, no markdown fences). Each element is an \
object with exactly these keys: "subject", "predicate", "object", \
"temporal_scope" (string or null).

Rules:
- Keep subject/predicate/object short (a few words each), suitable as an RDF triple.
- Extract 1-3 claims that are directly relevant to the question.
- If the passage asserts a trend, prefer object values "Increase", "Decrease", \
or "Stable".
- If the passage answers a yes/no question, prefer object values "Yes" or "No".
"""


class LLMClaimExtractor(ClaimExtractor):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "LLMClaimExtractor requires the 'anthropic' package "
                "(pip install anthropic)."
            ) from exc
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self._model = model

    def extract(self, example: GoldExample) -> list[ExtractedClaim]:
        results: list[ExtractedClaim] = []
        for idx, doc in enumerate(example.documents):
            text = doc.get("text", "")
            if not text.strip():
                continue
            source = doc.get("source", f"doc-{idx}")
            for claim in self._extract_from_document(example.query, source, text):
                results.append((idx, claim))
        return results

    def _extract_from_document(self, query: str, source: str, text: str) -> list[Claim]:
        prompt = _PROMPT_TEMPLATE.format(query=query, source=source, text=text[:4000])
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        try:
            records = json.loads(_extract_json_array(raw_text))
        except (json.JSONDecodeError, ValueError):
            return []

        claims: list[Claim] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            subject = str(record.get("subject", "")).strip()
            predicate = str(record.get("predicate", "")).strip()
            object_ = str(record.get("object", "")).strip()
            if not (subject and predicate and object_):
                continue
            claims.append(
                Claim(
                    subject=subject,
                    predicate=predicate,
                    object=object_,
                    temporal_scope=record.get("temporal_scope") or None,
                    source=source,
                    perspective=source,
                    confidence=0.8,
                    extracted_from=text[:240],
                )
            )
        return claims


def _extract_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON array found in LLM response")
    return text[start : end + 1]
