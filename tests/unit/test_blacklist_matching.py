"""Pure matching logic for the do-not-index name blacklist."""

from __future__ import annotations

import pytest

from pindb.blacklist import (
    BLACKLIST_FUZZY_THRESHOLD,
    BlacklistMatch,
    match_blacklisted_names,
)
from pindb.database.blacklist import BlacklistedName, BlacklistEntityType


def _entry(
    name: str,
    entity_type: BlacklistEntityType = BlacklistEntityType.shop,
) -> BlacklistedName:
    return BlacklistedName(entity_type=entity_type, name=name)


@pytest.mark.unit
class TestMatchBlacklistedNames:
    def test_exact_match_ignores_case_and_spacing(self):
        entries = [_entry("Sample Shop")]

        match = match_blacklisted_names(
            candidates=["  sample   SHOP "],
            entries=entries,
        )

        assert match is not None
        assert match.exact is True
        assert match.entry_name == "Sample Shop"
        assert match.score == 100.0

    def test_typo_scores_as_fuzzy_not_exact(self):
        entries = [_entry("Sample Shop")]

        match = match_blacklisted_names(
            candidates=["Sampel Shop"],
            entries=entries,
        )

        assert match is not None
        assert match.exact is False
        assert match.score >= BLACKLIST_FUZZY_THRESHOLD

    def test_unrelated_name_does_not_match(self):
        entries = [_entry("Sample Shop")]

        match = match_blacklisted_names(
            candidates=["Completely Different Vendor"],
            entries=entries,
        )

        assert match is None

    def test_exact_match_wins_over_earlier_fuzzy(self):
        entries = [_entry("Sample Shoppe"), _entry("Sample Shop")]

        match = match_blacklisted_names(
            candidates=["sample shop"],
            entries=entries,
        )

        assert match is not None
        assert match.exact is True
        assert match.entry_name == "Sample Shop"

    def test_alias_candidate_matches_too(self):
        entries = [_entry("Sample Shop")]

        match = match_blacklisted_names(
            candidates=["Fine Pins Co", "sample shop"],
            entries=entries,
        )

        assert match is not None
        assert match.exact is True
        assert match.candidate == "sample shop"

    def test_empty_candidates_and_blank_strings_are_skipped(self):
        entries = [_entry("Sample Shop")]

        assert match_blacklisted_names(candidates=[], entries=entries) is None
        assert match_blacklisted_names(candidates=["   "], entries=entries) is None

    def test_match_carries_entity_type(self):
        entries = [_entry("Sample Artist", entity_type=BlacklistEntityType.artist)]

        match: BlacklistMatch | None = match_blacklisted_names(
            candidates=["Sample Artist"],
            entries=entries,
        )

        assert match is not None
        assert match.entity_type == BlacklistEntityType.artist
