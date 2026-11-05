"""Upstage/법제처 연동 점검. 키 값은 출력하지 않습니다.

실행: python -X utf8 connectivity_test.py
결과는 콘솔과 conn_result.txt(UTF-8)에 함께 기록합니다.
"""
import io
import sys
import traceback

import config

lines = []


def log(msg):
    print(msg)
    lines.append(str(msg))


def check_chat():
    import upstage
    out = upstage.chat([{"role": "user", "content": "한 단어로만 답해: 대한민국 수도는?"}])
    log(f"[Chat] OK  model={config.CHAT_MODEL}  resp={out[:30]!r}")


def check_embed():
    import upstage
    v = upstage.embed(["테스트 문장"], config.EMBED_QUERY)
    log(f"[Embedding] OK  model={config.EMBED_QUERY}  dim={len(v[0])}")


def check_groundedness():
    import upstage
    verdict = upstage.groundedness("서울시 금연구역 과태료는 10만원이다.", "금연구역에서 흡연하면 10만원 과태료입니다.")
    log(f"[Groundedness] OK  verdict={verdict!r}")


def check_law_api():
    import requests
    r = requests.get("https://www.law.go.kr/DRF/lawSearch.do",
                     params=dict(OC=config.LAW_OC, target="ordin", type="XML",
                                 query="서울특별시 금연환경 조성 및 간접흡연 피해방지조례", display=5),
                     timeout=30)
    r.raise_for_status()
    ok = "서울특별시" in r.text
    log(f"[법제처 API] OK  status={r.status_code}  contains_seoul={ok}")


if __name__ == "__main__":
    for name, fn in [("Chat", check_chat), ("Embedding", check_embed),
                     ("Groundedness", check_groundedness), ("법제처 API", check_law_api)]:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log(f"[{name}] FAIL  {type(e).__name__}: {e}")
            lines.append(traceback.format_exc())
    with io.open("conn_result2.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
