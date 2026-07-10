"""Confirmation modal for irreversible account deletion: user must type username."""

from __future__ import annotations

from htpy import Element

from pindb.templates.components.islands import island


def delete_account_modal(
    trigger: Element,
    expected_username: str,
    form_action: str,
) -> Element:
    """Svelte ``delete-account-modal`` island: *expected_username* must be
    typed before the POST submit is enabled."""
    return island(
        "delete-account-modal",
        props={
            "triggerHtml": str(trigger),
            "expectedUsername": expected_username,
            "formAction": form_action,
        },
        class_="inline-flex items-center self-start",
    )
