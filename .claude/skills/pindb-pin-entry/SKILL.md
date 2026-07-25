---
name: pindb-pin-entry
description: Fill out the PinDB "Create a Pin" web form (pindb.info) from a source listing (a shop product page, or a page listing many pins). Invoke when asked to add a pin, or a batch of pins, to PinDB from an external site, using claude-in-chrome browser automation.
---

# PinDB Pin Entry (browser automation)

Drives `pindb.info` via `mcp__claude-in-chrome__*` tools to create pin (and supporting
shop/artist/tag) entries from an external source page (Shopify product page, marketplace
listing, etc). Load the browser tools first if deferred:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,
mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__tabs_create_mcp,
mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__form_input
```

## Golden rule: never submit without explicit confirmation

Creating a pin/shop/artist/tag is a public-content action (it goes into a shared, pending-review
database — see below). Always show the user the filled-out form (screenshot or summary) and get
an explicit go-ahead before clicking Submit. Holding off on submit when asked is the default, not
the exception.

## Mental model: pending review, not a private draft

Every entity you create (pin, shop, artist, tag, pin set) enters a **pending** state — invisible
to the public until an admin approves it. So creating a shop/tag/artist "to unblock the pin form"
is normal and expected, not a side effect to avoid. Pin approval cascades: approving a pin
auto-approves any pending shops/artists/tags attached to it, so you don't need to wait on each
dependency separately.

## Before creating anything: search first

Shops, artists, and tags are shared across every pin that references them. Duplicates are hard to
clean up later. Before creating a new shop/artist/tag, search for it (type into the relevant
picker on the pin form, or check `/list`) — if it exists under a slightly different name, that's
what aliases are for, not a new entity.

## Step 1 — Extract source data

On the source page (e.g. a Shopify product page), pull:
- **Name** — the title as the seller lists it.
- **Highest-resolution image URL.** Shopify CDN images are named `<basename>_<width>x.<ext>`
  (e.g. `_960x.jpg`). Read the `srcset`/`src` via `javascript_tool`, then strip the `_<width>x`
  size suffix and the leading `//` to get the master original — e.g.
  `.../Chemistry_Cat_V2_..._1080x.jpg?v=...` → `.../Chemistry_Cat_V2_....jpg?v=...`. Download it
  with `Bash`/`curl` into the scratchpad directory, then `Read` the file to visually inspect it
  before describing/tagging the pin.
