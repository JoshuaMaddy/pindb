# Tag Creation Guide

Tags are the primary way to classify and filter pins. They are shared across the entire database — a single tag can be associated with hundreds of pins — so accuracy and consistency matter more here than almost anywhere else.

---

## Before You Create a Tag

**Search first.** The most common mistake is creating a duplicate. If a tag exists but is missing a name you would search for, add an alias instead of creating a new tag.

---

## What Makes a Good Tag

- **Specific enough to be useful, broad enough to recur.** A tag that will ever only apply to only one pin is too narrow; a tag that applies to everything is too broad.
- **Describes the pin, not your opinion of it.** Tags are factual classification, not curation.
- **Matches how people would search.** Think about what someone looking for this type of pin would type.

---

## Tag Categories

Every tag has a category. Choose the one that most accurately describes what the tag represents.

| Category      | Use for                                                                                  |
|---------------|------------------------------------------------------------------------------------------|
| **General**   | Anything that doesn't fit a more specific category. Themes, styles, objects, adjectives. |
| **Character** | A specific named character (fictional or real) — `Pikachu`, `Mario`, `Mickey Mouse`.    |
| **Archetype** | A non-distinct, non-copyrightable character type — `Wizard`, `Knight`, `Princess`.       |
| **Copyright** | A franchise, series, brand, or IP. Characters typically belong to a copyright.           |
| **Company**   | An organisation that owns or publishes a copyright — `Nintendo`, `Disney`, `Sega`.       |
| **Species**   | A type of creature or being — cat, dragon, robot, etc.                                   |
| **Material**  | The physical material or finish of the pin — hard enamel, soft enamel, glitter, etc.     |
| **Color**     | A dominant color or color scheme of the pin.                                             |
| **Meta**      | Additional information scoped to specific tags, like Pokemon Generation.                 |

**Character vs. Archetype.** A *Character* is a specific, named, usually copyrighted entity (`Link`). An *Archetype* is the generic role or trope that character fits (`Knight`). Use both where applicable — `Link` (Character) implies `Knight` (Archetype) implies `The Legend of Zelda` (Copyright) implies `Nintendo` (Company).

**Copyright vs. Company.** *Copyright* is the work itself (`Pokemon (Series)`); *Company* is the organisation behind it (`Nintendo`, `The Pokemon Company`). A copyright typically implies its company.

When in doubt, use **General**. Admins can recategorize if needed.

---

## Tag Aliases

Aliases are alternate names that the tag can be found by. They follow the same lowercase-underscore format as the tag name itself.

Good uses for aliases:
- Common alternate spellings (`grey` for a `gray` tag)
- Shortened forms (`Ghibli` for `Studio Ghibli`)
- Localizations of names (`Clefairy`, in Japanese `ピッピ`)

Aliases are searchable but not displayed directly. A tag's canonical name is what appears on pins.

---

## Tag Implications

Implications are a powerful feature: if tag **A** implies tag **B**, then any pin tagged with A is automatically also tagged with B. Implications are transitive — if A implies B and B implies C, a pin with A gets both B and C.

**Use implications to encode is-a relationships.** Examples:
- `Pikachu` implies `Pokemon (Series)` — every Pikachu is in the Pokemon series.
- `Pokemon (Series)` implies `Nintendo` — Pokemon is owned by Nintendo, hence, `Pikachu -> Pokemon (Series) -> Nintendo`.
- `Pikachu` **DOES NOT** imply `Yellow` — not *every* depiction of Pikachu has to be yellow, only canonical ones do.

**Do not use implications for loose associations.** Implications are structural, not editorial. If a connection depends on context, use a tag on the pin directly instead. If `Pikachu` is yellow in this pin, add `Yellow`.

When you add an implication to an existing tag, all pins currently tagged with that tag are updated automatically. Use this feature with great caution!
