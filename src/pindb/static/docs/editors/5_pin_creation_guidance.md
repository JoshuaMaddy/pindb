# Pin Creation Guide

Pins are the core of the database. A complete, accurate pin entry makes it easier for collectors to identify, track, and find the pins they're looking for.

---

## Before You Create a Pin

**Search first.** Check that the pin does not already exist in the database. Try searching by name, artist, and shop. If the pin exists but is missing information, edit it rather than creating a duplicate.

---

## Required Fields

### Name

The pin's name as the creator has given it. Use the name from the shop listing, packaging, or the artist's own description. If no official name exists, use a short, descriptive name that identifies the pin clearly.

### Acquisition type

How the pin was sold:

| Type          | Use when                                                             |
|---------------|----------------------------------------------------------------------|
| **Single**    | Sold individually, buyer knows exactly what they are getting.        |
| **Blind box** | Sold in packaging where the specific design is unknown until opened. |
| **Set**       | Sold as part of a multi-pin package where all contents are known.    |

### Front image

A clear photo of the front of the pin. See the image guidelines below.

### Shop

At least one shop must be associated with the pin — the shop that sold or produced it. If the shop does not exist yet, create it first (it can be pending) and then associate it here.

---

## Optional Fields

### Back image

A photo of the back of the pin. Useful for showing post type, stamps, markings, or back art. Not required but encouraged for well-documented entries.

### Artists

The creator(s) of the pin's artwork. If the artist does not exist yet, create them first and associate them here.

### Description

A description of the pin's subject matter, any notable details, or context about the release. Keep it factual.

### Limited edition / Number produced

Check **limited edition** if the pin was explicitly sold as a limited run. Enter the edition size in **number produced** if known.

### Release date / End date

The date the pin went on sale (or pre-order!), and the date sales ended (for limited or time-limited releases). Use the date the shop opened orders, not the date of shipment.

### Funding type

| Type            | Use when                                      |
|-----------------|-----------------------------------------------|
| **Self**        | Funded directly by the artist or shop.        |
| **Crowdfunded** | Funded via Kickstarter, Makeship, or similar. |
| **Sponsored**   | Funded or commissioned by a third party.      |

### Dimensions

Width and height in millimeters. Measure the widest and tallest points of the pin design, not the backing card. Make your best educated guess if possible, but, if totally unknown leave blank.

### Posts

The number of pin posts (clutch backs).

### SKU

The shop's internal product identifier, if one is publicly listed. Useful for distinguishing variants.

### Tags

Select all applicable tags. You only need to select explicit tags — implied tags are added automatically. For example, tagging a pin `Pikachu` will automatically apply `Pokemon (Series)`.

### Grades

The condition grades available or applicable for this pin. If a shop sells pins at "grades", document them to the best of your ability. This includes the *original* price per grade, as well as primary currency. If there is no grade, leave the default `Normal` grade and populate price and currency if known.

### Links

External URLs for this specific pin — the original shop listing, a fan wiki page, etc.

### Variants

Other pins in the database that are variants of this one (color variants, size variants, etc.). Variant relationships are symmetric — adding pin B as a variant of pin A also makes pin A a variant of pin B.

### Unauthorized copies

Known bootleg or unauthorized copies of this pin. Use this to flag counterfeits that appear in the database, not simply similar-looking designs.

---

## Image Guidelines

If taking an image of a pin because no official images can be found, or choosing an official image:

- **Resolution:** Higher is better.
- **Background:** A plain, neutral background makes the pin easier to see. White or light grey works well.
- **Lighting:** Even lighting without harsh shadows. Avoid flash glare on metallic finishes.
- **Orientation:** Front-facing, not angled. The full pin should be visible with minimal cropping.
- **File size:** Up to 20 MB. JPG, PNG, and WEBP all work.

EXIF data (GPS, device info) is stripped automatically on upload.

---

## Pins Sold in Sets

If a pin was sold as part of a multi-pin product set, each individual pin should have its own entry. Then create (or find) a Pin Set entry and add all the pins to it. This allows each pin to be tracked individually in collections and want lists while preserving the set relationship.