"""
Screenshot capture + pixel-diff assertions for e2e visual parity checks.

Baselines live in ``tests/e2e/__screenshots__/`` (committed; captured on this
dev machine — font/antialiasing rendering is OS-specific, so regenerate them
here, not in CI). Failures write ``<name>.actual.png`` and ``<name>.diff.png``
to ``tests/e2e/artifacts/`` (gitignored) for review. Regenerate baselines with
``uv run pytest -m e2e --update-screenshots``.

The pixel threshold is deliberately generous — the semantic gate is a visual
review of new/changed baselines and diff artifacts, not pixel-perfection.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch
from playwright.sync_api import Locator, Page

BASELINE_DIR: Path = Path(__file__).parent / "__screenshots__"
ARTIFACT_DIR: Path = Path(__file__).parent / "artifacts"

# Kill animations/transitions/caret so captures are stable frame-to-frame.
_FREEZE_CSS: str = (
    "*, *::before, *::after {"
    " animation: none !important;"
    " transition: none !important;"
    " caret-color: transparent !important;"
    " }"
)

# Fraction of pixels allowed to differ before the assertion fails.
_MAX_DIFF_RATIO: float = 0.001


def _capture(target: Page | Locator) -> Image.Image:
    page: Page = target if isinstance(target, Page) else target.page
    page.add_style_tag(content=_FREEZE_CSS)
    page.evaluate("document.fonts.ready")
    return Image.open(BytesIO(target.screenshot())).convert("RGBA")


def assert_screenshot(
    target: Page | Locator,
    name: str,
    *,
    update: bool = False,
) -> None:
    """Capture ``target`` and compare against the committed baseline.

    Args:
        target (Page | Locator): Playwright page or locator to capture.
        name (str): Baseline name; maps to ``__screenshots__/<name>.png``.
        update (bool): Overwrite the baseline instead of asserting
            (wired to ``--update-screenshots`` via the fixture).
    """
    actual: Image.Image = _capture(target)
    baseline_path: Path = BASELINE_DIR / f"{name}.png"

    if update or not baseline_path.exists():
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        actual.save(baseline_path)
        if not update:
            raise AssertionError(
                f"No baseline for {name!r}; wrote {baseline_path}. Visually "
                "review it, commit it, and re-run."
            )
        return

    baseline: Image.Image = Image.open(baseline_path).convert("RGBA")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    if baseline.size != actual.size:
        actual.save(ARTIFACT_DIR / f"{name}.actual.png")
        raise AssertionError(
            f"Screenshot {name!r} size changed: baseline {baseline.size} vs "
            f"actual {actual.size}. Actual saved to artifacts/; if intended, "
            "re-run with --update-screenshots."
        )

    diff_image: Image.Image = Image.new(mode="RGBA", size=actual.size)
    mismatched: int = pixelmatch(
        baseline,
        actual,
        diff_image,
        threshold=0.15,
    )
    total_pixels: int = actual.size[0] * actual.size[1]
    ratio: float = mismatched / total_pixels
    if ratio > _MAX_DIFF_RATIO:
        actual.save(ARTIFACT_DIR / f"{name}.actual.png")
        diff_image.save(ARTIFACT_DIR / f"{name}.diff.png")
        raise AssertionError(
            f"Screenshot {name!r} differs from baseline: {mismatched} px "
            f"({ratio:.3%} > {_MAX_DIFF_RATIO:.3%}). See artifacts/{name}"
            ".{actual,diff}.png; if intended, --update-screenshots."
        )
