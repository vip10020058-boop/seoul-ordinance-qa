"""4단계: 검색 → Solar 답변 → 검증 → 대회 응답 형식.

설계 원칙 세 가지
  1. LLM은 근거 '번호'만 고릅니다. 조항 표기(citation)는 코드가 조각 라벨로 만듭니다.
  2. source_url · effective_date도 코드가 채웁니다. LLM이 링크나 날짜를 쓰게 두지 않습니다.
  3. 의심스러우면 '확인 불가'. 근거 없는 답은 맞아도 점수가 없고, 함정 문항에서는 감점입니다.
"""
import json
import math
import re
from collections import Counter

import numpy as np

import config

UNKNOWN = {"answer": "확인 불가", "citation": [], "source_url": "", "effective_date": ""}
DISTRICT = re.compile(r"서울특별시\s*\S+구\s")      # 'OO구' 자치구 조례 인용 방지

_cache = {}


# ------------------------------------------------------------ 검색
def _bigrams(text):
    t = re.sub(r"\s+", "", text)
    return [t[i:i + 2] for i in range(len(t) - 1)]


def _load():
    unit = config.CHUNK_UNIT
    if unit in _cache:
        return _cache[unit]
    chunks = json.loads((config.DATA / f"chunks_{unit}.json").read_text(encoding="utf-8"))
    vec_path = config.DATA / f"vectors_{unit}.npy"
    vecs = np.load(vec_path) if vec_path.exists() else None
    if vecs is not None:
        vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    # 키워드 검색용 (글자 2개 단위 BM25)
    docs = [Counter(_bigrams(c["label"] + " " + c["text"])) for c in chunks]
    df = Counter(g for d in docs for g in d)
    avg = sum(sum(d.values()) for d in docs) / len(docs)
    _cache[unit] = (chunks, vecs, docs, df, avg)
    return _cache[unit]


def _bm25(query, docs, df, avg, k1=1.2, b=0.75):
    n = len(docs)
    q = set(_bigrams(query))
    scores = np.zeros(n)
    for i, d in enumerate(docs):
        ln = sum(d.values())
        s = 0.0
        for g in q:
            if g in d:
                idf = math.log(1 + (n - df[g] + 0.5) / (df[g] + 0.5))
                s += idf * d[g] * (k1 + 1) / (d[g] + k1 * (1 - b + b * ln / avg))
        scores[i] = s
    return scores


# 용어·연령·대상의 '정의'를 묻는 질문인지 판별 (정의 조항을 우선 근거로 올리기 위함)
_DEF_QUESTION = re.compile(r"(무엇|뭐|몇\s*살|몇\s*세|나이|연령|정의|기준|이란|라\s*함은|대상.*(누구|무엇)|누구)")
_DEF_LABEL = re.compile(r"\(정의\)")
_DEF_TEXT = re.compile(r"(\(정의\)|(?:이란|란|라 함은).{0,40}말한다)")


def _rerank(question, chunks, idx, score):
    """정의형 질문이면, '정의' 조항에 가산점을 줘 재정렬한다.
    입주대상·사용료 등 표면상 비슷한 조항에 밀려 정의 조항이 누락되는 것을 막는다."""
    if not _DEF_QUESTION.search(question):
        return idx
    boosted = []
    for i in idx:
        s = score[i]
        c = chunks[i]
        if _DEF_LABEL.search(c.get("title", "")) or _DEF_TEXT.search(c["text"][:120]) \
                or "(정의)" in c["text"][:40]:
            s += 0.15
        boosted.append((s, i))
    boosted.sort(reverse=True)
    return [i for _, i in boosted]


def retrieve(question, top_k=config.TOP_K):
    """임베딩(의미) + 키워드(용어) 혼합 검색. 임베딩이 없으면 키워드만 씁니다."""
    chunks, vecs, docs, df, avg = _load()
    kw = _bm25(question, docs, df, avg)
    kw_norm = kw / kw.max() if kw.max() > 0 else kw
    if vecs is not None and config.UPSTAGE_API_KEY:
        import upstage
        q = np.array(upstage.embed([question], config.EMBED_QUERY)[0], dtype=np.float32)
        cos = vecs @ (q / np.linalg.norm(q))
        score = 0.7 * cos + 0.3 * kw_norm          # TODO: 가중치를 공개 예시로 조정해 보세요
    else:
        cos, score = None, kw_norm
    # 넉넉히 뽑은 뒤 정의형 질문이면 재순위화해 상위 top_k를 고른다
    pool = np.argsort(score)[::-1][:max(top_k * 2, 10)]
    idx = _rerank(question, chunks, list(pool), score)[:top_k]
    return [{**chunks[i], "score": float(score[i]),
             "cos": float(cos[i]) if cos is not None else None} for i in idx]


