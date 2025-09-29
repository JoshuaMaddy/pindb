from pathlib import Path
from typing import Sequence

from fastapi.datastructures import URL
from htpy import br, button, div, form, fragment, h1, h2, input, label, option, select

from pindb.database import Material, Shop, Tag
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base

DIMENSION_PATTERN = r".*?(\d*\.?\d*)\s*(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"

with open(
    Path(__file__).parent.parent / "js/pin_creation.js", "r", encoding="utf-8"
) as js_file:
    SCRIPT_CONTENT = js_file.read()


def pin_form(
    post_url: URL | str,
    materials: Sequence[Material],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
):
    return html_base(
        body_content=fragment[
            h1["Create a Pin"],
            form(hx_post=str(post_url), enctype="multipart/form-data")[
                h2["Required Fields"],
                div[
                    label(for_="front_image")["Front Image"],
                    input(
                        type="file",
                        id="image",
                        name="front_image",
                        accept="image/png, image/jpeg, image/jpg, image/webp",
                        required=True,
                    ),
                ],
                div[
                    label(for_="name")["Name"],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        autocomplete="off",
                    ),
                ],
                div[
                    label(for_="acquisition_type")["Acquisition"],
                    select(
                        name="acquisition_type",
                        id="acquisition_type",
                        required=True,
                    )[
                        [
                            option(value=acquisition_type)[
                                acquisition_type.replace("_", " ").title()
                            ]
                            for acquisition_type in AcquisitionType
                        ]
                    ],
                ],
                div[
                    label(for_="material_ids")["Materials"],
                    select(
                        name="material_ids",
                        id="material_ids",
                        required=True,
                    )[
                        [
                            option(value=material.id)[material.name]
                            for material in materials
                        ]
                    ],
                ],
                div[
                    label(for_="shop_ids")["Shops"],
                    select(
                        name="shop_ids",
                        id="shop_ids",
                        required=True,
                    )[[option(value=shop.id)[shop.name] for shop in shops]],
                ],
                div[
                    label(for_="tag_ids")["Tags"],
                    select(
                        name="tag_ids",
                        id="tag_ids",
                        required=True,
                    )[[option(value=tag.id)[tag.name] for tag in tags]],
                ],
                h2["Optional Fields"],
                # Images
                div[
                    label(for_="back_image")["Back Image"],
                    input(
                        type="file",
                        id="image",
                        name="back_image",
                        accept="image/png, image/jpeg, image/jpg, image/webp",
                    ),
                ],
                # Production
                div[
                    label(for_="limited_edition")["Limited Edition"],
                    input(
                        name="limited_edition",
                        id="limited_edition",
                        type="checkbox",
                    ),
                ],
                div[
                    label(for_="number_produced")["Number Produced"],
                    input(
                        name="number_produced",
                        id="number_produced",
                        type="number",
                        min=0,
                        step=1,
                    ),
                ],
                div[
                    label(for_="release_date")["Release Date"],
                    input(
                        name="release_date",
                        id="release_date",
                        type="date",
                    ),
                ],
                div[
                    label(for_="end_date")["End Date"],
                    input(
                        name="end_date",
                        id="end_date",
                        type="date",
                    ),
                ],
                div[
                    label(for_="funding_type")["Funding Type"],
                    select(
                        name="funding_type",
                        id="funding_type",
                    )[
                        [
                            option(value=funding)[funding.replace("_", " ").title()]
                            for funding in FundingType
                        ]
                    ],
                ],
                # Physical
                div[
                    label(for_="posts")["Posts"],
                    input(
                        name="posts",
                        id="posts",
                        type="number",
                        min=1,
                        step=1,
                        value=1,
                    ),
                ],
                div[
                    label(for_="width")["Width"],
                    input(
                        name="width",
                        id="width",
                        type="text",
                        pattern=DIMENSION_PATTERN,
                    ),
                ],
                div[
                    label(for_="height")["Height"],
                    input(
                        name="height",
                        id="height",
                        type="text",
                        pattern=DIMENSION_PATTERN,
                    ),
                ],
                div[
                    label(for_="links")["Links"],
                    div(id="links")[
                        input(
                            name="links",
                            id="link_0",
                            type="text",
                        ),
                    ],
                    br,
                    button(id="add-link-button")["Add Link"],
                ],
                input(type="submit", value="Submit"),
            ],
        ],
        script_content=SCRIPT_CONTENT,
    )
