import type { CollectionEntry } from 'astro:content';
import fs from 'node:fs';
import path from 'node:path';

// Category/novels folder slug is already baked into the entry's path-based id
// (e.g. "world-history/sapiens" -> "world-history"), since the migration script
// writes one folder per category. Deriving it this way guarantees it always
// matches the folder actually on disk, rather than re-slugifying the display name.
export function folderSlug(entry: CollectionEntry<'books'>): string {
  return entry.id.split('/')[0];
}

// connects_from / connects_to store the frontmatter's own `id` (a bare slug,
// e.g. "guns-germs-and-steel"), not the path-based collection id. This finds
// the entry whose frontmatter id matches, so we can build a working link.
export function findByDataId(
  books: CollectionEntry<'books'>[],
  dataId: string | null
): CollectionEntry<'books'> | undefined {
  if (!dataId) return undefined;
  return books.find((b) => b.data.id === dataId);
}

// Mirrors scripts/migrate_curriculum.py's CATEGORY_SLUGS so a non-fiction
// category *name* (e.g. from connects_to_nonfiction) can link to its
// /categories/<slug>/ page without a second data lookup. Novels use "novels".
const CATEGORY_SLUGS: Record<string, string> = {
  'World History': 'world-history',
  'British History': 'british-history',
  'Biography': 'biography',
  'Psychology': 'psychology',
  'Science': 'science',
  'Politics & Economics': 'politics-economics',
  'Religion & Mythology': 'religion-mythology',
  'Ancient Philosophy': 'ancient-philosophy',
  'Modern Philosophy': 'modern-philosophy',
  'Leadership, Business & Decision Making': 'leadership-business-decision-making',
  'Military History': 'military-history',
  'Technology & AI': 'technology-ai',
  'Nature, Geography & Environment': 'nature-geography-environment',
  'Health & Longevity': 'health-longevity',
  'Exploration, Adventure & Travel': 'exploration-adventure-travel',
  'Novels': 'novels',
};

export function categorySlug(name: string): string | undefined {
  return CATEGORY_SLUGS[name];
}

// Sequence-ordered view of the whole 500-book master reading order (novels
// interleaved with non-fiction). Used for the book page's primary "next/prev"
// links so they follow the actual staircase, not just same-category order.
export function bySequence(books: CollectionEntry<'books'>[]): CollectionEntry<'books'>[] {
  return [...books]
    .filter((b) => b.data.sequence != null)
    .sort((a, b) => (a.data.sequence ?? 0) - (b.data.sequence ?? 0));
}

// Reading-progress helpers, all driven off review.reading_status /
// review.finished_date. A book counts as "read" once reading_status is
// 'finished' -- kept as a function (not a filter callers repeat) so the
// homepage, category pages, and any future page agree on the definition.
export function isFinished(b: CollectionEntry<'books'>): boolean {
  return b.data.review.reading_status === 'finished';
}
export function isCurrentlyReading(b: CollectionEntry<'books'>): boolean {
  return b.data.review.reading_status === 'reading';
}

export function readingProgress(books: CollectionEntry<'books'>[]) {
  const finished = books.filter(isFinished);
  const reading = books.filter(isCurrentlyReading);
  const lastFinished = finished.length
    ? [...finished].sort((a, b) =>
        (b.data.review.finished_date ?? '').localeCompare(a.data.review.finished_date ?? '')
      )[0]
    : null;
  return {
    finishedCount: finished.length,
    total: books.length,
    currentlyReading: reading[0] ?? null,
    lastFinished,
  };
}

// Minimal RFC4180 CSV parser — handles quoted fields, embedded commas, and
// escaped quotes ("" inside a quoted field). Used for data/ownership.csv,
// which is exported straight from LibraryThing/Kindle/Audible and can have
// commas in subtitles.
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\r') {
      // skip, \n handles the line break
    } else if (c === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else {
      field += c;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

// Slug helpers mirroring scripts/migrate_curriculum.py's slugify()/last_name_slug(),
// so ownership-library slugs feel consistent with curriculum slugs even though
// they're generated independently (ownership.csv has no stable "id" of its own).
function slugify(s: string): string {
  const ascii = s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, ''); // strip accents, like the Python unicodedata step
  return ascii
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function lastNameSlug(author: string): string {
  const cleaned = author.replace(/\(.*?\)/g, '').trim();
  const firstAuthor = cleaned.replace(/&/g, ',').split(',')[0];
  const parts = firstAuthor.trim().split(/\s+/).filter(Boolean);
  return parts.length ? slugify(parts[parts.length - 1]) : 'unknown';
}

export interface OwnedBook {
  slug: string;
  title: string;
  subtitle: string;
  author: string;
  formats: string[];
}

// Reads data/ownership.csv (a sibling of the `site/` directory at the repo
// root) and returns every owned book with a unique slug. Shared by the
// library index (search/filter list) and the per-book detail pages, so both
// generate the exact same slug for the exact same row.
export function loadOwnershipBooks(): OwnedBook[] {
  const csvPath = path.resolve(process.cwd(), '../data/ownership.csv');
  const raw = fs.readFileSync(csvPath, 'utf-8');
  const rows = parseCsv(raw).filter((r) => r.length > 1 && r[0] !== '');
  const [, ...dataRows] = rows;

  const usedSlugs = new Set<string>();
  const books: OwnedBook[] = [];

  for (const r of dataRows) {
    const title = r[0]?.trim() ?? '';
    if (!title) continue;
    const subtitle = r[1]?.trim() ?? '';
    const author = r[2]?.trim() ?? '';
    const formats = (r[3] ?? '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const base = slugify(title);
    let slug = base;
    if (usedSlugs.has(slug)) {
      slug = `${base}-${lastNameSlug(author)}`;
    }
    if (usedSlugs.has(slug)) {
      let i = 2;
      while (usedSlugs.has(`${base}-${lastNameSlug(author)}-${i}`)) i++;
      slug = `${base}-${lastNameSlug(author)}-${i}`;
    }
    usedSlugs.add(slug);

    books.push({ slug, title, subtitle, author, formats });
  }

  return books.sort((a, b) => a.title.localeCompare(b.title));
}
