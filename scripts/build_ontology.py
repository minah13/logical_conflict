"""데이터셋(google_conflicts / wikicontradict) -> Claim 추출 -> 온톨로지(RDF/OWL/SKOS)
저장까지의 전체 파이프라인을 실행하는 CLI.

두 데이터셋 모두 공개 저장소에서 인증 없이 받을 수 있으므로, --input을
생략하면 자동으로 내려받아 data/ 아래에 캐시해 재사용한다(직접 파일을
관리할 필요 없음). 이미 갖고 있는 파일을 쓰고 싶다면 --input으로 지정한다.

사용 예)

    # rag_conflicts: 자동 다운로드(최초 1회, ~46MB) 후 캐시 재사용
    python scripts/build_ontology.py --dataset google_conflicts \\
        --limit 200 --output output/google_conflicts.ttl

    # WikiContradict: 자동 다운로드(경량, datasets 패키지 불필요)
    python scripts/build_ontology.py --dataset wikicontradict \\
        --output output/wikicontradict.ttl

    # 이미 내려받은 파일을 직접 지정
    python scripts/build_ontology.py --dataset google_conflicts \\
        --input conflicts.jsonl --output output/google_conflicts.ttl

    # WikiContradict를 datasets 패키지로 Hugging Face에서 로드
    python scripts/build_ontology.py --dataset wikicontradict --huggingface \\
        --output output/wikicontradict.ttl

    # LLM 기반 추출기 사용 (ANTHROPIC_API_KEY 필요)
    python scripts/build_ontology.py --dataset wikicontradict \\
        --extractor llm --output output/wikicontradict_llm.ttl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset import google_conflicts, wikicontradict
from dataset.base import GoldExample
from extraction.base import ClaimExtractor
from extraction.heuristic import HeuristicClaimExtractor
from ontology.builder import OntologyGraph


def load_examples(args: argparse.Namespace) -> list[GoldExample]:
    if args.dataset == "google_conflicts":
        if args.input:
            return google_conflicts.load(args.input, limit=args.limit)
        return google_conflicts.load_from_github(
            force_download=args.force_download, limit=args.limit
        )

    if args.dataset == "wikicontradict":
        if args.input:
            examples = wikicontradict.load_from_file(args.input)
        elif args.huggingface:
            examples = wikicontradict.load_from_huggingface()
        else:
            examples = wikicontradict.load_from_hub(force_download=args.force_download)
        return examples[: args.limit] if args.limit else examples

    raise SystemExit(f"알 수 없는 데이터셋: {args.dataset}")


def build_extractor(name: str) -> ClaimExtractor:
    if name == "heuristic":
        return HeuristicClaimExtractor()
    if name == "llm":
        from extraction.llm import LLMClaimExtractor

        return LLMClaimExtractor()
    raise SystemExit(f"알 수 없는 추출기: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["google_conflicts", "wikicontradict"], required=True)
    parser.add_argument(
        "--input",
        help="이미 내려받은 데이터셋 파일 경로 (.jsonl/.json/.csv). "
        "생략하면 자동으로 다운로드하여 data/ 아래에 캐시한다.",
    )
    parser.add_argument(
        "--huggingface",
        action="store_true",
        help="wikicontradict를 'datasets' 패키지로 Hugging Face에서 로드(기본은 경량 직접 다운로드)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="캐시된 파일이 있어도 다시 다운로드",
    )
    parser.add_argument("--extractor", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 example 수")
    parser.add_argument("--output", default="output/ontology.ttl", help="온톨로지 저장 경로")
    parser.add_argument("--rdf-format", default="turtle", help="rdflib serialize format (turtle/xml/json-ld 등)")
    parser.add_argument("--claims-json", default=None, help="추출된 Claim 목록을 JSON으로 함께 저장할 경로(선택)")

    args = parser.parse_args()

    examples = load_examples(args)
    print(f"[load] {args.dataset}: {len(examples)}개 example 로드됨")

    extractor = build_extractor(args.extractor)
    graph = OntologyGraph()

    all_claims_dump: list[dict] = []
    for example in examples:
        extracted = extractor.extract(example)
        graph.add_extracted_claims(example, extracted)
        for doc_index, claim in extracted:
            all_claims_dump.append(
                {
                    "example_id": example.id,
                    "doc_index": doc_index,
                    "subject": claim.subject,
                    "predicate": claim.predicate,
                    "object": claim.object,
                    "temporal_scope": claim.temporal_scope,
                    "source": claim.source,
                    "perspective": claim.perspective,
                    "confidence": claim.confidence,
                }
            )

    stats = graph.stats()
    print(f"[extract] claim {len(all_claims_dump)}개 추출")
    print(f"[ontology] {stats}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(str(output_path), format=args.rdf_format)
    print(f"[save] 온톨로지 -> {output_path}")

    if args.claims_json:
        claims_path = Path(args.claims_json)
        claims_path.parent.mkdir(parents=True, exist_ok=True)
        claims_path.write_text(
            json.dumps(all_claims_dump, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[save] Claim 목록 -> {claims_path}")


if __name__ == "__main__":
    main()
