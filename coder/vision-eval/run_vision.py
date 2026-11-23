"""Compare vision models on items.json (make_media.py): describe each image, or a video's frames, and grade the text.

Each item's score is the share of its facts the description states (a regex per fact), averaged with how exactly it
transcribes the item's text lines when there are any (the best match per line, difflib ratio). Hallucinations (things
not in the picture) are counted separately. Every description is saved, so the grading can be read and checked.

  python3 run_vision.py --models qwen3-vl:8b,gemma4:e4b --base-url http://127.0.0.1:11436 --out results/run.json

Models are called through Ollama's /api/chat (images as base64), one at a time, loaded before their items.
"""

import argparse
import base64
import difflib
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORY = {"invoice": "text", "code-screenshot": "text", "table": "text", "bar-chart": "text", "count-shapes": "counting",
            "video": "video"}  # fmt: skip


def post(base, path, body, timeout=900):
    r = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def ocr_score(text, lines):
    got = [re.sub(r"^[\s>*`#|-]+|[\s`|]+$", "", x) for x in text.splitlines()]
    got = [x for x in got if x]
    return sum(max((difflib.SequenceMatcher(None, want.strip(), g).ratio() for g in got), default=0) for want in lines) / len(lines)


def grade(item, text):
    t = text.lower()
    hits = [name for name, rx in item["facts"] if re.search(rx, t, re.S)]
    facts = len(hits) / len(item["facts"])
    ocr = ocr_score(text, item["ocr"]) if item["ocr"] else None
    hall = [name for name, rx in item["hallucinations"] if re.search(rx, t, re.S)]
    score = facts if ocr is None else (facts + ocr) / 2
    return {"score": round(score, 3), "facts": round(facts, 3), "ocr": None if ocr is None else round(ocr, 3),
            "missed": [n for n, _ in item["facts"] if n not in hits], "hallucinations": hall}  # fmt: skip


def describe(base, model, item, think):
    imgs = [base64.b64encode(open(os.path.join(HERE, "media", f), "rb").read()).decode() for f in item["files"]]
    body = {"model": model, "stream": False, "messages": [{"role": "user", "content": item["prompt"], "images": imgs}],
            "options": {"temperature": 0.2, "seed": 7, "num_predict": 6000}}  # fmt: skip
    if think is not None:
        body["think"] = think
    t = time.time()
    r = post(base, "/api/chat", body)
    secs = time.time() - t
    tps = r.get("eval_count", 0) / (r.get("eval_duration", 1) / 1e9)
    # some models think even when asked not to (qwen3-vl:4b): the budget covers the thinking, and a cut-off answer
    # (done_reason "length") is recorded
    return r["message"]["content"], secs, tps, r.get("done_reason"), len((r["message"].get("thinking") or "").split())


def load(base, model):
    t = time.time()
    post(base, "/api/generate", {"model": model, "keep_alive": -1})
    ps = json.load(urllib.request.urlopen(base + "/api/ps", timeout=30))
    m = [x for x in ps.get("models", []) if x["name"] == model]
    return time.time() - t, ((round(m[0]["size_vram"] / 1e9, 1), round(m[0]["size"] / 1e9, 1)) if m else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    ap.add_argument("--regrade", action="store_true", help="grade the saved descriptions in --out again (after a grader fix)")
    ap.add_argument("--base-url", default="http://127.0.0.1:11436")
    ap.add_argument("--out", required=True)
    ap.add_argument("--think", choices=["off", "default"], default="off",
                    help="off: ask thinking models to answer directly (as a captioning service would)")
    a = ap.parse_args()
    items = json.load(open(os.path.join(HERE, "items.json")))
    if a.regrade:
        out = json.load(open(a.out))
        byid = {i["id"]: i for i in items}
        for v in out["models"].values():
            for r in v["results"]:
                r.update(grade(byid[r["item"]], r["text"]))
            cats = {}
            for r in v["results"]:
                cats.setdefault(r["category"], []).append(r["score"])
            v["score"] = round(sum(r["score"] for r in v["results"]) / len(v["results"]), 3)
            v["by_category"] = {k: round(sum(x) / len(x), 3) for k, x in cats.items()}
            v["hallucinations"] = sum(len(r["hallucinations"]) for r in v["results"])
        json.dump(out, open(a.out, "w"), indent=1)
        a.models = ""
    out = json.load(open(a.out)) if os.path.exists(a.out) else {"items": [i["id"] for i in items], "models": {}}
    for model in [m for m in a.models.split(",") if m]:
        secs, vram = load(a.base_url, model)
        print(f"== {model}: loaded in {secs:.0f}s, GPU/total GB {vram}", flush=True)
        res = []
        for it in items:
            think = False if a.think == "off" else None
            err = None
            try:
                text, s, tps, why, thought = describe(a.base_url, model, it, think)
            except Exception as e:  # a model without a think switch refuses the field: ask again without it
                try:
                    text, s, tps, why, thought = describe(a.base_url, model, it, None)
                except Exception as e2:  # the model cannot do this item at all (moondream: several images)
                    text, s, tps, why, thought, err = "", 0.0, 0, "error", 0, str(e2)[:120]
            g = grade(it, text)
            res.append({"item": it["id"], "category": CATEGORY.get(it["id"], "photo"), **g, "seconds": round(s, 1),
                        "tok_per_s": round(tps), "words": len(text.split()), "done_reason": why, "thinking_words": thought,
                        "error": err, "text": text})  # fmt: skip
            print(f"  {it['id']:16} {g['score']:.2f}  facts {g['facts']:.2f}" + (f" ocr {g['ocr']:.2f}" if g["ocr"] is not None else "")
                  + (f"  HALLUCINATED {g['hallucinations']}" if g["hallucinations"] else "") + f"  {s:.0f}s"
                  + (f"  [{why}]" if why != "stop" else "") + (f" {err}" if err else ""), flush=True)  # fmt: skip
        cats = {}
        for r in res:
            cats.setdefault(r["category"], []).append(r["score"])
        out["models"][model] = {"vram_gb": vram, "load_seconds": round(secs, 1), "results": res,
                                "score": round(sum(r["score"] for r in res) / len(res), 3),
                                "by_category": {k: round(sum(v) / len(v), 3) for k, v in cats.items()},
                                "hallucinations": sum(len(r["hallucinations"]) for r in res),
                                "median_seconds": sorted(r["seconds"] for r in res)[len(res) // 2]}  # fmt: skip
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(out, open(a.out, "w"), indent=1)
    print("\nmodel                        score   text  count  video  photo  halluc  median s   GB")
    for m, v in out["models"].items():
        c = v["by_category"]
        print(f"{m:28} {v['score']:5.2f}  {c.get('text', 0):5.2f}  {c.get('counting', 0):5.2f}  {c.get('video', 0):5.2f}"
              f"  {c.get('photo', 0):5.2f}  {v['hallucinations']:6}  {v['median_seconds']:8.1f}  {v['vram_gb']}")  # fmt: skip


if __name__ == "__main__":
    main()
