"""Pure-Python helpers for `/bulk/tag` row resolution.

Kept DB-free so the topological / collision logic is unit-testable without
a Postgres container. The route module composes these with `_get_or_create`
and SQLAlchemy work.
"""

from __future__ import annotations

from collections import defaultdict, deque


class CycleError(Exception):
    """Raised when in-batch implications form a cycle. ``names`` is the set of
    row names participating in the cycle (so the route can mark each row)."""

    def __init__(self, names: set[str]) -> None:
        super().__init__(f"Cycle in implications among: {sorted(names)}")
        self.names = names


def find_duplicate_indices(names: list[str]) -> dict[str, list[int]]:
    """Map each duplicated non-empty name to every index where it appears."""
    by_name: dict[str, list[int]] = defaultdict(list)
    for index, name in enumerate(names):
        if not name:
            continue
        by_name[name].append(index)
    return {name: idxs for name, idxs in by_name.items() if len(idxs) > 1}


def topo_sort_indices(
    names: list[str], implications_per_row: list[list[str]]
) -> list[int]:
    """Order row indices so each row's in-batch implications come first.

    Out-of-batch implication names are treated as DB references and add no
    edges. Raises :class:`CycleError` listing every row name in any cycle.
    """
    if len(names) != len(implications_per_row):
        raise ValueError("names and implications_per_row must match length")

    name_to_index: dict[str, int] = {name: idx for idx, name in enumerate(names)}

    edges_to: dict[int, set[int]] = defaultdict(set)  # idx -> {idx that need it first}
    in_degree: list[int] = [0] * len(names)

    for row_idx, impls in enumerate(implications_per_row):
        prereqs: set[int] = set()
        for impl_name in impls:
            target = name_to_index.get(impl_name)
            if target is None:
                continue
            prereqs.add(target)
        for prereq_idx in prereqs:
            if row_idx not in edges_to[prereq_idx]:
                edges_to[prereq_idx].add(row_idx)
                in_degree[row_idx] += 1

    queue: deque[int] = deque(idx for idx, deg in enumerate(in_degree) if deg == 0)
    order: list[int] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for dependent in edges_to.get(node, ()):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) < len(names):
        cycle_names = {names[idx] for idx, deg in enumerate(in_degree) if deg > 0}
        raise CycleError(cycle_names)

    return order
