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
  · '둘 다/중복/함께' 받을 수 있는지 묻는 질문은, 각 혜택 조항뿐 아니라 "둘 이상의 사유에
    해당하면 높은 하나만 적용한다" 같은 중복 적용 제한 조항이 근거에 있으면 반드시 함께 보고
    답한다. 그런 제한 조항이 있으면 "중복해서 받을 수 없고 감면율이 높은 하나만 적용된다"고
    명확히 답하며, 그 조항 번호를 evidence_ids에 반드시 포함한다.
- 질문이 한두 단어의 키워드(예: "담배 구역", "주차 요금")여도, 근거에서 그 주제의 핵심 내용
  (지정 기준·금액·요건 등)을 찾아 요약해 답한다. 근거에 관련 조문이 있으면 found를 true로 한다.
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


# '둘 이상의 감면/할인 사유에 해당하면 높은 하나만 적용' 류의 중복 적용 제한 조항을 포착한다.
_OVERLAP_LIMIT = re.compile(
    r"둘\s*이상.{0,30}(감면|할인|사유).{0,40}(하나만|가장\s*(높은|많은)|높은\s*하나)")
# 두 혜택을 '둘 다/함께/동시에/중복' 받을 수 있는지 묻는 질문인지 판별한다.
_OVERLAP_QUESTION = re.compile(r"(둘\s*다|두\s*가지|함께|같이|동시에|중복|모두)")


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
    result = merged[:top_k]
    # 중복 여부(둘 다/함께/중복) 질문이면 '중복 적용 제한' 조항을 반드시 상위 근거에 포함한다.
    # 이 조항(예: "둘 이상의 감면사유에 해당하면 높은 하나만 적용")은 문장이 짧아 임베딩
    # 유사도가 낮게 나와 top_k에 못 드는 경우가 많다. 상위 근거가 가리키는 '같은 법령'에서
    # 전체 조각을 뒤져 중복 제한 조항을 찾아 맨 앞에 끼워 넣는다.
    if _OVERLAP_QUESTION.search(question) and result:
        if not any(_OVERLAP_LIMIT.search(h["text"]) for h in result):
            limit_chunk = _find_overlap_limit(result)
            if limit_chunk is not None:
                result = [limit_chunk] + result[:top_k - 1]
        result.sort(key=lambda h: 0 if _OVERLAP_LIMIT.search(h["text"]) else 1)
    return result


def _find_overlap_limit(result):
    """상위 근거가 속한 법령들 안에서 '중복 적용 제한' 조항 조각을 찾아 반환(없으면 None).

    score·cos는 상위 근거의 최댓값을 승계한다(이 조항은 '같은 법령'에서 질문 쟁점의 전제로
    확실히 관련되므로, 짧은 문장 탓에 낮게 나오는 자체 임베딩 유사도 대신 검색 신뢰도를 쓴다)."""
    chunks, _, _, _, _ = _load()
    laws = {h.get("law") or h["label"].split(" 제")[0] for h in result}
    top_score = max((h["score"] or 0) for h in result)
    cos_vals = [h["cos"] for h in result if h.get("cos") is not None]
    top_cos = max(cos_vals) if cos_vals else None
    for c in chunks:
        law = c.get("law") or c["label"].split(" 제")[0]
        if law in laws and _OVERLAP_LIMIT.search(c["text"]) and not DISTRICT.search(c["label"]):
            return {**c, "score": top_score, "cos": top_cos}
    return None


def _detail(response, verification_status, used=None, unknown_reason=""):
    """웹 전용 메타데이터를 보존하되, 대회 응답 형식과 분리합니다."""
    return {
        "response": response,
        "verification_status": verification_status,
        "used": used or [],
        "unknown_reason": unknown_reason,
    }


