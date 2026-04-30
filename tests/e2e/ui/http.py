"""Helpers for httpx-driven HTML assertions in e2e UI specs."""

from __future__ import annotations

from bs4 import BeautifulSoup


def parse_html(response) -> BeautifulSoup:
    return BeautifulSoup(response.text, "html.parser")
