import argparse, json, sys

def counts(text):
    return len(text.splitlines()), len(text.split()), len(text)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    text = open(a.file).read()
    lines, words, chars = counts(text)
    if a.json:
        print(json.dumps({"lines": lines, "words": words, "chars": chars}))
    else:
        print(f"{lines} {words} {chars} {a.file}")

if __name__ == "__main__":
    sys.exit(main())
