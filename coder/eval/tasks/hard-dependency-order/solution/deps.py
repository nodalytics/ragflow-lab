import heapq


class CycleError(Exception):
    def __init__(self, cycle):
        super().__init__(" -> ".join(cycle))
        self.cycle = cycle


def _find_cycle(deps):
    state, stack = {}, []

    def visit(u):
        state[u] = 1
        stack.append(u)
        for v in sorted(deps.get(u, [])):
            if state.get(v) == 1:
                cyc = stack[stack.index(v):]
                i = cyc.index(min(cyc))
                cyc = cyc[i:] + cyc[:i]
                return cyc + [cyc[0]]
            if not state.get(v):
                found = visit(v)
                if found:
                    return found
        stack.pop()
        state[u] = 2
        return None

    for u in sorted(deps):
        if not state.get(u):
            found = visit(u)
            if found:
                return found
    return None


def order(deps):
    nodes = set(deps) | {d for ds in deps.values() for d in ds}
    need = {n: set(deps.get(n, [])) for n in nodes}
    users = {n: set() for n in nodes}
    for n, ds in need.items():
        for d in ds:
            users[d].add(n)
    ready = [n for n in nodes if not need[n]]
    heapq.heapify(ready)
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for u in users[n]:
            need[u].discard(n)
            if not need[u]:
                heapq.heappush(ready, u)
    if len(out) != len(nodes):
        raise CycleError(_find_cycle(deps))
    return out
