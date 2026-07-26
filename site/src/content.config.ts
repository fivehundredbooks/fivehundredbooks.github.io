import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

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
      started_on: z.string().nullable(),
      finished_on: z.string().nullable(),
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
