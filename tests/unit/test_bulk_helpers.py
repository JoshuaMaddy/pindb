"""Unit tests for src/pindb/routes/bulk/_helpers.py — no DB required."""

from datetime import date

import pytest

from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.model_utils import MagnitudeParseError
from pindb.routes.bulk._helpers import (
    BULK_SCALAR_FIELDS,
    TagMode,
    _coerce_bulk_scalar,
    apply_bulk_scalars,
    compute_tag_change,
    snapshot_scalar_updates,
)


@pytest.mark.unit
class TestComputeTagChange:
    def test_add_unions(self):
        assert compute_tag_change({1, 2}, {2, 3}, TagMode.add) == {1, 2, 3}

    def test_remove_subtracts(self):
        assert compute_tag_change({1, 2, 3}, {2, 4}, TagMode.remove) == {1, 3}

    def test_replace_overwrites(self):
        assert compute_tag_change({1, 2}, {3, 4}, TagMode.replace) == {3, 4}

    def test_add_empty_submitted_noop(self):
        assert compute_tag_change({1, 2}, set(), TagMode.add) == {1, 2}

    def test_replace_empty_clears(self):
        assert compute_tag_change({1, 2}, set(), TagMode.replace) == set()


@pytest.mark.unit
class TestCoerceScalar:
    def test_acquisition_type(self):
        result = _coerce_bulk_scalar("acquisition_type", "single")
        assert result == AcquisitionType.single

    def test_funding_type(self):
        result = _coerce_bulk_scalar("funding_type", "self")
        assert result == FundingType.self

    def test_limited_edition_bool(self):
        assert _coerce_bulk_scalar("limited_edition", "on") is True
        assert _coerce_bulk_scalar("limited_edition", "false") is False

    def test_number_produced_int(self):
        assert _coerce_bulk_scalar("number_produced", "42") == 42

    def test_width_parses_magnitude_like_pin_form(self):
        assert _coerce_bulk_scalar("width", "12.5mm") == 12.5
        assert _coerce_bulk_scalar("width", "1in") == 25.4
        assert _coerce_bulk_scalar("height", "2cm") == 20.0

    def test_width_idempotent_after_mm_float(self):
        """apply_bulk_scalars coerces twice; stored mm floats must pass through."""
        assert _coerce_bulk_scalar("width", 12.5) == 12.5

    def test_invalid_width_raises(self):
        with pytest.raises(MagnitudeParseError):
            _coerce_bulk_scalar("width", "not-a-dimension")

    def test_release_date(self):
        assert _coerce_bulk_scalar("release_date", "2026-01-05") == date(2026, 1, 5)

    def test_empty_becomes_none(self):
        assert _coerce_bulk_scalar("number_produced", "") is None


class _FakePin:
    """Minimal duck-typed stand-in for Pin in apply_bulk_scalars tests."""

    def __init__(self) -> None:
        self.acquisition_type = AcquisitionType.single
        self.limited_edition: bool | None = None
        self.number_produced: int | None = None
        self.release_date: date | None = None
        self.end_date: date | None = None
        self.funding_type: FundingType | None = None
        self.posts = 1
        self.width: float | None = None
        self.height: float | None = None


@pytest.mark.unit
class TestApplyBulkScalars:
    def test_only_submitted_fields_change(self):
        pin = _FakePin()
        pin.width = 10.0
        apply_bulk_scalars(pin, {"posts": "3"})  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
        assert pin.posts == 3
        # Untouched fields stay as they were.
        assert pin.width == 10.0
        assert pin.number_produced is None

    def test_multiple_fields(self):
        pin = _FakePin()
        apply_bulk_scalars(
            pin,  # ty:ignore[invalid-argument-type]
            {
                "limited_edition": "on",
                "number_produced": "500",
                "release_date": "2026-02-01",
            },
        )
        assert pin.limited_edition is True
        assert pin.number_produced == 500
        assert pin.release_date == date(2026, 2, 1)

    def test_unknown_field_ignored(self):
        pin = _FakePin()
        apply_bulk_scalars(pin, {"not_a_field": "oops", "posts": "7"})  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
        assert pin.posts == 7
        assert not hasattr(pin, "not_a_field")


@pytest.mark.unit
class TestSnapshotScalarUpdates:
    def test_enums_serialize(self):
        out = snapshot_scalar_updates(
            {
                "acquisition_type": AcquisitionType.blind_box,
                "funding_type": FundingType.crowdfunded,
                "release_date": date(2026, 3, 1),
                "posts": 4,
            }
        )
        assert out == {
            "acquisition_type": "blind_box",
            "funding_type": "crowdfunded",
            "release_date": "2026-03-01",
            "posts": 4,
        }

    def test_unknown_fields_dropped(self):
        out = snapshot_scalar_updates({"posts": 4, "rogue": "x"})
        assert out == {"posts": 4}

    def test_bulk_scalar_fields_coverage(self):
        # Sanity guard: new fields added to the helper should get a unit too.
        assert "posts" in BULK_SCALAR_FIELDS
        assert "acquisition_type" in BULK_SCALAR_FIELDS
