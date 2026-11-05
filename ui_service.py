"""시민용 웹에 필요한 상세 근거·선택지·체크리스트를 구성합니다.

대회 채점용 `rag.answer()`와 `/ask`의 4필드 계약은 변경하지 않습니다.
"""
import re

import rag


CLARIFICATION_RULES = [
    (
        re.compile(r"^(?:담배|흡연|금연)(?:\s*(?:구역|지역|장소))?$"),
        "담배·금연구역과 관련해 무엇을 알고 싶은지 선택해 주세요.",
        [
            "서울시 금연구역은 어디에 지정되나요?",
            "금연구역에서 담배를 피우면 과태료가 얼마인가요?",
            "금연구역 안에 흡연구역을 설치할 수 있나요?",
        ],
    ),
    (
        re.compile(r"^(?:주차|주차장|주차비|주차\s*할인)$"),
        "주차와 관련해 어떤 내용을 알고 싶은지 선택해 주세요.",
        [
            "서울시 공영주차장 요금은 얼마인가요?",
            "공영주차장에 경차를 세우면 할인되나요?",
            "장애인 할인과 다둥이 할인을 중복으로 받을 수 있나요?",
        ],
    ),
    (
        re.compile(r"^(?:청년|청년\s*지원|청년\s*정책)$"),
        "청년 정책과 관련해 무엇을 알고 싶은지 선택해 주세요.",
        [
            "서울시 청년 기본 조례에서 청년은 몇 살까지인가요?",
            "서울시 청년시설 입주 대상은 누구인가요?",
            "의무복무 제대군인은 청년 연령을 연장받을 수 있나요?",
        ],
    ),
    (
        re.compile(r"^(?:동물|반려동물|강아지|고양이|동물\s*등록)$"),
        "반려동물과 관련해 무엇을 알고 싶은지 선택해 주세요.",
        [
            "유기견을 입양해 동물등록하면 등록수수료를 내야 하나요?",
            "동물등록 수수료를 감면받을 수 있는 경우는 무엇인가요?",
            "서울시 동물보호 조례의 지원 대상은 누구인가요?",
        ],
    ),
    (
        re.compile(r"^(?:자전거|자전거\s*주차|자전거\s*도로)$"),
        "자전거 이용과 관련해 무엇을 알고 싶은지 선택해 주세요.",
        [
            "서울시 자전거주차장은 무료인가요?",
            "자전거주차장 요금을 받는 경우 얼마인가요?",
            "서울시가 자전거 이용 활성화를 위해 지원하는 것은 무엇인가요?",
        ],
    ),
    (
        re.compile(r"^(?:공원|도시공원|어린이공원)$"),
        "공원 이용과 관련해 무엇을 알고 싶은지 선택해 주세요.",
        [
            "어린이공원에서 술을 마시면 과태료가 있나요?",
            "65세 이상이면 서울대공원 동물원 입장료가 면제되나요?",
            "서울시 도시공원의 이용료 면제 대상은 누구인가요?",
        ],
    ),
]

STOPWORDS = {
    "서울시", "서울특별시", "조례", "질문", "답변", "관련", "경우", "사람", "따라",
    "있습니다", "합니다", "됩니다", "대한", "해당", "그리고", "하지만", "다만",
    "얼마인가요", "되나요", "있나요", "무엇인가요", "어떻게", "누구인가요",
}

