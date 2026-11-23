import re


class PatchError(Exception):
    pass


HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _hunks(patch):
    hunks, cur = [], None
    for ln in patch.splitlines(keepends=True):
        if ln.startswith(("--- ", "+++ ")) and cur is None:
            continue
        m = HUNK.match(ln)
        if m:
            cur = {"a": int(m.group(1)), "b": int(m.group(2) or 1), "lines": []}
            hunks.append(cur)
        elif cur is not None and ln[:1] in (" ", "-", "+"):
            body = ln[1:]
            cur["lines"].append((ln[0], body if body.endswith("\n") else body + "\n"))
    return hunks


def apply_patch(text, patch):
    lines = text.splitlines(keepends=True)
    no_final = bool(lines) and not lines[-1].endswith("\n")
    if no_final:
        lines[-1] += "\n"
    offset = 0
    for h in _hunks(patch):
        old = [b for k, b in h["lines"] if k in (" ", "-")]
        new = [b for k, b in h["lines"] if k in (" ", "+")]
        start = h["a"] - 1 if h["b"] else h["a"]
        for d in [0] + [x for k in range(1, 11) for x in (-k, k)]:
            s = start + offset + d
            if 0 <= s <= len(lines) - len(old) and lines[s:s + len(old)] == old:
                lines[s:s + len(old)] = new
                offset += d + len(new) - len(old)
                break
        else:
            raise PatchError(f"hunk at line {h['a']} does not apply")
    out = "".join(lines)
    return out[:-1] if no_final and out.endswith("\n") else out