def answer_detailed(question):
    """대회 응답과 웹용 근거 메타데이터를 함께 생성합니다.

    `answer()`는 이 함수의 response만 반환하므로 대회 4필드 계약은 바뀌지 않습니다.
    """
    import upstage
    hits = _merged_retrieve(question)

    # 검증 ①: 검색 단계에서 이미 관련 조문이 없어 보이면 바로 '확인 불가'
    if config.USE_VERIFY and hits and hits[0]["cos"] is not None and hits[0]["cos"] < config.MIN_SCORE:
        return _detail(dict(UNKNOWN), "unavailable", unknown_reason="retrieval_low")

    # 중복(둘 다/함께) 질문이고 검색에 '중복 적용 제한' 조항이 있으면, LLM이 그 조항을 놓치거나
    # 반대로 답하지 않도록 질문 끝에 명시적 지시를 덧붙인다(근거 자체는 [근거]에 이미 들어 있다).
    hint = ""
    if _OVERLAP_QUESTION.search(question) and any(_OVERLAP_LIMIT.search(h["text"]) for h in hits):
        hint = ("\n\n[지시] 이 질문은 두 혜택을 '둘 다' 받을 수 있는지를 묻는다. 근거 중 "
                "'둘 이상의 사유에 해당하면 높은 하나만 적용한다'는 중복 적용 제한 조항을 반드시 "
                "반영해, 중복해서 받을 수 없고 감면율이 높은 하나만 적용된다고 답하고 그 조항 "
                "번호를 evidence_ids에 포함하라.")

    raw = upstage.chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": f"[근거]\n{_context(hits)}\n\n[질문]\n{question}{hint}"}],
        response_format=SCHEMA)
    out = json.loads(raw)
    used = [hits[i - 1] for i in out.get("evidence_ids", []) if 1 <= i <= len(hits)]
    used = [h for h in used if not DISTRICT.search(h["label"])]
    if not out.get("found") or not used:
        return _detail(dict(UNKNOWN), "unavailable", unknown_reason="no_supported_answer")

    # 검증 ②: 답이 고른 근거에 실제로 기반하는지 Groundedness Check.
    #
    # 채점 구조상 '일반 문항에서의 확인 불가 = 0점'이 가장 큰 손실이다. 반대로 함정(근거 없는)
    # 문항은 이미 검색 단계(retrieval_low)와 found/used 단계에서 걸러진다. 따라서 검증기는
    # '검색이 애매한데 LLM이 억지로 답한 경우'를 거르는 데만 쓰고, 검색이 확실한(top1 cos가
    # 충분히 높은) 답은 LLM 검증이 흔들려 notGrounded를 내더라도 버리지 않는다.
    #   - top1 cos >= RECHECK_COS : notGrounded여도 답 보존(상태만 not_sure). 1회 재판정으로
    #                               grounded가 회복되면 그대로 grounded.
    #   - top1 cos <  RECHECK_COS : notGrounded면 확인 불가 처리(근거가 약해 신뢰 어려움).
    verdict = "not_checked"
    if config.USE_VERIFY:
        verdict = upstage.groundedness(_context(used), out["answer"])
        if verdict == "notGrounded":
            top_cos = used[0].get("cos")
            if top_cos is not None and top_cos >= config.RECHECK_COS:
                verdict = upstage.groundedness(_context(used), out["answer"])
                if verdict == "notGrounded":
                    # 검색은 확실하다 → 정답일 가능성이 높으므로 보존하고 상태만 보류로 표시
                    verdict = "notSure"
            else:
                return _detail(dict(UNKNOWN), "not_grounded", unknown_reason="verification_failed")

    # 근거 보강: 중복(둘 다/함께) 질문이고 검색에 '중복 적용 제한' 조항이 있으면, LLM이 근거
    # 번호를 누락했더라도 그 조항을 근거에 보탠다. 답 내용은 위 [지시]로 교정되고, 근거는 코드가
    # 보강해 '내용은 맞는데 조항 번호만 빠지는' 흔들림을 없앤다(해당 조항이 없으면 아무것도 안 함).
    if _OVERLAP_QUESTION.search(question):
        used_labels = {h["label"] for h in used}
        for h in hits:
            if h["label"] in used_labels or DISTRICT.search(h["label"]):
                continue
            if _OVERLAP_LIMIT.search(h["text"]):
                used.append(h)
                break

    citation = list(dict.fromkeys(h["label"] for h in used))   # 순서 유지, 중복 제거
    first = used[0]
    response = {"answer": out["answer"], "citation": citation,
                "source_url": first["source_url"], "effective_date": first["effective_date"]}
    status = {"grounded": "grounded", "notSure": "not_sure"}.get(verdict, "not_checked")
    return _detail(response, status, used=used)


def answer(question):
    """대회 채점용 4필드 응답만 반환합니다."""
    return answer_detailed(question)["response"]


def answer_without_rag(question):
    """시연용 '전' 장면: 검색 없이 LLM만으로 답하게 하면 어떻게 되는가."""
    import upstage
    return upstage.chat([
        {"role": "system", "content": "너는 서울시 조례 전문가다. 답과 함께 근거 조항(제○조 제○항)과 원문 링크, 시행일을 적어라."},
        {"role": "user", "content": question}], temperature=0.3)