TOPIC_QUESTIONS = {
    "smoking": [
        "서울시 금연구역은 어디에 지정되나요?",
        "금연구역에서 담배를 피우면 과태료가 얼마인가요?",
        "금연구역 안에 흡연구역을 설치할 수 있나요?",
    ],
    "parking": [
        "공영주차장에 경차를 세우면 할인되나요?",
        "주차요금 감면 사유가 여러 개면 중복 적용되나요?",
        "서울시 공영주차장 급지별 요금은 얼마인가요?",
    ],
    "youth": [
        "서울시 청년은 몇 살까지인가요?",
        "서울시 청년시설 입주 대상은 누구인가요?",
        "의무복무 제대군인은 청년 연령을 연장받을 수 있나요?",
    ],
    "animal": [
        "유기견 입양 시 동물등록 수수료가 감면되나요?",
        "동물등록 수수료 감면 대상은 누구인가요?",
        "서울시 동물보호 조례의 지원 내용은 무엇인가요?",
    ],
    "bicycle": [
        "서울시 자전거주차장은 무료인가요?",
        "자전거주차장 요금을 받는 경우 얼마인가요?",
        "서울시는 자전거 이용을 어떻게 지원하나요?",
    ],
    "park": [
        "어린이공원에서 술을 마시면 과태료가 있나요?",
        "65세 이상이면 서울대공원 동물원 입장료가 면제되나요?",
        "도시공원 이용료 면제 대상은 누구인가요?",
    ],
}


def clarification(question):
    normalized = re.sub(r"[?!.,]", "", question).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    for pattern, message, options in CLARIFICATION_RULES:
        if pattern.fullmatch(normalized):
            return {"message": message, "options": options}
    return None


def _topic(question, used):
    text = question + " " + " ".join(h.get("law", "") + " " + h.get("label", "") for h in used)
    if re.search(r"금연|흡연|담배", text):
        return "smoking"
    if re.search(r"주차", text):
        return "parking"
    if re.search(r"청년", text):
        return "youth"
    if re.search(r"동물보호|동물등록|유기견|반려동물|강아지|고양이", text):
        return "animal"
    if re.search(r"자전거", text):
        return "bicycle"
    if re.search(r"도시공원|어린이공원|서울대공원|동물원", text):
        return "park"
    return ""


def _checklist(topic, question):
    if topic == "parking":
        if re.search(r"경차|경형", question):
            return [
                "차량이 자동차등록상 경형자동차인지 확인",
                "지하철 환승주차장 이용 및 환승 목적 여부 확인",
                "다른 감면 사유가 함께 있으면 높은 감면율 하나가 적용되는지 확인",
            ]
        return [
            "이용할 주차장이 노상·노외 중 어디인지 확인",
            "주차장의 급지와 이용 시간 또는 정기권 종류 확인",
            "감면 대상이면 현장에서 요구하는 확인 자료 점검",
        ]
    if topic == "smoking":
        return [
            "해당 장소가 지정 금연구역인지 현장 표지나 공식 공고로 확인",
            "질문이 과태료·지정 기준·흡연구역 설치 중 어느 쟁점인지 확인",
            "단속·이의제기 등 행정 절차는 담당 기관의 최신 공식 안내 확인",
        ]
    if topic == "youth":
        return [
            "질문한 사업이나 정책에 별도 연령 기준이 있는지 확인",
            "신청일을 기준으로 본인의 연령을 확인",
            "의무복무 제대군인 연령 연장 규정에 해당하는지 확인",
        ]
    if topic == "animal":
        return [
            "입양·기증받은 동물이 조례상 감면 대상인지 확인",
            "등록수수료와 등록대행 수수료를 구분해 확인",
            "등록 방법·기한은 담당 기관의 최신 공식 안내 확인",
        ]
    if topic == "bicycle":
        return [
            "해당 자전거주차장이 무료 원칙의 적용 대상인지 확인",
            "민간 위탁 등 요금 부과 예외에 해당하는지 확인",
            "시간·일·월 중 실제 이용 유형과 현장 안내판 확인",
        ]
    if topic == "park":
        if re.search(r"술|음주|금주", question):
            return [
                "해당 공원이 실제 금주구역으로 지정됐는지 현장 표지·공고 확인",
                "질문한 장소가 어린이공원 등 조례 적용 대상인지 확인",
                "단속·과태료 절차는 담당 기관의 최신 공식 안내 확인",
            ]
        return [
            "이용할 시설과 적용되는 입장료·이용료 종류 확인",
            "나이·자격 등 면제 요건을 확인할 자료 준비",
            "현장 운영 조건은 공식 안내에서 최종 확인",
        ]
    return []


