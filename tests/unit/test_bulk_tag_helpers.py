"""Pure-Python helpers for `/bulk/tag` row resolution: name normalization,
duplicate detection, and topological sort over in-batch implication edges."""

from __future__ import annotations

import pytest

from pindb.routes.bulk._tag_helpers import (
    CycleError,
    find_duplicate_indices,
    topo_sort_indices,
)


@pytest.mark.unit
class TestFindDuplicateIndices:
    def test_no_duplicates(self):
        assert find_duplicate_indices(["a", "b", "c"]) == {}

    def test_two_duplicates(self):
        assert find_duplicate_indices(["a", "b", "a"]) == {"a": [0, 2]}

    def test_three_duplicates(self):
        assert find_duplicate_indices(["x", "x", "x"]) == {"x": [0, 1, 2]}

    def test_empty(self):
        assert find_duplicate_indices([]) == {}

    def test_blank_names_ignored(self):
        # Empty-string names are caller's problem (validation), not duplicates.
        assert find_duplicate_indices(["a", "", "", "b"]) == {}


@pytest.mark.unit
class TestTopoSortIndices:
    def test_empty(self):
        assert topo_sort_indices([], []) == []

    def test_single(self):
        assert topo_sort_indices(["a"], [[]]) == [0]

    def test_no_in_batch_edges(self):
        # All implications point outside the batch; order is preserved.
        order = topo_sort_indices(["a", "b", "c"], [["external"], ["other"], []])
        assert order == [0, 1, 2]

    def test_chain_a_implies_b(self):
        # Row A implies row B → B must be created before A so A can link to it.
        order = topo_sort_indices(["a", "b"], [["b"], []])
        assert order == [1, 0]

    def test_chain_b_implies_a(self):
        order = topo_sort_indices(["a", "b"], [[], ["a"]])
        assert order == [0, 1]

    def test_diamond(self):
        # a→b, a→c, b→d, c→d. d first, then b/c, then a.
        names = ["a", "b", "c", "d"]
        impls = [["b", "c"], ["d"], ["d"], []]
        order = topo_sort_indices(names, impls)
        # d must come before b and c, which both come before a.
        pos = {name: i for i, name in enumerate(names[idx] for idx in order)}
        assert pos["d"] < pos["b"]
        assert pos["d"] < pos["c"]
        assert pos["b"] < pos["a"]
        assert pos["c"] < pos["a"]

    def test_simple_cycle(self):
        with pytest.raises(CycleError) as exc:
            topo_sort_indices(["a", "b"], [["b"], ["a"]])
        assert exc.value.names == {"a", "b"}

    def test_self_loop(self):
        with pytest.raises(CycleError) as exc:
            topo_sort_indices(["a"], [["a"]])
        assert exc.value.names == {"a"}

    def test_out_of_batch_implication_ignored(self):
        # Implication name not in the batch is treated as a DB ref, no edge.
        order = topo_sort_indices(["a"], [["pokemon"]])
        assert order == [0]

    def test_three_node_cycle_with_extra_node(self):
        # a→b→c→a, plus standalone d.
        with pytest.raises(CycleError) as exc:
            topo_sort_indices(
                ["a", "b", "c", "d"],
                [["b"], ["c"], ["a"], []],
            )
        assert exc.value.names == {"a", "b", "c"}

    def test_duplicate_implication_entries_collapse(self):
        # ["b", "b"] should not double-count; A still depends on B.
        order = topo_sort_indices(["a", "b"], [["b", "b"], []])
        assert order == [1, 0]
