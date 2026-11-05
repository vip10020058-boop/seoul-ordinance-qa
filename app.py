"""5단계: 대회 제출용 API 서버.

실행:  uvicorn app:app --host 0.0.0.0 --port 8000
호출:  POST /ask  {"question": "장애인 주차요금 감면되나요?"}

채점은 운영진이 마감 직후 1회 실행합니다. 문항당 90초를 넘기거나 오류가 나면 0점입니다.
그래서 어떤 경우에도 정해진 JSON을 돌려주도록 감쌌습니다.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

import config
import rag
import ui_service

app = FastAPI(title="서울시 조례 Q&A")
log = logging.getLogger("uvicorn.error")

WEB_INDEX = config.ROOT / "web" / "index.html"


class Ask(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home():
    """시민용 질문 화면. 없으면 간단한 안내를 돌려준다."""
    if WEB_INDEX.exists():
        return FileResponse(WEB_INDEX)
    return HTMLResponse("<h1>서울시 조례 Q&A</h1><p>POST /ask 로 질문하세요.</p>")


@app.get("/health")
def health():
    return {"ok": True, "chunk_unit": config.CHUNK_UNIT, "verify": config.USE_VERIFY}


@app.post("/ask")
async def ask(req: Ask):
    try:
        return await asyncio.wait_for(asyncio.to_thread(rag.answer, req.question),
                                      timeout=config.ANSWER_TIMEOUT_SEC)
    except Exception as e:  # noqa: BLE001  시간 초과·API 오류 모두 '확인 불가'로 응답
        log.warning("ask failed: %r", e)
        return dict(rag.UNKNOWN)


@app.post("/ui/ask")
async def ui_ask(req: Ask):
    """시민용 화면 전용 응답. 대회 채점용 `/ask` 계약과 분리합니다."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(ui_service.answer, req.question),
                                      timeout=config.ANSWER_TIMEOUT_SEC)
    except Exception as e:  # noqa: BLE001
        log.warning("ui ask failed: %r", e)
        return {
            **dict(rag.UNKNOWN),
            "needs_clarification": False,
            "clarification_options": [],
            "verification_status": "unavailable",
            "unknown_reason": "server_error",
            "evidence": [],
            "checklist": [],
            "follow_up_questions": [],
            "searched_laws": [],
        }
