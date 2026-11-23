import json, pathlib, subprocess, sys
WC = pathlib.Path(__file__).resolve().parent.parent / "wc.py"

def run(*args, tmp):
    f = tmp / "t.txt"
    f.write_text("hello world\nsecond line here\n")
    return subprocess.run([sys.executable, str(WC), *args, str(f)], capture_output=True, text=True, check=True).stdout, f

def test_plain_unchanged(tmp_path):
    out, f = run(tmp=tmp_path)
    assert out == f"2 5 29 {f}\n"

def test_json(tmp_path):
    out, _ = run("--json", tmp=tmp_path)
    assert json.loads(out) == {"lines": 2, "words": 5, "chars": 29}
