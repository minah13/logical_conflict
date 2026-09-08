"""GoldExample + Claim 목록을 RDF/OWL/SKOS 온톨로지(ABox)로 적재한다.

연구 설계서 2단계("Ontology Construction")의 구현체.
스키마(TBox)는 :mod:`ontology.schema` 에서 정의하고, 이 모듈은 실제 데이터
인스턴스(ABox)를 그래프에 채워 넣는다.
"""

from __future__ import annotations

import re

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD

from dataset.base import GoldExample
from models import Claim
from ontology.namespace import LC, RDF, RDFS
from ontology.schema import attach_schema, normalize_concept

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", str(value)).strip("_")
    return slug or "unknown"


class OntologyGraph:
    """온톨로지 스키마(TBox) + 인스턴스 데이터(ABox)를 담는 rdflib 그래프 래퍼."""

    def __init__(self) -> None:
        self.graph = Graph()
        attach_schema(self.graph)
        self._document_cache: dict[tuple[str, int], URIRef] = {}
        self._perspective_cache: dict[str, URIRef] = {}

    # -- Perspective ---------------------------------------------------
    def _perspective_uri(self, name: str) -> URIRef:
        name = name or "unknown"
        slug = _slugify(name)
        uri = LC[f"perspective/{slug}"]
        if slug not in self._perspective_cache:
            self.graph.add((uri, RDF.type, LC.Perspective))
            self.graph.add((uri, RDFS.label, Literal(name)))
            self._perspective_cache[slug] = uri
        return uri

    # -- Example / Document ---------------------------------------------------
    def add_example(self, example: GoldExample) -> URIRef:
        """GoldExample과 그에 속한 모든 검색 문서를 그래프에 추가한다."""

        g = self.graph
        example_uri = LC[f"example/{_slugify(example.id)}"]
        g.add((example_uri, RDF.type, LC.Example))
        g.add((example_uri, LC.queryText, Literal(example.query)))
        g.add((example_uri, LC.goldLabel, Literal(example.gold_label)))
        g.add((example_uri, LC.sourceDataset, Literal(example.source_dataset)))

        category = example.raw.get("_contradiction_type") or example.raw.get("conflict_type")
        if category:
            g.add((example_uri, LC.contradictionCategory, Literal(str(category))))

        for idx, doc in enumerate(example.documents):
            doc_uri = self.add_document(example.id, idx, doc)
            g.add((example_uri, LC.hasDocument, doc_uri))

        return example_uri

    def add_document(self, example_id: str, doc_index: int, doc: dict) -> URIRef:
        key = (example_id, doc_index)
        if key in self._document_cache:
            return self._document_cache[key]

        g = self.graph
        doc_uri = LC[f"document/{_slugify(example_id)}/{doc_index}"]
        g.add((doc_uri, RDF.type, LC.Document))
        g.add((doc_uri, LC.documentText, Literal(doc.get("text", ""))))
        source = doc.get("source", f"doc-{doc_index}")
        g.add((doc_uri, LC.documentSource, Literal(source)))
        g.add((doc_uri, LC.hasPerspective, self._perspective_uri(source)))

        self._document_cache[key] = doc_uri
        return doc_uri

    # -- Claim ---------------------------------------------------
    def add_claim(
        self,
        claim: Claim,
        example_uri: URIRef | None = None,
        document_uri: URIRef | None = None,
    ) -> URIRef:
        g = self.graph
        claim_uri = LC[f"claim/{_slugify(claim.id)}"]
        g.add((claim_uri, RDF.type, LC.Claim))
        g.add((claim_uri, LC.subjectText, Literal(claim.subject)))
        g.add((claim_uri, LC.predicateText, Literal(claim.predicate)))
        g.add((claim_uri, LC.objectText, Literal(claim.object)))
        if claim.temporal_scope:
            g.add((claim_uri, LC.temporalScope, Literal(claim.temporal_scope)))
        g.add((claim_uri, LC.claimScope, Literal(claim.scope)))
        g.add((claim_uri, LC.confidence, Literal(claim.confidence, datatype=XSD.float)))
        if claim.extracted_from:
            g.add((claim_uri, LC.extractedFrom, Literal(claim.extracted_from)))
        g.add((claim_uri, LC.sourceName, Literal(claim.source)))
        g.add((claim_uri, LC.claimPerspective, self._perspective_uri(claim.perspective)))

        concept_name = normalize_concept(claim.object)
        if concept_name:
            g.add((claim_uri, LC.objectConcept, LC[concept_name]))

        if example_uri is not None:
            g.add((example_uri, LC.hasClaim, claim_uri))
        if document_uri is not None:
            g.add((claim_uri, LC.extractedFromDocument, document_uri))

        return claim_uri

    def add_extracted_claims(
        self,
        example: GoldExample,
        extracted: list[tuple[int, Claim]],
    ) -> URIRef:
        """하나의 GoldExample과, 그로부터 추출된 (문서 인덱스, Claim) 목록을 적재한다."""

        example_uri = self.add_example(example)
        for doc_index, claim in extracted:
            document_uri = self._document_cache.get((example.id, doc_index))
            self.add_claim(claim, example_uri=example_uri, document_uri=document_uri)
        return example_uri

    # -- Output ---------------------------------------------------
    def serialize(self, path: str, format: str = "turtle") -> None:
        self.graph.serialize(destination=path, format=format)

    def stats(self) -> dict[str, int]:
        return {
            "triples": len(self.graph),
            "examples": len(list(self.graph.subjects(RDF.type, LC.Example))),
            "documents": len(list(self.graph.subjects(RDF.type, LC.Document))),
            "claims": len(list(self.graph.subjects(RDF.type, LC.Claim))),
            "perspectives": len(list(self.graph.subjects(RDF.type, LC.Perspective))),
        }
