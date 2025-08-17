from typing import Sequence

from fastapi.datastructures import URL
from htpy import div, form, fragment, h1, h2, input, label, option, select

from pindb.database import Material, Shop
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base

DIMENSION_PATTERN = r".*?(\d*\.?\d*)\s*(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"


def pin_form(
    post_url: URL | str,
    materials: Sequence[Material],
    shops: Sequence[Shop],
):
    return html_base(
        fragment[
            h1["Create a Pin"],
            form(hx_post=str(post_url))[
                h2["Required Fields"],
                div[
                    label(for_="name")["Name"],
                    input(type="text", name="name", id="name", required=True),
                ],
                div[
                    label(for_="acquisition_type")["Acquisition"],
                    select(name="acquisition_type", required=True)[
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
                    select(name="material_ids", required=True)[
                        [
                            option(value=material.id)[material.name]
                            for material in materials
                        ]
                    ],
                ],
                div[
                    label(for_="shop_ids")["Shops"],
                    select(name="shop_ids", required=True)[
                        [option(value=shop.id)[shop.name] for shop in shops]
                    ],
                ],
                h2["Optional Fields"],
                # Production
                div[
                    label(for_="limited_edition")["Limited Edition"],
                    input(name="limited_edition", type="checkbox"),
                ],
                div[
                    label(for_="number_produced")["Number Produced"],
                    input(name="number_produced", type="number", min=0, step=1),
                ],
                div[
                    label(for_="release_date")["Release Date"],
                    input(name="release_date", type="date"),
                ],
                div[
                    label(for_="end_date")["End Date"],
                    input(name="end_date", type="date"),
                ],
                div[
                    label(for_="funding_type")["Funding Type"],
                    select(name="funding_type")[
                        [
                            option(value=funding)[funding.replace("_", " ").title()]
                            for funding in FundingType
                        ]
                    ],
                ],
                # Physical
                div[
                    label(for_="posts")["Posts"],
                    input(name="posts", type="number", min=1, step=1, value=1),
                ],
                div[
                    label(for_="width")["Width"],
                    input(name="width", type="text", pattern=DIMENSION_PATTERN),
                ],
                div[
                    label(for_="height")["Height"],
                    input(name="height", type="text", pattern=DIMENSION_PATTERN),
                ],
                input(type="submit", value="Submit"),
            ],
        ]
    )
