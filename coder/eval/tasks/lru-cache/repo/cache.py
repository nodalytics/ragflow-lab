class LRUCache:
    """A least-recently-used cache holding at most `capacity` items (capacity >= 1, else ValueError).
    get(key) returns the value, or None if absent, and marks the key as most recently used.
    put(key, value) inserts or updates the key, marks it most recently used, and evicts the least
    recently used key when the cache is over capacity. len(cache) is the number of items."""

    def __init__(self, capacity):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def put(self, key, value):
        raise NotImplementedError
