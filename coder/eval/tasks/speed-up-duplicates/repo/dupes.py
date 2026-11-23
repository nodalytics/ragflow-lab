def find_duplicates(items):
    """The values that appear more than once, in the order their second occurrence appears."""
    out = []
    for i, x in enumerate(items):
        if x in items[:i] and x not in out:
            out.append(x)
    return out
