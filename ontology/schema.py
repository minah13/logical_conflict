"""RDF/OWL/SKOS 스키마(TBox) 정의.

연구 설계서 2단계("Ontology Construction")에서 기술한 세 가지 요소를 구현한다.

- RDF  : Claim/Document/Perspective/Example 을 위한 클래스와 속성
- OWL  : 상호 배타적인 값(Increase/Decrease 등)에 대한 disjointWith 제약
- SKOS : 서로 다른 표현으로 등장하는 동의어 개념을 연결 (예: Growth ~ Increase)
"""

from __future__ import annotations

from rdflib import Graph, Literal
from rdflib.namespace import XSD

from ontology.namespace import LC, OWL, RDF, RDFS, SKOS

# ---------------------------------------------------------------------------
# 클래스
# ---------------------------------------------------------------------------
CLASSES = [
    (LC.Example, "검색 질의 하나에 대응하는 사례(질의 + 검색 문서 집합)"),
    (LC.Document, "검색된 개별 문서"),
    (LC.Perspective, "문서가 속한 출처/관점"),
    (LC.Claim, "문서에서 추출된 주장(Subject-Predicate-Object triple)"),
    (LC.Concept, "Claim의 object 값을 정규화한 통제 어휘 개념"),
]

# ---------------------------------------------------------------------------
# 속성
# ---------------------------------------------------------------------------
OBJECT_PROPERTIES = [
    (LC.hasDocument, LC.Example, LC.Document, "Example이 포함하는 검색 문서"),
    (LC.hasClaim, LC.Example, LC.Claim, "Example에서 추출된 Claim"),
    (LC.extractedFromDocument, LC.Claim, LC.Document, "Claim이 추출된 원본 문서"),
    (LC.hasPerspective, LC.Document, LC.Perspective, "문서가 속한 관점"),
    (LC.claimPerspective, LC.Claim, LC.Perspective, "Claim이 속한 관점"),
    (LC.objectConcept, LC.Claim, LC.Concept, "Claim object 값의 정규화된 개념"),
]

DATATYPE_PROPERTIES = [
    (LC.subjectText, LC.Claim, XSD.string, "Claim의 subject 원문"),
    (LC.predicateText, LC.Claim, XSD.string, "Claim의 predicate 원문"),
    (LC.objectText, LC.Claim, XSD.string, "Claim의 object 원문"),
    (LC.temporalScope, LC.Claim, XSD.string, "Claim이 적용되는 시점/기간"),
    (LC.claimScope, LC.Claim, XSD.string, "Claim이 적용되는 범위(지역 등)"),
    (LC.confidence, LC.Claim, XSD.float, "Claim 추출 신뢰도"),
    (LC.extractedFrom, LC.Claim, XSD.string, "Claim이 추출된 원문 발췌"),
    (LC.sourceName, LC.Claim, XSD.string, "Claim 출처 식별자"),
    (LC.documentText, LC.Document, XSD.string, "문서 원문"),
    (LC.documentSource, LC.Document, XSD.string, "문서 출처 식별자(URL 등)"),
    (LC.queryText, LC.Example, XSD.string, "질의 원문"),
    (LC.goldLabel, LC.Example, XSD.string, "정답 레이블(4단계 분류)"),
    (LC.sourceDataset, LC.Example, XSD.string, "원본 데이터셋 이름"),
    (LC.contradictionCategory, LC.Example, XSD.string, "원본 데이터셋의 세부 모순 유형"),
]

# ---------------------------------------------------------------------------
# 통제 어휘(Concept) 및 OWL disjointWith 제약
#
# 각 그룹 내부의 개념들은 동일한 subject/predicate/temporalScope 하에서
# 동시에 참일 수 없는 상호 배타적 값이다. (예: Increase와 Decrease)
# ---------------------------------------------------------------------------
DISJOINT_GROUPS: dict[str, list[str]] = {
    "Trend": ["Increase", "Decrease", "Stable"],
    "Polarity": ["Yes", "No"],
}

# SKOS closeMatch: 서로 다른 어휘로 등장하지만 동일 개념을 가리키는 대체 개념.
# (예: "Revenue Growth" 라는 표현과 "Sales Increase" 라는 표현을 Increase로 통합)
SKOS_CLOSE_MATCHES: dict[str, list[str]] = {
    "Increase": ["Growth", "Improvement", "Rise"],
    "Decrease": ["Decline", "Downturn", "Fall"],
}


