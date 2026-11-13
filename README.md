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

## 가장 쉬운 실행 (Windows, 더블클릭)

1. 저장소를 받습니다 (Code → Download ZIP 후 압축 해제, 또는 `git clone`).
2. `.env.example`을 복사해 `.env`로 만들고 `UPSTAGE_API_KEY=` 뒤에 키를 입력합니다.
   (`.env`가 없으면 `1_서버켜기.bat`이 자동으로 만들고 메모장을 열어 줍니다.)
3. `1_서버켜기.bat` 실행 → 첫 실행 시 Python 설치(없을 때)·가상환경·패키지·임베딩 색인을
   자동으로 준비한 뒤 서버를 켭니다. `Application startup complete`가 보이면 정상입니다.
4. `2_공개주소켜기.bat` 실행 → cloudflared가 없으면 자동으로 내려받고 공개 주소를 띄웁니다.
5. (선택) `3_제출전점검.bat`으로 채점 URL 셀프 점검.

## 수동 실행 (Windows PowerShell)

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

## 최신 자체 점검 결과 (2026-11-13)

아래 수치는 팀에서 공유한 로컬 제출 전 점검 로그 기준입니다. 공개 저장소의 코드만으로 동일 환경에서 재실행한 결과는 아닙니다.

| 항목 | 측정 결과 | 해석 |
|---|---:|---|
| 단위 테스트 | 32/32 통과* | 공유받은 별도 로컬 로그 기준 |
| 검색 근거 회수율 | 15/15 = 100% | 정답 근거가 검색 Top-6에 포함된 비율이며 최종 답변 정답률은 아님 |
| 일반 API 문항 | 인용 점수 15/15 = 100% | 셀프채점기의 조·항 인용 평가 기준 |
| 함정 문항 | 2/3 = 66.7% | T3에서 확인 불가 처리 실패 |
| JSON 계약 | 18/18 = 100% | 필수 응답 형식 통과 |
| 요청 오류 | 0건 | 해당 점검 실행 구간 기준 |
| 응답 시간 | 약 0.03~5.35초 | 18문항 실행 로그 기준 |

**남은 결함 — T3 함정 문항:** 3개 함정 질문 중 1개가 확인 불가로 처리되지 않았고, 청년 기본 조례 제10조 제8항·제20조 제2항·제10조 제7항이 인용됐습니다. 질문 원문과 답변 전문을 확인하기 전에는 원인을 단정하지 않습니다. 해당 결과 JSON과 T3 API 응답 전문을 확인해 재현한 뒤 수정해야 합니다.

> **점수 해석·재현성 주의:** `check.py`의 일반 문항 점수는 조·항 인용 점수입니다. 답변 본문의 모든 사실관계를 검증하는 지표가 아닙니다. 검색 회수율 역시 최종 답변 정확도와 다릅니다. 위 결과를 “전체 답변 100% 정답”으로 표현하지 않습니다. 또한 현재 공개 저장소의 `sample_questions.json`은 11문항(T1·T2 함정 2문항)입니다. 위 18문항 점검은 별도의 로컬 문항 세트로 실행한 결과이며, 그 문항 세트와 결과 JSON은 현재 저장소에 포함되어 있지 않아 공개 저장소만으로는 동일한 18문항 검증을 재현할 수 없습니다. 32개 단위 테스트의 테스트 코드와 결과 파일도 공개 저장소에서 확인되지 않아 공개 상태로는 재현할 수 없습니다.

## 제출 전 체크리스트

- [ ] T3 함정 질문 원문·응답 전문 및 18문항 테스트 세트 저장/공유
- [ ] 외부 공개 URL에서 `GET /health`와 `POST /ask`를 각각 확인
- [ ] 제출 환경에서 API 서버와 터널 프로세스 지속 실행 확인
- [ ] Quick Tunnel 재시작 후 공개 URL 변경 여부 확인
- [ ] `.env` 및 실제 API 키가 커밋되지 않았는지 확인
- [ ] 6종 조례 전체 질문의 조·항·시행일·원문 링크 대조

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
