from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

# 본 연구 온톨로지의 기본 네임스페이스.
LC = Namespace("http://logical-conflict.example.org/ontology#")

__all__ = ["LC", "OWL", "RDF", "RDFS", "SKOS", "XSD"]
