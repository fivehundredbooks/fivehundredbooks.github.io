import type { CollectionEntry } from 'astro:content';

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
