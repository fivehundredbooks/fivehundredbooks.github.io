import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// A hand-edited (or GitHub-web-UI-edited) frontmatter date like
// `started_on: 2026-07-11` is unquoted YAML, which every compliant YAML
// parser -- including whatever Astro's content loader uses -- resolves to a
// native Date via the core schema's implicit !!timestamp tag, not a string.
// Rather than relying on every future hand-edit (or migrate_curriculum.py
// rerun) to remember to quote these, accept either shape here and normalize
// to a plain YYYY-MM-DD string, since that's what util.ts's string-based
// getReadingStatus()/localeCompare() sorting throughout the site expects.
const dateStringField = z
  .union([z.string(), z.date()])
  .nullable()
  .transform((v) => (v instanceof Date ? v.toISOString().slice(0, 10) : v));

const books = defineCollection({
  loader: glob({
    pattern: ['**/*.md', '!README.md'],
    base: '../data/curriculum',
  }),
  schema: z.object({
    id: z.string(),
    title: z.string(),
    subtitle: z.string().nullable(),
    author: z.string(),
    type: z.enum(['nonfiction', 'fiction']),
    category: z.string(),
    mini_theme: z.number().nullable(),
    mini_theme_name: z.string().nullable(),
    level: z.number().nullable(),
    sequence: z.number().nullable(),
    phase: z.string().nullable(),
    round: z.number().nullable(),
    status: z.enum(['draft', 'confirmed']),
    why_chosen: z.string().nullable(),
    connects_from: z.string().nullable(),
    connects_to: z.string().nullable(),
    source_lists: z.array(z.string()),
    owned: z.boolean(),
    connects_to_nonfiction: z.array(z.string()).optional(),
    connects_to_nonfiction_note: z.string().nullable().optional(),
    placement_note: z.string().nullable().optional(),
    // Homepage "Currently Reading" fields -- hand-set once a book is
    // actually picked up, not produced by migrate_curriculum.py's parsers.
    // .optional() (not just .nullable()) because most of the 500 files
    // predate these fields and don't have the keys at all yet; the script
    // will backfill them with explicit nulls/[] on its next full re-run,
    // same pattern as `review` below.
    image: z.string().nullable().optional(),
    about: z.string().nullable().optional(),
    tags: z.array(z.string()).optional(),
    goodreads_url: z.string().nullable().optional(),
    review: z.object({
      own_site_url: z.string().nullable(),
      medium_url: z.string().nullable(),
      linkedin_posted: z.string().nullable(),
      rating: z.number().nullable(),
      // Plain ISO date strings (YYYY-MM-DD), hand-set in a book's frontmatter
      // when you actually start/finish it. Reading status (not_started/
      // reading/finished) is deliberately NOT stored as its own field -- it's
      // derived from these two dates by lib/util.ts's getReadingStatus(), so
      // there's only one thing to keep in sync, not two. migrate_curriculum.py
      // preserves both across re-runs.
      started_on: dateStringField,
      finished_on: dateStringField,
      // Short (1-2 sentence) takeaway -- meant to show up in list/timeline
      // views (e.g. /reading-log/) even before a full review is written.
      // The Markdown body below frontmatter is still the place for a full
      // review; this is just the quick "what did I actually learn" note.
      key_takeaway: z.string().nullable(),
    }),
  }),
});

const blog = defineCollection({
  loader: glob({
    pattern: '**/*.md',
    base: './src/content/blog',
  }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    tags: z.array(z.string()).optional(),
  }),
});

export const collections = { books, blog };
