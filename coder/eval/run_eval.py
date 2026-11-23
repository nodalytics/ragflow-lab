"""Compare coding models on the tasks in tasks/ (make_tasks.py), through opencode, graded by hidden tests.

For each model, task and repetition: the task's repo is copied to a fresh git repository, opencode runs the task's
prompt there non-interactively (`opencode run -m ...`), and only then are the hidden tests copied in and run. A task
passes when every hidden test passes; the agent's own claims are never read.

  python3 run_eval.py --validate                      the hidden tests fail on each starting repo and pass on its
                                                      reference solution (run this first: it proves the grading)
  python3 run_eval.py --models qwen3.8:27b,devstral-small-2:24b --reps 2 --out results/run.json

The models are served by the lab's Ollama (coder/coder.sh), reached at --base-url (default http://127.0.0.1:11435,
the ssh tunnel: ../../lab.sh tunnel). Each model is loaded before its tasks, so a model swap is not timed.
opencode uses its own config for this (OPENCODE_CONFIG), so the user's config is not touched.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")


def tasks(only=None):
    names = sorted(os.listdir(TASKS))
    return [n for n in names if not only or n in only]


def grade(repo, task):
    """Copy the hidden tests into repo/hidden_tests and run them; returns (passed, failed)."""
    dst = os.path.join(repo, "hidden_tests")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(TASKS, task, "hidden"), dst)
    env = {**os.environ, "PYTHONPATH": repo, "PYTHONDONTWRITEBYTECODE": "1"}
    try:  # a slow solution (or a hang) is a fail, not a stuck grader
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "hidden_tests"],
                           cwd=repo, env=env, capture_output=True, text=True, timeout=120)  # fmt: skip
    except subprocess.TimeoutExpired:
        return 0, 1, "grading timed out after 120 s"
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    p = sum(int(w) for w, nxt in zip(tail.split(), tail.split()[1:]) if w.isdigit() and nxt.startswith("passed"))
    f = sum(int(w) for w, nxt in zip(tail.split(), tail.split()[1:]) if w.isdigit() and nxt.startswith(("failed", "error")))
    return p, f, tail


def fresh(task, overlay=None):
    d = tempfile.mkdtemp(prefix=f"eval-{task}-")
    shutil.copytree(os.path.join(TASKS, task, "repo"), d, dirs_exist_ok=True)
    if overlay:
        shutil.copytree(os.path.join(TASKS, task, overlay), d, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q", d], check=True)
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.name=eval", "-c", "user.email=eval@local", "commit", "-qm", "start"],
                   check=True)  # fmt: skip
    return d


def validate(only=None):
    ok = True
    for t in tasks(only):
        d0 = fresh(t)
        p0, f0, _ = grade(d0, t)
        d1 = fresh(t, "solution")
        p1, f1, tail1 = grade(d1, t)
        good = f0 > 0 and f1 == 0 and p1 > 0
        ok &= good
        print(f"{'ok ' if good else 'BAD'} {t}: start {p0} passed {f0} failed; solution {p1} passed {f1} failed"
              + ("" if good else f"  ({tail1})"), flush=True)  # fmt: skip
        shutil.rmtree(d0)
        shutil.rmtree(d1)
    print("all tasks valid" if ok else "SOME TASKS ARE INVALID")
    return ok


def opencode_config(base, models):
    m = {name: {"name": name, "tool_call": True, "limit": {"context": 98304, "output": 16384}} for name in models}
    cfg = {"$schema": "https://opencode.ai/config.json",
           "provider": {"evallab": {"npm": "@ai-sdk/openai-compatible", "name": "Eval lab",
                                     "options": {"baseURL": base + "/v1", "apiKey": "unused"}, "models": m}}}  # fmt: skip
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(cfg, f)
    f.close()
    return f.name


def load(base, model):
    body = json.dumps({"model": model, "keep_alive": -1}).encode()
    t = time.time()
    urllib.request.urlopen(urllib.request.Request(base + "/api/generate", body), timeout=900).read()
    ps = json.load(urllib.request.urlopen(base + "/api/ps", timeout=30))
    m = [x for x in ps.get("models", []) if x["name"] == model]
    gpu = round(m[0]["size_vram"] / m[0]["size"], 3) if m else None
    return time.time() - t, gpu


def reachable(base, wait=600):
    """Wait until the model server answers (an ssh tunnel can drop and come back); False after `wait` seconds."""
    t = time.time()
    while time.time() - t < wait:
        try:
            urllib.request.urlopen(base + "/api/tags", timeout=10).read()
            return True
        except Exception:
            time.sleep(15)
    return False


def run(args):
    models = args.models.split(",")
    cfg = opencode_config(args.base_url, models)
    out = {"models": models, "reps": args.reps, "tasks": tasks(args.tasks), "runs": [], "load": {}}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    logs = os.path.splitext(args.out)[0] + "_logs"
    os.makedirs(logs, exist_ok=True)
    for model in models:
        secs, gpu = load(args.base_url, model)
        out["load"][model] = {"seconds": round(secs, 1), "on_gpu": gpu}
        print(f"== {model}: loaded in {secs:.0f}s, {gpu:.0%} on the GPU", flush=True)
        for rep in range(args.reps):
            for t in out["tasks"]:
                prompt = open(os.path.join(TASKS, t, "prompt.txt")).read().strip()
                env = {**os.environ, "OPENCODE_CONFIG": cfg}
                for attempt in range(3):  # a run that never reached the server is infrastructure, not the model: rerun it
                    if not reachable(args.base_url):
                        sys.exit(f"the model server at {args.base_url} is unreachable; stopping (results so far are saved)")
                    d = fresh(t)
                    start = time.time()
                    try:
                        r = subprocess.run(["opencode", "run", "-m", f"evallab/{model}", prompt], cwd=d, env=env,
                                           capture_output=True, text=True, timeout=args.timeout)  # fmt: skip
                        log, timed_out = r.stdout + r.stderr, False
                    except subprocess.TimeoutExpired as e:
                        log, timed_out = (e.stdout or b"").decode(errors="replace") + "\n[TIMEOUT]", True
                    secs = time.time() - start
                    if "Unable to connect" not in log:
                        break
                    print(f"  {t:22} rep {rep}: lost the connection, rerunning", flush=True)
                    shutil.rmtree(d, ignore_errors=True)
                p, f, tail = grade(d, t)
                passed = f == 0 and p > 0
                out["runs"].append({"model": model, "task": t, "rep": rep, "pass": passed, "tests_passed": p,
                                    "tests_failed": f, "seconds": round(secs, 1), "timed_out": timed_out})  # fmt: skip
                with open(os.path.join(logs, f"{model.replace(':', '_').replace('/', '_')}-{t}-{rep}.log"), "w") as fh:
                    fh.write(log)
                print(f"  {t:22} rep {rep}: {'PASS' if passed else 'fail'} ({p} passed, {f} failed) {secs:.0f}s"
                      + (" TIMEOUT" if timed_out else ""), flush=True)  # fmt: skip
                shutil.rmtree(d, ignore_errors=True)
                json.dump(out, open(args.out, "w"), indent=1)
    summary(out)
    json.dump(out, open(args.out, "w"), indent=1)
    os.unlink(cfg)


def summary(out):
    print("\nmodel                      tasks passed     tests passed   median seconds")
    for model in out["models"]:
        rs = [r for r in out["runs"] if r["model"] == model]
        if not rs:
            continue
        tp = sum(r["tests_passed"] for r in rs)
        tt = tp + sum(r["tests_failed"] for r in rs)
        secs = sorted(r["seconds"] for r in rs)
        print(f"{model:26} {sum(r['pass'] for r in rs):3}/{len(rs):<3} ({sum(r['pass'] for r in rs) / len(rs):4.0%})"
              f"   {tp:4}/{tt:<4}      {secs[len(secs) // 2]:6.0f}")  # fmt: skip


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--models", default="qwen3.8:27b")
    ap.add_argument("--tasks", default="", help="comma-separated task names (default: all)")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600, help="seconds an agent gets per task")
    ap.add_argument("--base-url", default="http://127.0.0.1:11435")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "run.json"))
    a = ap.parse_args()
    a.tasks = [t for t in a.tasks.split(",") if t]
    if a.validate:
        sys.exit(0 if validate(a.tasks) else 1)
    run(a)
