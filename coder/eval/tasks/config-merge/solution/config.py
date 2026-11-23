import copy

def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out

def _convert(raw, old):
    if isinstance(old, bool):
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        raise ValueError(raw)
    if isinstance(old, int):
        return int(raw)
    if isinstance(old, float):
        return float(raw)
    return raw

def load_config(defaults, file_values, env):
    c = _merge(defaults, file_values)
    for k, raw in env.items():
        if not k.startswith("APP_"):
            continue
        path = k[4:].lower().split("__")
        node = c
        for p in path[:-1]:
            node = node.setdefault(p, {})
        node[path[-1]] = _convert(raw, node.get(path[-1]))
    return c
