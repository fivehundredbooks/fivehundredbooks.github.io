---
status: draft — proposed schema for the GitHub repo, not yet built
date: 2026-07-26
---

# Data schema for the 500 Books repo

This defines the data layer the future GitHub repo, website, and scripts will
all read from. It does not touch the curriculum content itself (`22_...`,
`25_...`, etc. stay exactly as they are, still pending your review) — it only
defines the *shape* that content moves into once each category is locked.

## Why two datasets, not one

There are two different lists living in this project, and they should stay
separate rather than merge into one file:

**The curriculum** — the 500 curated books (125 novels + 375 non-fiction).
This is the public-facing dataset: it's what the website displays, what
category/level/mini-theme pages are built from, and what reviews attach to.
Small, curated, slow-changing.

**Ownership** — everything you actually own across Kindle, Audible, and
Physical (`29_All_Books_Owned.csv`, ~2,200 records). Most of these aren't
part of the 500 — they're thrillers, comics, sales books, etc. This is a
private inventory, not site content. It only becomes relevant to the site
where it overlaps with the curriculum (so a curriculum page can show "you
own this on Kindle" or link an affiliate purchase link).

A single merged table would force every thriller you own into the same
schema as Sapiens, and would force curriculum books into an ownership
schema before you've even bought them. Keeping them separate, joined by a
shared `id`, avoids that.

## 1. Curriculum records — one Markdown file per book

Recommended shape: **one `.md` file per book**, YAML frontmatter for
structured fields, Markdown body for the review once you've written one.
This is the format Astro/11ty/Hugo "content collections" read natively —
the site build reads the folder directly, no separate database or sync
step. It's also git-diff friendly, so `git log` on a single book file *is*
the edit history CLAUDE.md asks you to keep.

Path convention: `/data/curriculum/<category-slug>/<book-slug>.md`
e.g. `/data/curriculum/world-history/sapiens.md`

```yaml
---
id: sapiens-harari              # stable slug, used in URLs and cross-refs — never rename once published
title: Sapiens
subtitle: A Brief History of Humankind
author: Yuval Noah Harari
type: nonfiction                # nonfiction | fiction
category: World History         # one of the 15, or "Novels" for fiction
mini_theme: 1                   # 1-5 within the category
mini_theme_name: "Big Frameworks — Why Civilizations Rise and Fall"
level: 0                        # 0-10
sequence: null                  # global position in the full 500-book order — filled in once that's locked
status: draft                   # draft | confirmed  (tracks CLAUDE.md's "not yet locked" convention)
why_chosen: >
  Opens the category with a macro-framework the reader can test every later,
  narrower book against.
connects_from: null             # id of the book this follows, once sequence is set
connects_to: guns-germs-and-steel-diamond
source_lists: []                # novels only — which of the 9 canon lists it appeared on
owned: false                    # true once you own it — id of the ownership record it maps to, or false
review:
  own_site_url: null
  medium_url: null
  linkedin_posted: null         # date, once posted — LinkedIn has no reliable API, so this stays a manual flag
  rating: null
  started_on: null              # ISO date, hand-set when you actually start a book
  finished_on: null             # ISO date, hand-set when you actually finish it (supersedes the original finished_date name)
  key_takeaway: null            # 1-2 sentence takeaway, shown in list/timeline views ahead of a full review
---

<!-- Review body goes here once written. Empty until then. -->
```

Fields worth flagging:

- `status: draft` mirrors what's already in `25_Levels_and_MiniThemes_Draft.md`
  — nothing here forces you to lock the curriculum before the repo exists.
  Migration from the current Markdown-table drafts into individual files is
  its own step, done once a category is actually confirmed, not before.
- `mini_theme_name` is duplicated across the 5 books in that theme by
  design — cheap redundancy that keeps each file self-contained rather than
  needing a join to a separate mini-themes table.
- `owned` is a boolean/link, not a copy of format/ASIN data — that detail
  lives in the ownership record so it isn't duplicated in two places.
- Reading status (not started / reading / finished) is deliberately **not**
  its own field — it's computed from `started_on`/`finished_on` at build time
  (`getReadingStatus()` in the site's `lib/util.ts`), so there's one pair of
  dates to hand-edit per book, not a status enum that can drift out of sync
  with them. (2026-07-26: this replaced an earlier `reading_status` enum +
  `finished_date` pair added directly to the live schema ahead of this doc;
  this section now reflects what's actually live.)
- **Always quote `started_on`/`finished_on` in YAML** (`started_on: "2026-07-11"`,
  not `started_on: 2026-07-11`). Unquoted, it's a bare YAML date scalar, which
  every compliant YAML parser (including whatever Astro's content loader
  uses) resolves to a native `Date` via the core schema's implicit
  `!!timestamp` tag — not a string — which fails the Zod schema's
  `z.string()` check and breaks the build. (2026-07-27: hit this for real —
  a direct GitHub-web-UI edit set `started_on: 2026-07-11` unquoted on
  Sapiens and broke the build. Fixed at the schema layer, not just by
  requoting that one file: `content.config.ts` now accepts either a string
  or a `Date` for both fields and normalizes to a plain `YYYY-MM-DD` string,
  so a future unquoted hand-edit can't reintroduce this.)
- (2026-07-27) Added four optional "Currently Reading" fields, populated by
  hand once a book is actually picked up — not produced by
  `migrate_curriculum.py`'s parsers, so the script reads them back and
  carries them forward on every rerun, same as `review`/`status: confirmed`:
  - `image` — a hotlinkable cover URL (Open Library's covers API by ISBN is
    the default source: `https://covers.openlibrary.org/b/isbn/<isbn>-L.jpg`)
  - `about` — a 2-4 sentence blurb for the homepage card (distinct from
    `why_chosen`, which is about curriculum placement, not the book itself)
  - `tags` — a short list of freeform subject tags, shown as pills
  - `goodreads_url` — link to the book's Goodreads page
  All four are `.optional()` (not just `.nullable()`) in the Zod schema,
  since most of the 500 files predate them and don't have the keys at all
  yet — only `sapiens.md` has real values so far, as the pilot for the
  homepage's "Currently Reading" section.

## 2. Ownership records — extend the existing CSV, don't replace it

`29_All_Books_Owned.csv` keeps its current shape (Title, Subtitle, Author,
Format, Formats Owned) as the base, with columns added as they become
useful rather than all at once:

| Column | Added when |
|---|---|
| `curriculum_id` | as soon as any owned book matches a curriculum `id` — links the two datasets |
| `asin` | going forward, since Kindle purchases are ASIN-first (see below) |
| `isbn` | backfilled for Physical only, from the LibraryThing re-export |
| `reading_status` | when you want the site to show "currently reading" |
| `date_finished` | same |

Because ASIN differs per edition (a Kindle ASIN and an Audible ASIN for the
same book are different values), `asin` should really be one value per
*format*, not per book row. The simplest fix without restructuring the
whole file: keep one row per format when an ASIN is recorded (undoing the
multi-format merge only for that book), or add `asin_kindle` /
`asin_audible` as separate columns. Worth deciding once you're actually
capturing ASINs rather than now.

## 3. Repo layout

```
/data
  /curriculum
    /world-history/*.md
    /british-history/*.md
    ... (15 category folders + /novels)
  ownership.csv              # current 29_All_Books_Owned.csv, evolving per above
/scripts
  consolidate_libraries.py   # the Kindle/Audible/Physical dedup script already built
  lookup_asin.py             # future: Amazon Product Advertising API lookups
/site
  (Astro/11ty/Hugo project, reads from /data at build time)
CNAME                        # fivehundredbooks.com, for GitHub Pages custom domain
```

## 4. What this unlocks later, without redesigning anything

- **Affiliate links** — generated from `asin` at build time, no new field needed.
- **"You own this" badges on the site** — from `owned` + a join on `curriculum_id`.
- **Review syndication** — the Markdown body is the canonical review; a
  script can push it to Medium via their API with a canonical-URL pointer
  back to the site, and prep (not auto-post) the LinkedIn version.
- **Reading progress / "currently reading" page** — from `reading_status`
  and `date_finished`, no schema change.

## Not decided yet, on purpose

- Whether `/site` is Astro, 11ty, or Hugo — a build-tooling choice, not a
  data-modeling one, and doesn't block anything above.
- The full 375-book cross-category interleaved reading order — `sequence`
  stays `null` until that pass happens, per the note in
  `25_Levels_and_MiniThemes_Draft.md`.
- Migrating the current Markdown-table drafts into individual `.md` files —
  do this category by category, only once a category is confirmed, so
  drafts don't get treated as locked by accident.