KEY_PHRASES = [
    "경형자동차", "저공해자동차", "환승주차장", "주차요금", "감면율", "중복",
    "금연구역", "흡연구역", "과태료", "담배", "흡연",
    "동물등록", "등록수수료", "등록대행 수수료", "유기동물", "유기견",
    "청년", "연령", "의무복무", "제대군인", "입주 대상자",
    "자전거주차장", "주차요금표", "월정기권",
    "금주구역", "어린이공원", "입장료", "이용료", "면제",
]


def _keywords(question, answer):
    source = question + " " + answer
    phrases = [phrase for phrase in KEY_PHRASES if phrase in source]
    numbers = re.findall(r"100분의\s*\d+|\d+(?:,\d{3})*(?:\.\d+)?(?:원|세|시간|분|일|년|%)", source)
    question_terms = re.findall(r"[가-힣A-Za-z]{2,}", question)
    unique = []
    for token in sorted(phrases + numbers + question_terms, key=len, reverse=True):
        if token in STOPWORDS or token in unique:
            continue
        unique.append(token)
    return unique[:14]


def _excerpt(text, question, answer, max_chars=900):
    body = re.sub(r"^\[[^\]]+\]\s*", "", (text or "").strip())
    if not body:
        return "", [], False

    segments = [s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+", body) if s.strip()]
    terms = _keywords(question, answer)
    scored = []
    for index, segment in enumerate(segments):
        score = sum((4 if any(ch.isdigit() for ch in term) or len(term) >= 5 else 2)
                    for term in terms if term in segment)
        scored.append((score, index, segment))

    max_score = max((item[0] for item in scored), default=0)
    threshold = max(3, int(max_score * 0.6))
    matches = sorted(
        (item for item in scored if item[0] >= threshold),
        key=lambda item: (-item[0], item[1]),
    )[:2]
    if matches:
        chosen = sorted(matches, key=lambda item: item[1])
        excerpt = "\n…\n".join(dict.fromkeys(item[2] for item in chosen))
    else:
        excerpt = body

    truncated = len(excerpt) > max_chars or (excerpt != body and len(segments) > len(matches))
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "…"

    highlights = [term for term in terms if term in excerpt][:8]
    return excerpt, highlights, truncated


def _evidence(used, question, answer):
    items = []
    seen = set()
    for hit in used:
        label = hit["label"]
        if label in seen:
            continue
        seen.add(label)
        excerpt, highlights, truncated = _excerpt(hit.get("text", ""), question, answer)
        items.append({
            "citation": label,
            "law": hit.get("law", ""),
            "excerpt": excerpt,
            "highlights": highlights,
            "is_truncated": truncated,
            "source_url": hit.get("source_url", ""),
            "effective_date": hit.get("effective_date", ""),
        })
    return items


def _related_questions(topic, question):
    questions = TOPIC_QUESTIONS.get(topic, [])
    compact = re.sub(r"\s+", "", question)
    return [q for q in questions if re.sub(r"\s+", "", q) != compact][:3]


def answer(question):
    question = question.strip()
    clarify = clarification(question)
    if clarify:
        return {
            **dict(rag.UNKNOWN),
            "answer": clarify["message"],
            "needs_clarification": True,
            "clarification_options": clarify["options"],
            "verification_status": "clarification",
            "unknown_reason": "ambiguous_question",
            "evidence": [],
            "checklist": [],
            "follow_up_questions": [],
            "searched_laws": [],
        }

    detail = rag.answer_detailed(question)
    response = detail["response"]
    used = detail["used"]
    topic = _topic(question, used)
    is_unknown = response["answer"].startswith("확인 불가")
    evidence = [] if is_unknown else _evidence(used, question, response["answer"])

    return {
        **response,
        "needs_clarification": False,
        "clarification_options": [],
        "verification_status": detail["verification_status"],
        "unknown_reason": detail["unknown_reason"],
        "evidence": evidence,
        "checklist": [] if is_unknown else _checklist(topic, question),
        "follow_up_questions": _related_questions(topic, question),
        "searched_laws": list(dict.fromkeys(item["law"] for item in evidence if item["law"])),
    }
