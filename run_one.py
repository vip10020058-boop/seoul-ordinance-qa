"""질문을 인덱스 범위로 나눠 채점하고 결과를 UTF-8 JSON으로 저장.

사용:  python -X utf8 run_one.py 0 2     # sample_questions[0:2] 채점
각 호출이 짧게 끝나도록 소량씩 처리합니다. 결과는 part_<start>_<end>.json에 저장.
"""
import json
import re
import sys
import time

import config
import rag

CITE = re.compile(r"(서울특별시.*?(?:조례|규칙))\s*(제\d+조(?:의\d+)?|별표\s*\d*|별도\s*\d+)\s*(제\d+항)?")


def parse(c):
    m = CITE.search(c)
    if not m:
        return None
    return re.sub(r"\s+", "", m.group(1)), re.sub(r"\s+", "", m.group(2)), m.group(3)


def match(pred, gold):
    p, g = parse(pred), parse(gold)
    if not p or not g or p[0] != g[0] or p[1] != g[1]:
        return 0.0
    if g[2] is None or p[2] == g[2]:
        return 1.0
    return 0.5


def score_citation(preds, gold):
    if not gold:
        return None
    total = 0.0
    for alts in gold:
        total += max((match(p, a) for p in preds for a in alts), default=0.0)
    return total / len(gold)


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else start + 1
    qs = json.loads(open(config.ROOT / "sample_questions.json", encoding="utf-8").read())[start:end]
    rows = []
    for q in qs:
        t0 = time.time()
        try:
            r = rag.answer(q["question"])
            err = None
        except Exception as e:  # noqa: BLE001
            r, err = {}, repr(e)
        sec = round(time.time() - t0, 1)
        unknown = r.get("answer", "").startswith("확인 불가") and r.get("citation") == []
        if q["gold"]:
            sc = 0.0 if err or sec > 90 else score_citation(r.get("citation", []), q["gold"])
        else:
            sc = 1.0 if unknown and not err and sec <= 90 else 0.0
        fmt_ok = unknown or (r.get("source_url", "").startswith("http") and
                             bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("effective_date", ""))))
        rows.append({"id": q["id"], "type": q["type"], "score": sc, "sec": sec,
                     "format_ok": bool(fmt_ok), "error": err,
                     "citation": r.get("citation"), "answer": r.get("answer", "")[:120]})
    out = config.ROOT / f"part_{start}_{end}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out)


if __name__ == "__main__":
    main()
