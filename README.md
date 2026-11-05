# 서울시 조례 Q&A — 공공 법령 Q&A AI 경진대회

서울특별시 조례 6종을 대상으로, 사용자의 자연어 질문에 **실제 조문을 근거로** 답하고
조·항 단위 인용·원문 링크·시행일을 함께 제공하는 RAG 기반 Q&A API입니다.

공식 스타터 킷(baseline)을 기반으로 대회 채점 규격에 맞게 수정했습니다.

```
법제처 OPEN API ─▶ 조·항 단위 조각 ─▶ 검색(임베딩+키워드) ─▶ Solar 답변 ─▶ 검증 ─▶ 대회 JSON
       │                 ▲
       └─ 별표(요금표) ─▶ Document Parse
```

## 대회 규격 요약

- **대상**: 서울특별시 조례 6종(주차장·동물보호·자전거·도시공원·청년·금연), **2026-10-01 시행본**. 자치구(OO구) 조례 인용은 오답.
- **엔드포인트**: `POST /ask`, 요청 `{"question": "..."}`
- **응답 JSON 4필드**: `answer`, `citation`, `source_url`, `effective_date`
- **근거 없음**: `{"answer": "확인 불가", "citation": [], "source_url": "", "effective_date": ""}`
- **제약**: 문항당 90초 이내, 항상 유효 JSON (서버 오류·형식 깨짐 시 0점)

## 빠른 시작 (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# .env 에 키 입력 (.env.example 참고)
#   UPSTAGE_API_KEY=up-...
#   LAW_OC=본인OC            # open.law.go.kr 신청, 미설정 시 'test'

.\.venv\Scripts\python.exe -X utf8 fetch_ordinances.py   # 1. 조례 6종 수집 → data/ordinances.json (이미 포함)
.\.venv\Scripts\python.exe -X utf8 parse_annex.py        # 2. 별표(요금표)를 Document Parse로 읽기 → data/annex/
.\.venv\Scripts\python.exe -X utf8 build_index.py        # 3. 조각 생성 + 임베딩 → data/vectors_paragraph.npy
.\.venv\Scripts\python.exe -X utf8 check.py --retrieval  # 4. 검색 점검 (키 없이도 동작)
.\.venv\Scripts\python.exe -X utf8 check.py              # 5. 로컬 전체 셀프 채점

.\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000   # 6. 제출용 API
.\.venv\Scripts\python.exe -X utf8 check.py --url http://localhost:8000/ask # (새 창) 서버 채점
```

> 한글이 깨지면 `python` 대신 `-X utf8`을 붙이세요.
> 이 저장소는 `data/ordinances.json`과 조각(chunks)을 포함합니다. 임베딩(`vectors_*.npy`)과
> 별표 파싱 결과(`data/annex/`)는 용량·재현성 때문에 제외되어 있으니 2·3단계를 실행해 생성하세요.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `fetch_ordinances.py` | 법제처 API로 조례 6종 수집, 조·항 분리, 자치구 조례 제외 |
| `parse_annex.py` | 별표(요금표)를 Upstage Document Parse로 읽어 표 구조 보존 |
| `build_index.py` | 조각마다 인용 라벨 부여 + Solar Embedding 색인 |
| `rag.py` | 검색 → Solar 답변 → **검증** → 대회 JSON 생성 |
| `upstage.py` | Upstage API (Chat / Embedding / Document Parse / 근거검증) |
| `app.py` | `POST /ask` FastAPI 서버 (90초 타임아웃·오류 방어) |
| `check.py` | 공개 예시 기반 셀프 채점 |
| `config.py` | 대상 조례·모델명·시연 스위치 |
| `connectivity_test.py` | Chat/Embedding/근거검증/법제처 API 연동 점검 (키 미노출) |

## 베이스라인 대비 변경점

1. **근거 검증 모델 교체 (필수)** — 기존 `groundedness-check` 전용 모델은 Upstage API
   서빙이 종료되어(2026-08-12) 400 오류를 반환합니다. 그대로 두면 `USE_VERIFY=1`에서 모든
   답변이 '확인 불가'로 떨어져 **근거 정확도 0점**이 됩니다. 이를 **현행 Solar Chat(solar-pro4)에
   판정 프롬프트를 주는 LLM 기반 검증**으로 교체했습니다(`upstage.py: groundedness`).
   반환값(grounded / notGrounded / notSure)과 호출부(`rag.py`)는 그대로 호환됩니다.
2. **연동 점검 스크립트 추가** — `connectivity_test.py`로 Chat·Embedding·근거검증·법제처
   API 4종을 한 번에 점검(키 값은 출력하지 않음).

## 설계 원칙 (점수와 직결)

1. **LLM은 근거 번호(`evidence_ids`)만 고른다.** `citation` 문자열은 코드가 조각 라벨로
   생성 → 조항 표기 실수·환각 차단.
2. **`source_url`·`effective_date`는 코드가 채운다.** 시행 버전 고정 법제처 링크 + API 시행일.
3. **의심스러우면 '확인 불가'.** 검색 점수가 `MIN_SCORE` 미만이거나 검증이 `notGrounded`면
   답하지 않는다.

## 모델

- Chat: `solar-pro4`
- Embedding: `solar-embedding-2-query`(질문) / `solar-embedding-2-passage`(조문)
- 근거검증: `solar-pro4` 기반 LLM 판정
- 문서파싱: `document-parse`

## 보안

- `UPSTAGE_API_KEY`·`LAW_OC`는 `.env`에만 두며 `.gitignore`로 커밋 제외.
- 키를 화면·로그·채팅에 노출하지 말 것. 노출 시 즉시 재발급(rotate).

## 한계

- 조문이 많은 대형 법령은 응답이 느려질 수 있음(90초 제한 주의).
- 근거검증은 전용 API가 아닌 Solar Chat 기반 판정이라 완벽하지 않음.
- 법률 자문이 아닌 **법령 정보 안내**이며 법적 효력이 없음.
