"""
데이터셋 참고 링크
 https://github.com/google-research-datasets/rag_conflicts

실제 파일(conflicts.jsonl)의 레코드 스키마 (2026-09 기준, 원본 리포지토리에서 확인):

    {
      "source": "situated_qa_geo",
      "question": "...",
      "search_results": [
        {"title": "...", "url": "...", "snippet": "...",
         "date": "...", "response_str": "...", "short_text": "..."},
        ...
      ],
      "conflict_type": "No conflict" | "Complementary information"
                      | "Conflicting opinions and research outcomes"
                      | "Conflict due to outdated information"
                      | "Conflict due to misinformation",
      "correct_answer": "..."
    }

각 ``search_results`` 항목이 하나의 검색 문서에 해당하며, 항목마다 서로 다른
``url``(=출처)을 가지므로 이를 관점(perspective) 분리의 기준으로 사용한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from dataset._download import DEFAULT_CACHE_ROOT, ensure_downloaded
from dataset.base import GoldExample
from models import VerdictLabel

GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/google-research-datasets/"
    "rag_conflicts/main/conflicts.jsonl"
)
DEFAULT_CACHE_PATH = DEFAULT_CACHE_ROOT / "rag_conflicts" / "conflicts.jsonl"

LABEL_MAP = {
    "No conflict": VerdictLabel.CONSISTENT.value,
    "Complementary information": VerdictLabel.PERSPECTIVE_DIVERGENCE.value,
    "Conflicting opinions and research outcomes": VerdictLabel.INTER_PERSPECTIVE_CONTRADICTION.value,
    "Conflict due to outdated information": VerdictLabel.INTRA_PERSPECTIVE_CONTRADICTION.value,
    "Conflict due to misinformation": VerdictLabel.INTER_PERSPECTIVE_CONTRADICTION.value,
}


def load(
    path: str | Path,
    query_field: str = "question",
    documents_field: str = "search_results",
    text_field: str = "short_text",
    source_field: str = "url",
    label_field: str = "conflict_type",
    label_map: dict[str, str] = LABEL_MAP,
    limit: int | None = None,
) -> list[GoldExample]:
    """conflicts.jsonl (또는 이를 부분 추출한 파일)을 GoldExample 목록으로 변환한다."""

    examples: list[GoldExample] = []
    for i, record in enumerate(_iter_records(Path(path))):
        if limit is not None and len(examples) >= limit:
            break

        raw_label = record.get(label_field)
        gold_label = label_map.get(raw_label)
        if gold_label is None:
            continue

        documents = [
            {
                "text": doc.get(text_field) or doc.get("response_str", ""),
                "source": doc.get(source_field) or doc.get("title", f"doc-{j}"),
                "title": doc.get("title", ""),
            }
            for j, doc in enumerate(record.get(documents_field, []))
        ]
        if not documents:
            continue

        record_id = f"{record.get('source', 'google_conflicts')}-{i}"
        examples.append(
            GoldExample(
                id=record_id,
                query=record.get(query_field, ""),
                documents=documents,
                gold_label=gold_label,
                source_dataset="google_conflicts",
                raw=record,
            )
        )
    return examples


def load_from_github(
    url: str = GITHUB_RAW_URL,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    force_download: bool = False,
    limit: int | None = None,
) -> list[GoldExample]:
    """conflicts.jsonl을 GitHub에서 내려받아(캐시 재사용) GoldExample로 변환한다.

    파일이 46MB 정도로 크기 때문에, 캐시 경로(기본값: ``data/rag_conflicts/
    conflicts.jsonl``)에 이미 존재하면 다시 내려받지 않는다.
    """

    path = ensure_downloaded(url, cache_path, force=force_download)
    return load(path, limit=limit)


def _iter_records(path: Path):
    with path.open(encoding="utf-8") as f:
        first_non_ws = _peek_non_whitespace(f)
        if first_non_ws == "[":
            for record in json.load(f):
                yield record
            return
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _peek_non_whitespace(f) -> str:
    pos = f.tell()
    ch = f.read(1)
    while ch and ch.isspace():
        ch = f.read(1)
    f.seek(pos)
    return ch
