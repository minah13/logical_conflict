# Ontology-based Perspective-Aware Contradiction Detection for Explainable RAG

## 문제 정의

Retrieval-Augmented Generation(RAG)은 외부 문서를 검색하여 LLM의 응답 생성에 활용함으로써 환각(Hallucination)을 줄이고 최신 정보를 반영할 수 있다.

그러나 실제 환경에서는 검색된 문서들이 항상 동일한 사실을 말하지 않는다.

예를 들어 동일한 질의에 대해 다음과 같은 문서가 검색될 수 있다.

> 문서 A : "Tesla의 2024년 매출은 증가할 것으로 예상된다."

> 문서 B : "Tesla의 2024년 매출은 감소할 것으로 예상된다."

현재 대부분의 RAG 시스템은 이러한 정보를 단순히 결합하여 LLM에 전달한다.

이 과정에서 LLM은

- 하나를 임의로 선택하거나
- 두 정보를 혼합하거나
- 모순 자체를 인식하지 못하는

문제가 발생한다.

특히 기존 RAG 연구는

- Retrieval
- Re-ranking
- Chunking
- Context Compression

에 집중되어 있으며, 검색된 문서들 사이의 논리적 관계(Logical Relation)는 거의 다루지 않는다.

---

## 연구 목표

본 연구의 목표는 단순 의미 유사도(Semantic Similarity)가 아닌 논리적 수준(Logical Level)에서 문서 간 모순을 탐지하는 것이다.

이를 위해 다음 질문을 다룬다.

- 서로 다른 관점과 실제 모순을 구분할 수 있는가?
- LLM이 생성한 Claim을 논리적으로 검증할 수 있는가?
- 모순의 발생 원인을 설명 가능한 형태로 제공할 수 있는가?
- RAG 응답의 신뢰성을 향상시킬 수 있는가?

---

# 핵심 아이디어

본 연구는 세 가지 원칙을 기반으로 한다.

## 1. 가능한 설명은 최대한 유지한다

현실 세계에서는 하나의 사건에 대해 여러 해석이 존재할 수 있다.

예를 들어

```text
Tesla 매출 증가

Tesla 매출 감소

중국 시장 감소, 북미 시장 증가
```

는 서로 다른 설명이다.

기존 시스템은 초기 단계에서 하나를 선택하려고 하지만,

본 연구는 Rashomon Effect 개념을 적용하여 여러 설명을 동시에 유지한다.

이를 Possible Worlds라고 정의한다.

```text
World 1
매출 증가

World 2
매출 감소

World 3
지역별 차이 존재
```

초기 단계에서는 어떤 세계도 제거하지 않는다.

---

## 2. 결정은 최대한 늦게 한다

초기 선택은 정보 손실을 발생시킨다.

따라서

- 문서를 합치지 않고
- 관점을 분리하여 유지하고
- 가능한 설명을 모두 생성한 뒤

후속 검증 단계에서 판단한다.

이를 통해

Perspective Divergence와 실제 Contradiction을 구분할 수 있다.

---

## 3. 후보 생성과 최종 선택은 다른 문제이다

기존 연구는 모순 탐지 자체를 목표로 한다.

그러나 실제로는

```text
좋은 후보 생성
≠
올바른 후보 선택
```

이다.

예를 들어

```text
매출 증가

매출 감소

시장별 차이
```

세 가지 설명이 모두 생성될 수 있다.

중요한 것은

"후보를 만드는 것"이 아니라

"어떤 후보가 가장 타당한가"

를 판단하는 것이다.

따라서 본 연구는

### Candidate Generation

가능한 설명 생성

### Candidate Verification

논리 검증

### Final Adjudication

최종 선택

을 분리하여 수행한다.

---

# 제안 방법론

## Step 1. Claim Extraction

LLM을 활용하여 자연어 문서를 구조화된 Claim으로 변환한다.

예)

```json
{
  "subject": "Tesla",
  "predicate": "RevenueTrend",
  "object": "Increase",
  "year": "2024"
}
```

---

## Step 2. Ontology Construction

Claim을 RDF Triple로 표현한다.

```text
Tesla
 ├─ RevenueTrend
 └─ Increase
```

OWL을 이용하여 논리 규칙을 정의한다.

```text
Increase disjointWith Decrease
```

SKOS를 이용하여 의미적으로 유사한 개념을 연결한다.

```text
Revenue Growth
≈
Sales Increase
```

이를 통해 자연어 표현 차이를 제거한다.

---

## Step 3. Perspective Separation

문서를 하나의 사실 집합으로 합치지 않는다.

```text
Document A
→ Perspective A

Document B
→ Perspective B
```

관점별로 독립적인 Claim Set을 구성한다.

---

## Step 4. Rashomon World Construction

동일 사건에 대한 여러 설명을 유지한다.

```text
World 1
Revenue Increase

World 2
Revenue Decrease

World 3
Regional Difference
```

이 단계의 목적은

"정답 찾기"

가 아니라

"가능한 설명 보존"

이다.

---

## Step 5. Tableau Verification

Tableau Reasoning을 이용하여 논리적으로 불가능한 후보를 제거한다.

예)

```text
Tesla
RevenueTrend
Increase

Tesla
RevenueTrend
Decrease
```

Ontology 규칙

```text
Increase ⊥ Decrease
```

검증 결과

```text
Increase AND Decrease

→ UNSAT
```

즉,

논리적으로 불가능한 World를 제거한다.

Tableau의 역할은

정답 선택이 아니라

불가능한 후보 제거이다.

---

## Step 6. Evidence-aware Adjudication

Tableau를 통과한 후보들 중 최종 후보를 선택한다.

평가 요소

- 출처 신뢰도
- 증거 개수
- 증거 품질
- 최신성
- 의미적 지지도

이를 기반으로

```text
Support
Contradiction
Neutral
```

점수를 계산한다.

---

# Explainable RAG

최종적으로 사용자는 단순 결과가 아니라

왜 그런 판단이 내려졌는지 확인할 수 있다.

예)

```text
Claim A
↓
Revenue Increase

Claim B
↓
Revenue Decrease

Increase disjointWith Decrease

↓
Contradiction
```

따라서 시스템은

"무엇이 모순인가"

뿐만 아니라

"왜 모순인가"

까지 설명할 수 있다.

---

# 기대 효과

- RAG의 논리적 일관성 향상
- 관점 차이와 실제 모순 구분
- Implicit Contradiction 탐지
- Explainable AI 구현
- 금융, 의료, 법률 분야의 고신뢰 RAG 지원
- Candidate Generation과 Final Selection의 분리 연구

---

# 연구 가설

본 연구는 다음 가설을 검증하고자 한다.

> "Rashomon 기반 다중 설명 보존과 Ontology + Tableau 기반 논리 검증을 결합하면, 기존 RAG 및 NLI 기반 접근법보다 문서 간 논리적 모순을 더 정확하게 탐지하고 설명할 수 있다."