# 자연어 표현 -> 통제 어휘(canonical concept) 매핑.
# HeuristicClaimExtractor가 이 사전을 이용해 원문 텍스트를 Concept로 정규화한다.
CONCEPT_LEXICON: dict[str, list[str]] = {
    "Increase": [
        "증가", "상승", "성장", "급증", "확대", "개선",
        "growth", "increase", "increased", "increasing", "rise", "rose",
        "rising", "grew", "surge", "surged", "up", "improve", "improved",
        "improvement", "higher",
    ],
    "Decrease": [
        "감소", "하락", "축소", "급감", "둔화", "악화",
        "decline", "declined", "declining", "decrease", "decreased",
        "decreasing", "fall", "fell", "falling", "drop", "dropped",
        "down", "shrink", "shrank", "worsen", "worsened", "lower",
    ],
    "Stable": [
        "유지", "보합", "변동없음", "stable", "unchanged", "flat", "steady",
    ],
    "Yes": ["yes", "true"],
    "No": ["no", "false"],
}


_CONCEPT_PATTERNS: dict[str, list["re.Pattern[str]"]] | None = None


def _concept_patterns() -> dict[str, list["re.Pattern[str]"]]:
    global _CONCEPT_PATTERNS
    if _CONCEPT_PATTERNS is None:
        import re

        _CONCEPT_PATTERNS = {
            canonical: [re.compile(rf"\b{re.escape(term.lower())}\b") for term in terms]
            for canonical, terms in CONCEPT_LEXICON.items()
        }
    return _CONCEPT_PATTERNS


def normalize_concept(text: str) -> str | None:
    """자유 텍스트를 통제 어휘 개념 이름(예: "Increase")으로 정규화한다.

    단어 경계 기준으로 매치하여 "know"/"Norway"의 "no" 같은 부분 문자열
    오탐을 방지한다. 가장 먼저 매치되는 개념을 반환하며, 매치되는 개념이
    없으면 None을 반환한다.
    """

    lowered = text.lower()
    for canonical, patterns in _concept_patterns().items():
        for pattern in patterns:
            if pattern.search(lowered):
                return canonical
    return None


def build_schema_graph() -> Graph:
    """TBox(스키마)만 담은 새 rdflib.Graph를 생성해 반환한다."""

    g = Graph()
    attach_schema(g)
    return g


def attach_schema(g: Graph) -> Graph:
    """전달된 그래프에 온톨로지 스키마(TBox) 트리플을 추가한다."""

    g.bind("lc", LC)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("rdfs", RDFS)

    g.add((LC[""], RDF.type, OWL.Ontology))

    for cls, comment in CLASSES:
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.comment, Literal(comment, lang="ko")))

    for prop, domain, range_, comment in OBJECT_PROPERTIES:
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.domain, domain))
        g.add((prop, RDFS.range, range_))
        g.add((prop, RDFS.comment, Literal(comment, lang="ko")))

    for prop, domain, range_, comment in DATATYPE_PROPERTIES:
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.domain, domain))
        g.add((prop, RDFS.range, range_))
        g.add((prop, RDFS.comment, Literal(comment, lang="ko")))

    concept_scheme = LC.ControlledVocabulary
    g.add((concept_scheme, RDF.type, SKOS.ConceptScheme))

    for group_name, members in DISJOINT_GROUPS.items():
        member_uris = [LC[name] for name in members]
        for uri, name in zip(member_uris, members):
            g.add((uri, RDF.type, OWL.Class))
            g.add((uri, RDFS.subClassOf, LC.Concept))
            g.add((uri, RDF.type, SKOS.Concept))
            g.add((uri, SKOS.inScheme, concept_scheme))
            g.add((uri, SKOS.prefLabel, Literal(name, lang="en")))
            g.add((uri, RDFS.label, Literal(f"{group_name}:{name}")))
        # 그룹 내 모든 쌍에 대해 owl:disjointWith 를 추가한다.
        for i, uri_a in enumerate(member_uris):
            for uri_b in member_uris[i + 1 :]:
                g.add((uri_a, OWL.disjointWith, uri_b))
                g.add((uri_b, OWL.disjointWith, uri_a))

    for canonical, alt_names in SKOS_CLOSE_MATCHES.items():
        canonical_uri = LC[canonical]
        for alt_name in alt_names:
            alt_uri = LC[f"alt_{canonical}_{alt_name}"]
            g.add((alt_uri, RDF.type, SKOS.Concept))
            g.add((alt_uri, SKOS.inScheme, concept_scheme))
            g.add((alt_uri, SKOS.prefLabel, Literal(alt_name, lang="en")))
            g.add((alt_uri, SKOS.closeMatch, canonical_uri))
            g.add((canonical_uri, SKOS.closeMatch, alt_uri))

    return g
