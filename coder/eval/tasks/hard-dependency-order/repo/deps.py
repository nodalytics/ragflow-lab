class CycleError(Exception):
    def __init__(self, cycle):
        super().__init__(" -> ".join(cycle))
        self.cycle = cycle


def order(deps):
    """An install order for packages: `deps` maps each package to the packages it depends on, and every
    package must come after all of its dependencies. A dependency that is not a key is a package with no
    dependencies of its own, and is included. Among the valid orders, return the one that is
    alphabetically smallest (at each step, the alphabetically first package that is ready).

    If the dependencies contain a cycle, raise CycleError(cycle) where `cycle` is a list of packages
    tracing one cycle, starting and ending with the same package, e.g. ["a", "b", "c", "a"] when a depends
    on b, b on c and c on a, and starting at the alphabetically first package of that cycle.
    """
    raise NotImplementedError
