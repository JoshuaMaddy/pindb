# Import Script

Run `import_csv.py` to bulk-import pins from `import.csv` placed in this directory.
Images must be in a sibling `Images/` folder.

## CSV Format

| Column | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Pin name |
| `image` | string | yes | Filename in `Images/` (e.g. `my_pin.jpg`) |
| `acquisition` | enum | yes | `single`, `blind_box`, or `set` |
| `currency` | string | yes | ISO 4217 currency code (e.g. `USD`) |
| `grades` | string | yes | See [Grades](#grades) |
| `shops` | string | yes | Comma-separated shop names (e.g. `Shop A, Shop B`) |
| `materials` | string | yes | Comma-separated tag names (legacy column name; e.g. `Hard Enamel, Gold`) merged with `tags` when attaching to a pin |
| `tags` | string | yes | Comma-separated tag names |
| `pin_sets` | string | yes | Comma-separated pin set names |
| `artists` | string | yes | Comma-separated artist names |
| `links` | string | yes | Comma-separated URLs |
| `description` | string | no | Free-text description |
| `sku` | string | no | Vendor SKU |
| `limited_edition` | bool | no | `true` or `false` |
| `number_produced` | int | no | Edition size |
| `release_date` | date | no | `YYYY-MM-DD` |
| `end_date` | date | no | `YYYY-MM-DD` |
| `funding_type` | enum | no | `self`, `crowdfunded`, or `sponsored` |
| `posts` | int | no | Number of posts (default `1`) |
| `width` | float | no | Width in mm |
| `height` | float | no | Height in mm |

Leave optional cells empty rather than omitting the column.

## Grades

Each grade encodes a condition name, quantity owned, and price paid as `name|amount|price`.
Multiple grades are separated by `, `:

```
NM|10|25.00, VF|3|15.50
```

A pin with no grades: leave the cell empty (the column must still exist).

## Example Row

```csv
name,image,acquisition,currency,grades,shops,materials,tags,pin_sets,artists,links,description,sku,limited_edition,number_produced,release_date,end_date,funding_type,posts,width,height
Frog Pin,frog.jpg,single,USD,"NM|2|12.99, VF|1|8.00",Acme Store,Hard Enamel,Nature,,Jane Smith,https://example.com,,SKU-001,true,100,2024-01-15,,self,1,30,25
```
