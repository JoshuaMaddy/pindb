import asyncio
from pathlib import Path

import polars as pl
from polars import DataFrame, read_csv
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.file_handler import save_file

image_folder: Path = Path(__file__).parent / "images"

df: DataFrame = read_csv(Path(__file__).parent / "import.csv")

df = df.with_columns(
    tags=pl.col("tags").str.split(", "),
    shops=pl.col("shops").str.split(", "),
    materials=pl.col("materials").str.split(", "),
    pin_sets=pl.col("pin_sets").str.split(", "),
    artists=pl.col("artists").str.split(", "),
    grades=pl.col("grades").str.split(", "),
    description=pl.col("description").str.strip_chars(),
    name=pl.col("name").str.strip_chars(),
    image=pl.col("image").str.strip_chars(),
)

tags_set: set[str] = set()
for row in df.select(pl.col("tags")).unique().rows():
    tags_set.update(row[0])

shops_set: set[str] = set()
for row in df.select(pl.col("shops")).unique().rows():
    shops_set.update(row[0])

pin_sets_set: set[str] = set()
for row in df.select(pl.col("pin_sets")).unique().rows():
    pin_sets_set.update(row[0])

artists_set: set[str] = set()
for row in df.select(pl.col("artists")).unique().rows():
    artists_set.update(row[0])

links_set: set[str] = set()
for row in df.select(pl.col("links")).unique().rows():
    links_set.update(row[0])

with session_maker.begin() as session:
    for shop_name in shops_set:
        if not session.scalar(select(Shop).where(Shop.name == shop_name)):
            session.merge(Shop(name=shop_name))

    for tag_name in tags_set:
        if not session.scalar(select(Tag).where(Tag.name == tag_name)):
            session.merge(Tag(name=tag_name))

    for pins_set_name in pin_sets_set:
        if not session.scalar(select(PinSet).where(PinSet.name == pins_set_name)):
            session.merge(PinSet(name=pins_set_name))

    for link_path in links_set:
        if not session.scalar(select(Link).where(Link.path == link_path)):
            session.merge(Link(path=link_path))


async def import_csv():
    with session_maker.begin() as session:
        for row in df.rows(named=True):
            image_path = (
                Path(__file__).parent / "Images" / str(row["image"])
            ).resolve()

            if not image_path:
                print(f"No image found with name: {row['image']}")
                continue

            currency = session.scalar(
                select(Currency).where(Currency.code == row["currency"])
            )

            if not currency:
                print(f"No currency found with code: {row['currency']}")
                continue

            material_tag_names: list[str] = row.get("materials") or []
            tags = session.scalars(
                select(Tag).where(Tag.name.in_(list(row["tags"]) + material_tag_names))
            )
            pin_sets = session.scalars(
                select(PinSet).where(PinSet.name.in_(row["pin_sets"]))
            )
            shops = session.scalars(select(Shop).where(Shop.name.in_(row["shops"])))
            artists = session.scalars(
                select(Artist).where(Artist.name.in_(row["artists"]))
            )
            links = session.scalars(select(Link).where(Link.path.in_(row["links"])))
            grades = {
                Grade(
                    name=grade[0],
                    price=float(grade[2]) if grade[2].strip() else None,
                )
                for raw in row["grades"]
                if (grade := raw.split("|")) and len(grade) == 3 and grade[0].strip()
            }

            session.add(
                Pin(
                    name=row["name"],
                    acquisition_type=row["acquisition"],
                    front_image_guid=await save_file(image_path),
                    currency=currency,
                    shops=set(shops),
                    limited_edition=row["limited_edition"],
                    number_produced=row["number_produced"],
                    release_date=row["release_date"],
                    end_date=row["end_date"],
                    funding_type=row["funding_type"],
                    posts=row["posts"],
                    width=row["width"],
                    height=row["height"],
                    description=row["description"],
                    sku=row["sku"],
                    artists=set(artists),
                    sets=set(pin_sets),
                    tags=set(tags),
                    links=set(links),
                    grades=grades,
                )
            )


if __name__ == "__main__":
    asyncio.run(import_csv())