- **Price + currency**, size/height, materials/plating mentioned in the description, post/clutch
  count, and the product page URL (for the pin's Links field).

## Step 2 — Fill `/create/pin`

Go to `https://pindb.info/create/pin`. Upload the downloaded image to the **Front Image** file
input (find it via `find` — it's a hidden file input right after the "Front Image" button; use
`file_upload`, never click it directly). Then fill fields top to bottom.

### Form quirks (learned the hard way)

- **The page scrolls/reflows after the image upload finishes** (front-image preview pushes layout
  down). Take a fresh screenshot before clicking coordinates for Name/Shops — a click aimed at the
  pre-upload layout can land on the wrong field.
- **MultiSelect pickers (Shops, Artists, Tags, Pin Sets, Variants) do not support create-on-type**,
  despite what you might expect from a "type to search" box. Typing a name that doesn't exist just
  shows "No results found" — there is no inline "+ Create" option and pressing Enter does not
  create anything (it just clears the input). If the entity doesn't exist yet, open a **new tab**,
  go to `/create/shop`, `/create/artist`, or `/create/tag`, create it there, then return to the
  pin tab and re-search — the new entity appears in the dropdown within a second or two (Meilisearch
  index lag). Keep the pin-form tab open throughout; its in-progress field values persist across
  tab switches.
- **Tags dropdown shows a "Tag parents" preview** under the input once you select a tag with
  implications (e.g. selecting `Hard Enamel` shows it implies `Enamel`) — you don't need to add
  the parent tag yourself, it's implied automatically on save.
- **Grade price/currency** live next to the Grade name field: the "Unknown" placeholder input is
  actually the **price** field, and the `UNK` dropdown next to it is the **currency** — set both
  when the source page lists a price (use `form_input` with the currency's 3-letter ISO code, e.g.
  `"USD"`, not a numeric value).
- Use `browser_batch` or at minimum batch click+type+screenshot per field to cut round-trips.

### Field-by-field mapping

| Form field | Source | Notes |
|---|---|---|
| Front Image (required) | highest-res product image | see Step 1 |
| Back Image (optional) | back-of-pin photo if the listing has one | often absent for third-party shops |
| Name (required) | listing title | drop boilerplate like "- Hard Enamel Pin" only if the DB convention (check a few existing pins in that shop) strips it — otherwise keep as listed |
| Shops (required) | seller name | create shop first if missing (see below) |
| Artists (optional) | credited illustrator, if named separately from the shop | only add if a distinct name is given; if a studio doesn't credit per-pin, omit entirely (per Artist Guide) |
| Acquisition (required) | how it's sold | `Single` unless the listing is a blind box or multi-pin set — see Acquisition table below |
| Grade (required) | price + currency from listing | leave grade name as `Normal` unless the shop sells named quality tiers (Firsts/Seconds etc — see an example pin in that shop) |
| Tags (required) | subject, materials, colors, character/species | see Tagging below |
| Posts | "two posts", "single post", etc from listing description | numeric |
| Height / Width | listing's stated dimensions | mm or `N.Nin`; leave blank if genuinely unknown, don't guess |
| Funding Type | | `Self` unless listing explicitly says Kickstarter/Makeship (`Crowdfunded`) or names a commissioning third party (`Sponsored`) |
| Limited Edition / Number Produced | | only set Yes if explicitly sold as a limited run |
| Links | product page URL | paste the exact URL you sourced the pin from |
| Description | listing's description + your own visual read of the downloaded image | factual only — subject matter, notable details, materials; no opinions |

### Acquisition types

| Type | Use when |
|---|---|
| Single | Sold individually, buyer knows exactly what they're getting |
| Blind box | Specific design unknown until opened |
| Set | Sold as part of a multi-pin package where contents are known |

### Tagging

Look at 2-3 existing pins from the same shop or a visually similar pin (via `/list` → a shop with
pins → open one, `get_page_text`) to learn the site's tagging conventions before inventing your
own vocabulary. In general, tag:
- **Species/Character** — what's depicted (`Cat`, `Pikachu`, etc). Only tag explicit things —
  implied tags apply automatically via tag implications (e.g. tagging `Pikachu` auto-applies
  `Pokemon (Series)`).
- **Material** — `Hard Enamel` / `Soft Enamel` / `Glitter`, plating (`Gold Plating`, `Black Nickel
  Plating`, etc) as stated in the listing.
- **Color** — each dominant color visible in the actual artwork (check the downloaded image, not
  just the listing text) — e.g. `Black`, `Gold`, `Green`, `Blue`, `Purple`, `White`.
- **Notable objects/props** in the art if they recur as a useful category (`Book`, `Lab Coat`) —
  check whether the tag already exists first; if not, and it's specific-enough-to-recur /
  broad-enough-to-apply (per Tag Creation Guide), create it via `/create/tag` with **Category =
  General** unless it's clearly Material/Color/Species/Character/Archetype/Copyright/Company/Meta.
- **Before finalizing tags, do one explicit pass over the downloaded image and name every distinct
  object depicted, not just the ones that jump out first.** A pin has a subject (the cat) plus
  props that carry real search value (microscope, flask, books, goggles, lab coat) — it's easy to
  tag the obvious central figure and materials/colors while dropping a prop that's just as visible
  in the art. If a described object doesn't have a tag yet (e.g. `Microscope`), create it — don't
  silently drop it because it's not in your first-pass list.
- Tag categories, in order of how likely you'll need them for pins: `Species`, `Character`,
  `Archetype`, `Copyright`, `Company`, `Material`, `Color`, `Meta`, `General` (catch-all).
- Never invent an implication relationship (Tag Creation Guide: "not for loose associations") —
  only select tags, don't set up parent/child or implies relationships during pin entry.

## Step 3 — Creating a missing Shop

`/create/shop`: Name (exact public-facing name/capitalization/punctuation), optional Description,
Links (their storefront URL), Aliases. Submit, then return to the pin tab and re-search the Shops
field — the new shop appears once Meili re-indexes (usually within ~1s, occasionally needs a
retry).

## Step 4 — Creating a missing Artist

`/create/artist`, only if the listing credits a specific illustrator distinct from the shop
itself. Use their public handle/studio name, not a legal name, unless that's how they're
publicly known.

## Step 5 — Batch mode (a page listing many pins)

When given a listing/collection page with multiple pins:
1. Enumerate all product links on the page first (`find` or `read_page` for the product grid).
2. Process one pin fully (Steps 1-2, including any new shop/artist/tag creation) before moving to
   the next — this keeps shop/artist/tag reuse consistent (created once, reused across the rest of
   the batch without re-searching from scratch every time... but still re-verify via search since
   dropdown state doesn't carry across page loads).
3. Confirm each filled form with the user before submitting, or ask up front whether they want to
   review the whole batch at once vs. pin-by-pin — don't assume batch approval.
4. Track progress with `TaskCreate`/`TaskUpdate` (one task per pin) so a long batch survives
   context compaction.

## Reference: all doc pages (fetch again if this skill goes stale)

- `/docs` — index
- `/docs/editors/editing_guidance` — Editor Guide (pending system, approval/rejection, quality bar)
- `/docs/editors/shop_creation_guidance`
- `/docs/editors/artist_creation_guidance`
- `/docs/editors/tag_creation_guidance`
- `/docs/editors/pin_creation_guidance`
- `/docs/editors/pin_set_creation_guidance` (sets vs tags: use a set when order/membership of a
  specific release matters, e.g. a boxed set; use a tag for a factual property shared across many
  pins, e.g. `Cat`. Global sets need direct admin approval — don't attempt to create one solo.)
