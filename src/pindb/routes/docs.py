"""
FastAPI routes: `routes/docs.py`.
"""

import re
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from markdown_it import MarkdownIt

from pindb.templates.docs.index import docs_index
from pindb.templates.docs.page import DocEntry, DocSection, docs_page

router = APIRouter(prefix="/docs")

_DOCS_ROOT = Path(__file__).parent.parent / "static" / "docs"
_MD = MarkdownIt().enable("table")

_SECTIONS: dict[str, DocSection] = {}


def _slug_from_filename(name: str) -> str:
    """'1_editing_guidance' -> 'editing_guidance'"""
    return re.sub(r"^\d+_", "", name)


def _title_from_markdown(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _label_from_key(key: str) -> str:
    return key.replace("_", " ").title()


def _load_sections() -> dict[str, DocSection]:
    sections: dict[str, DocSection] = {}
    if not _DOCS_ROOT.exists():
        return sections
    for section_dir in sorted(_DOCS_ROOT.iterdir()):
        if not section_dir.is_dir():
            continue
        entries: list[DocEntry] = []
        for md_file in sorted(section_dir.glob("*.md")):
            stem = md_file.stem
            m = re.match(r"^(\d+)_(.+)$", stem)
            order = int(m.group(1)) if m else 0
            slug = _slug_from_filename(stem)
            text = md_file.read_text(encoding="utf-8")
            title = _title_from_markdown(text) or slug.replace("_", " ").title()
            entries.append(DocEntry(slug=slug, title=title, order=order))
        entries.sort(key=lambda e: e.order)
        if entries:
            key = section_dir.name
            sections[key] = DocSection(
                key=key,
                label=_label_from_key(key),
                entries=entries,
            )
    return sections


_SECTIONS = _load_sections()


def _find_md_file(section_key: str, slug: str) -> Path | None:
    section_dir = _DOCS_ROOT / section_key
    for md_file in section_dir.glob("*.md"):
        if _slug_from_filename(md_file.stem) == slug:
            return md_file
    return None


@router.get("")
def docs_root(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=str(docs_index(request=request, sections=list(_SECTIONS.values())))
    )


@router.get("/{section_key}")
def docs_section_root(section_key: str) -> RedirectResponse:
    section = _SECTIONS.get(section_key)
    if not section or not section.entries:
        raise HTTPException(status_code=404)
    first = section.entries[0]
    return RedirectResponse(url=f"/docs/{section_key}/{first.slug}", status_code=302)


@router.get("/{section_key}/{page_slug}")
def docs_page_route(request: Request, section_key: str, page_slug: str) -> HTMLResponse:
    section = _SECTIONS.get(section_key)
    if not section:
        raise HTTPException(status_code=404)

    md_file = _find_md_file(section_key, page_slug)
    if not md_file:
        raise HTTPException(status_code=404)

    text = md_file.read_text(encoding="utf-8")
    rendered = _MD.render(text)

    entry = next((e for e in section.entries if e.slug == page_slug), None)
    page_title = entry.title if entry else page_slug.replace("_", " ").title()

    return HTMLResponse(
        content=str(
            docs_page(
                request=request,
                section=section,
                current_slug=page_slug,
                rendered_html=rendered,
                page_title=page_title,
            )
        )
    )
