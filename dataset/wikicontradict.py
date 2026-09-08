"""
Hugging Face: ``ibm-research/Wikipedia_contradict_benchmark``

실제 배포 파일(WikiContradict_dataset_v1_rag_qa.csv)의 컬럼 스키마
(2026-09 기준, 원본 데이터셋에서 확인):

    question_ID, question, context1, context2, answer1, answer2,
    contradictType, samepassage, merged_context, ref_answer,
    WikipediaArticleTitle, url

``contradictType`` 값은 "Explicit"(명시적 모순) 또는
"Implicit (reasoning required)"(추론이 필요한 암묵적 모순) 두 가지이며,
이 값은 raw 메타데이터에 그대로 보존하여 RQ3(implicit contradiction 탐지
효과 비교)에 사용할 수 있도록 한다.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dataset._download import DEFAULT_CACHE_ROOT, ensure_downloaded
from dataset.base import GoldExample
from models import VerdictLabel

HF_DATASET_NAME = "ibm-research/Wikipedia_contradict_benchmark"
HF_DATA_FILE = "WikiContradict_dataset_v1_rag_qa.csv"
HF_RESOLVE_URL = f"https://huggingface.co/datasets/{HF_DATASET_NAME}/resolve/main/{HF_DATA_FILE}"
DEFAULT_CACHE_PATH = DEFAULT_CACHE_ROOT / "wikicontradict" / HF_DATA_FILE

# WikiContradict는 "서로 모순되는 두 문맥" 쌍만 수록한 벤치마크이므로
# 모든 레코드를 관점 간 모순(inter-perspective contradiction)으로 취급한다.
DEFAULT_LABEL = VerdictLabel.INTER_PERSPECTIVE_CONTRADICTION.value


def load_from_huggingface(split: str = "train") -> list[GoldExample]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ImportError(
            "load_from_huggingface requires the 'datasets' package "
            "(pip install datasets)."
        ) from exc
    hf_dataset = load_dataset(
        HF_DATASET_NAME, data_files=HF_DATA_FILE, split=split
    )
    return [_record_to_example(i, dict(record)) for i, record in enumerate(hf_dataset)]


def load_from_hub(
    url: str = HF_RESOLVE_URL,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    force_download: bool = False,
) -> list[GoldExample]:
    """WikiContradict CSV를 Hugging Face에서 직접 내려받아(캐시 재사용) 로드한다.

    ``datasets`` 패키지 설치 없이 표준 라이브러리만으로 동작하는 경량 경로다.
    (``pip install datasets`` 를 쓰고 싶다면 :func:`load_from_huggingface` 사용)
    """

    path = ensure_downloaded(url, cache_path, force=force_download)
    return load_from_file(path)


def load_from_file(path: str | Path) -> list[GoldExample]:
    """로컬에 내려받은 .csv 또는 .json/.jsonl 파일을 GoldExample 목록으로 변환한다."""

    path = Path(path)
    if path.suffix.lower() == ".csv":
        records = _read_csv(path)
    else:
        text = path.read_text(encoding="utf-8")
        stripped = text.strip()
        records = json.loads(stripped) if stripped.startswith("[") else [
            json.loads(line) for line in stripped.splitlines() if line.strip()
        ]
    return [_record_to_example(i, record) for i, record in enumerate(records)]


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _record_to_example(
    index: int,
    record: dict,
    id_field: str = "question_ID",
    question_field: str = "question",
    context1_field: str = "context1",
    context2_field: str = "context2",
    contradict_type_field: str = "contradictType",
    article_title_field: str = "WikipediaArticleTitle",
    url_field: str = "url",
) -> GoldExample:
    article = record.get(article_title_field, "")
    url = record.get(url_field, "")
    documents = [
        {
            "text": record.get(context1_field, ""),
            "source": f"{article} :: context1" if article else "wikipedia-context1",
            "url": url,
            "answer": record.get("answer1", ""),
        },
        {
            "text": record.get(context2_field, ""),
            "source": f"{article} :: context2" if article else "wikipedia-context2",
            "url": url,
            "answer": record.get("answer2", ""),
        },
    ]
    return GoldExample(
        id=str(record.get(id_field, index)),
        query=record.get(question_field, ""),
        documents=documents,
        gold_label=DEFAULT_LABEL,
        source_dataset="wikicontradict",
        raw={**record, "_contradiction_type": record.get(contradict_type_field)},
    )
