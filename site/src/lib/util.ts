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
