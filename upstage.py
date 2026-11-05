"""Upstage API 호출을 한곳에 모았습니다. (Chat · Embedding · Document Parse · Groundedness Check)

Solar는 OpenAI SDK와 호환됩니다. base_url만 https://api.upstage.ai/v1 로 바꾸면 됩니다.
"""
import json
import time

import requests

import config

_client = None


def client():
    global _client
    if _client is None:
        if not config.UPSTAGE_API_KEY:
            # SystemExit이 아니라 일반 예외로: 서버(app.py)가 잡아서 '확인 불가'로 응답할 수 있게
            raise RuntimeError("UPSTAGE_API_KEY가 없습니다. .env.example을 .env로 복사하고 키를 넣어 주세요.")
        from openai import OpenAI
        _client = OpenAI(api_key=config.UPSTAGE_API_KEY, base_url=config.UPSTAGE_BASE_URL)
    return _client


def _retry(fn, tries=4):
    """429(too_many_requests)는 잠시 기다렸다 다시 부릅니다. 한도는 Organization 단위로 공유됩니다."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if "429" in str(e) and i < tries - 1:
                time.sleep(2 ** i)
                continue
            raise


def chat(messages, response_format=None, temperature=0.0, reasoning_effort=None):
    kw = dict(model=config.CHAT_MODEL, messages=messages, temperature=temperature)
    if response_format:
        kw["response_format"] = response_format
    if reasoning_effort:                      # solar-pro4: 생략하면 추론 OFF, "low" 이상이면 ON
        kw["reasoning_effort"] = reasoning_effort
    resp = _retry(lambda: client().chat.completions.create(**kw))
    return resp.choices[0].message.content


def embed(texts, model):
    out = []
    for i in range(0, len(texts), 50):        # 한 번에 너무 많이 보내지 않습니다
        batch = texts[i:i + 50]
        resp = _retry(lambda: client().embeddings.create(model=model, input=batch))
        out.extend(d.embedding for d in resp.data)
    return out


def document_parse(path):
    """Document Parse: 문서를 구조가 살아 있는 HTML/Markdown으로 바꿉니다. 표가 표로 남습니다."""
    url = f"{config.UPSTAGE_BASE_URL}/document-digitization"
    headers = {"Authorization": f"Bearer {config.UPSTAGE_API_KEY}"}
    with open(path, "rb") as f:
        resp = requests.post(url, headers=headers, timeout=300,
                             files={"document": f},
                             data={"model": "document-parse",
                                   "output_formats": json.dumps(["html", "markdown"])})
    resp.raise_for_status()
    content = resp.json().get("content", {})
    return content.get("markdown") or content.get("html") or content.get("text") or ""


_GROUND_SYSTEM = """너는 사실 검증기다. [근거]에 적힌 내용만으로 [답변]의 핵심 주장이 뒷받침되는지 판정한다.
판정 기준:
- grounded: 답변의 핵심 사실(금액·비율·나이·대상·요건·가부)이 근거에서 확인된다.
  표현이 다르거나, 일반적 배경 설명·주의문구가 덧붙어도 핵심이 근거와 일치하면 grounded로 본다.
  "~는 규정이 없다 / 중복되지 않는다"처럼 근거에 해당 내용이 없음을 근거로 한 서술도,
  제시된 근거가 그 쟁점을 다루는 조항이면 grounded로 본다.
- notGrounded: 답변의 핵심 사실이 근거와 명백히 어긋난다(틀린 숫자·반대 결론 등).
- notSure: 근거가 질문의 쟁점과 무관해 참/거짓을 가릴 수 없다.
의심스러우면 notGrounded보다 notSure를 택한다.
반드시 grounded, notGrounded, notSure 중 하나의 단어만 출력한다."""

_GROUND_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "groundedness",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["grounded", "notGrounded", "notSure"]},
            },
            "required": ["verdict"],
            "additionalProperties": False,
        },
    },
}


def groundedness(context, answer):
    """답변이 근거(context)에 실제로 기반하는지 Solar Chat으로 판정합니다.

    과거 전용 모델 'groundedness-check'는 2026-08-12로 API 서빙이 종료되어,
    현행 Chat 모델(solar-pro4)에 판정 프롬프트를 주는 LLM 기반 검증으로 대체합니다.
    반환값은 기존과 동일: grounded / notGrounded / notSure
    """
    raw = chat(
        [{"role": "system", "content": _GROUND_SYSTEM},
         {"role": "user", "content": f"[근거]\n{context}\n\n[답변]\n{answer}"}],
        response_format=_GROUND_SCHEMA)
    try:
        return json.loads(raw).get("verdict", "notSure")
    except (json.JSONDecodeError, TypeError):
        # 형식이 깨져도 서버가 죽지 않도록 안전하게 보류 처리
        return "notSure"
