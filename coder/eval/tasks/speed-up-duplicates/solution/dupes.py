def find_duplicates(items):
    seen, out, reported = set(), [], set()
    for x in items:
        if x in seen and x not in reported:
            out.append(x)
            reported.add(x)
        seen.add(x)
    return out
