"""Unit tests for src/pindb/model_utils.py — no DB required."""

import pytest

from pindb.model_utils import empty_str_list_to_none, empty_str_to_none, magnitude_to_mm


@pytest.mark.unit
class TestEmptyStrToNone:
    def test_none_passthrough(self):
        assert empty_str_to_none(None) is None

    def test_empty_string_becomes_none(self):
        assert empty_str_to_none("") is None

    def test_non_empty_string_unchanged(self):
        assert empty_str_to_none("hello") == "hello"

    def test_whitespace_string_unchanged(self):
        # Whitespace is NOT empty — only the literal "" becomes None
        assert empty_str_to_none("   ") == "   "


@pytest.mark.unit
class TestEmptyStrListToNone:
    def test_none_passthrough(self):
        assert empty_str_list_to_none(None) is None

    def test_single_empty_string_becomes_none(self):
        assert empty_str_list_to_none([""]) is None

    def test_non_empty_list_unchanged(self):
        assert empty_str_list_to_none(["a", "b"]) == ["a", "b"]

    def test_multiple_items_including_empty_unchanged(self):
        # Only [""] (exactly one empty string) collapses to None
        assert empty_str_list_to_none(["", "b"]) == ["", "b"]

    def test_empty_list_unchanged(self):
        assert empty_str_list_to_none([]) == []


@pytest.mark.unit
class TestMagnitudeToMm:
    def test_inches_word(self):
        assert magnitude_to_mm("2 inches") == pytest.approx(50.8)

    def test_inch_singular(self):
        assert magnitude_to_mm("1 inch") == pytest.approx(25.4)

    def test_in_abbreviation_lower(self):
        assert magnitude_to_mm("1.5 in") == pytest.approx(38.1)

    def test_in_abbreviation_upper(self):
        assert magnitude_to_mm("1.5 IN") == pytest.approx(38.1)

    def test_centimeters_word(self):
        assert magnitude_to_mm("5 centimeters") == pytest.approx(50.0)

    def test_cm_abbreviation(self):
        assert magnitude_to_mm("3.5 cm") == pytest.approx(35.0)

    def test_cm_abbreviation_upper(self):
        assert magnitude_to_mm("3.5 CM") == pytest.approx(35.0)

    def test_millimeters_word(self):
        assert magnitude_to_mm("25 millimeters") == pytest.approx(25.0)

    def test_mm_abbreviation(self):
        assert magnitude_to_mm("38 mm") == pytest.approx(38.0)

    def test_mm_abbreviation_upper(self):
        assert magnitude_to_mm("38 MM") == pytest.approx(38.0)

    def test_decimal_mm(self):
        assert magnitude_to_mm("38.5 mm") == pytest.approx(38.5)

    def test_no_unit_returns_zero(self):
        assert magnitude_to_mm("25") == 0

    def test_no_match_returns_zero(self):
        assert magnitude_to_mm("not a measurement") == 0

    def test_empty_string_returns_zero(self):
        assert magnitude_to_mm("") == 0

    def test_leading_text_ignored(self):
        # Regex uses .*? so leading text is ok
        assert magnitude_to_mm("size: 12 mm") == pytest.approx(12.0)