# ------------------------------------------------------------ 답변
SYSTEM = """너는 서울특별시 조례 질의응답 도우미다.
규칙:
- 반드시 아래 [근거]에 적힌 내용만으로 답한다. 근거에 없는 내용은 추측하지 않는다.
- [근거]는 검색 점수순이지 정답순이 아니다. 질문에 가장 정확히 답하는 근거를 네가 직접 고른다.
  · 용어의 정의·나이·기준을 묻는 질문은 "정의"(제○조(정의)) 조항을 최우선 근거로 삼는다.
  · 금액·요금을 묻는 질문은 요금표(별표)나 해당 금액이 적힌 조항을 근거로 삼는다.
  · 가부(되나요/받을 수 있나요)를 묻는 질문은 요건·감면·예외가 적힌 조항을 근거로 삼는다.
- 답은 일반 시민이 이해할 수 있는 쉬운 말로 2~4문장으로 쓴다. 금액·비율·나이 같은 숫자는 그대로 쓴다.
  조건을 묻는 질문은 "네/아니요"로 시작하고, '다만·예외' 같은 단서가 있으면 함께 적는다.
- 답에 실제로 쓴 근거의 번호만 evidence_ids에 넣는다. 읽기만 하고 답에 안 쓴 근거는 넣지 않는다.
  여러 조항을 함께 썼다면 모두 넣는다.
- 근거 어디에도 답이 없으면 found를 false로 한다.
- 자치구(OO구) 조례나 규칙은 근거로 쓰지 않는다.
결과는 JSON으로 낸다."""

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "law_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "found": {"type": "boolean"},
                "answer": {"type": "string"},
                "evidence_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["found", "answer", "evidence_ids"],
            "additionalProperties": False,
        },
    },
}


def _context(hits):
    return "\n\n".join(f"[근거 {i}] {h['label']}\n{h['text']}" for i, h in enumerate(hits, 1))


_EXPAND_SYSTEM = """사용자의 일상어 질문을, 서울시 조례 조문에서 쓰는 법령 용어로 바꾼 검색어를 만든다.
핵심 개념의 조문식 표현(예: '몇 살'→'연령 정의', '벌금'→'과태료', '깎아주나'→'감면')을 포함한다.
쉼표로 구분한 한 줄 키워드만 출력한다."""


def _expanded_query(question):
    """질문을 조문 용어로 확장한 보조 검색어. 실패하면 원 질문을 그대로 쓴다."""
    try:
        import upstage
        kw = upstage.chat(
            [{"role": "system", "content": _EXPAND_SYSTEM},
             {"role": "user", "content": question}], temperature=0.0)
        return f"{question} {kw}".strip()
    except Exception:  # noqa: BLE001  확장 실패는 치명적이지 않다
        return question


def _is_def_chunk(h):
    return _DEF_TEXT.search(h["text"][:120]) or "(정의)" in h["text"][:40]


def _merged_retrieve(question, top_k=config.TOP_K):
    """원 질문 + 조문용어 확장 질문으로 각각 검색해 합친다(중복 라벨 제거, 높은 점수 우선).
    정의형 질문이면 '정의' 조항을 맨 앞으로 끌어올린다."""
    base = retrieve(question, top_k=top_k)
    merged = base
    if config.UPSTAGE_API_KEY:
        expanded = _expanded_query(question)
        if expanded != question:
            extra = retrieve(expanded, top_k=top_k)
            best = {}
            for h in base + extra:
                cur = best.get(h["label"])
                if cur is None or (h["score"] or 0) > (cur["score"] or 0):
                    best[h["label"]] = h
            merged = sorted(best.values(), key=lambda h: h["score"] or 0, reverse=True)
    # 정의형 질문이면 정의 조항을 선두로 (LLM이 정의 조항을 1순위 근거로 보게 함)
    if _DEF_QUESTION.search(question):
        merged.sort(key=lambda h: 0 if _is_def_chunk(h) else 1)
    return merged[:top_k]


def answer(question):
    import upstage
    hits = _merged_retrieve(question)

    # 검증 ①: 검색 단계에서 이미 관련 조문이 없어 보이면 바로 '확인 불가'
    if config.USE_VERIFY and hits and hits[0]["cos"] is not None and hits[0]["cos"] < config.MIN_SCORE:
        return dict(UNKNOWN)

    raw = upstage.chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": f"[근거]\n{_context(hits)}\n\n[질문]\n{question}"}],
        response_format=SCHEMA)
    out = json.loads(raw)
    used = [hits[i - 1] for i in out.get("evidence_ids", []) if 1 <= i <= len(hits)]
    used = [h for h in used if not DISTRICT.search(h["label"])]
    if not out.get("found") or not used:
        return dict(UNKNOWN)

    # 검증 ②: 답이 고른 근거에 실제로 기반하는지 Groundedness Check.
    # notGrounded만 보류한다. 단, 검색 신뢰도(top1 cos)가 충분히 높으면 1회 재판정해
    #   LLM 검증의 비결정성으로 정답이 버려지는 것을 줄인다. (notSure는 통과)
    if config.USE_VERIFY:
        verdict = upstage.groundedness(_context(used), out["answer"])
        if verdict == "notGrounded":
            top_cos = used[0].get("cos")
            if top_cos is not None and top_cos >= config.RECHECK_COS:
                verdict = upstage.groundedness(_context(used), out["answer"])
            if verdict == "notGrounded":
                return dict(UNKNOWN)

    citation = list(dict.fromkeys(h["label"] for h in used))   # 순서 유지, 중복 제거
    first = used[0]
    return {"answer": out["answer"], "citation": citation,
            "source_url": first["source_url"], "effective_date": first["effective_date"]}


def answer_without_rag(question):
    """시연용 '전' 장면: 검색 없이 LLM만으로 답하게 하면 어떻게 되는가."""
    import upstage
    return upstage.chat([
        {"role": "system", "content": "너는 서울시 조례 전문가다. 답과 함께 근거 조항(제○조 제○항)과 원문 링크, 시행일을 적어라."},
        {"role": "user", "content": question}], temperature=0.3)
