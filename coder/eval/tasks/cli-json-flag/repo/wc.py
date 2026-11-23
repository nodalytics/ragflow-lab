import argparse, sys

def counts(text):
    return len(text.splitlines()), len(text.split()), len(text)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    a = ap.parse_args(argv)
    text = open(a.file).read()
    lines, words, chars = counts(text)
    print(f"{lines} {words} {chars} {a.file}")

if __name__ == "__main__":
    sys.exit(main())
