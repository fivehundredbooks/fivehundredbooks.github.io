import csv, re
from collections import defaultdict, Counter

SRC_DIR = '/sessions/nice-stoic-pascal/mnt/500BOOKS'
OUT = '/sessions/nice-stoic-pascal/mnt/outputs/All_Books_Owned.csv'

HONORIFICS = r'^(sir|dr|dame|lord|lady|professor|prof|mr|mrs|ms|rev)\.?\s+'

def clean_text(s):
    if not s:
        return ''
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = ' '.join(s.strip().split())
    return s

def title_key(t):
    t = clean_text(t).lower()
    t = re.sub(r"[^a-z0-9' ]", ' ', t)
    return ' '.join(t.split())

def subtitle_key(s):
    s = clean_text(s).lower()
    s = re.sub(r"[^a-z0-9' ]", ' ', s)
    return ' '.join(s.split())

def primary_author_raw(a):
    a = clean_text(a)
    parts = re.split(r',| and | & ', a)
    return clean_text(parts[0]) if parts else a

def author_key(a):
    a = primary_author_raw(a).lower()
    a = re.sub(HONORIFICS, '', a)
    a = a.replace('.', '')
    a = re.sub(r'[^a-z0-9 ]', ' ', a)
    return ' '.join(a.split())

def norm_author_display(a):
    a = clean_text(a)
    # normalize separators to "; "
    parts = re.split(r'\s*,\s*|\s+and\s+|\s*&\s*', a)
    parts = [p.strip() for p in parts if p.strip()]
    return '; '.join(parts)

sources = [
    ('Physical', '26_LibraryThing_Physical_Library.csv', 'TITLE', 'SUBTITLE', 'AUTHOR'),
    ('Kindle', '27_Kindle_Library.csv', 'TITLE', 'Subtitle', 'Author'),
    ('Audible', '28_Audible_Library.csv', 'TITLE', 'SUBTITLE', 'AUTHOR'),
]

# Step 1: load + dedupe within each source on (title_key, subtitle_key, author_key)
records = []  # each: dict with tkey, skey, akey, title, subtitle, author, format
for fmt, fname, tcol, scol, acol in sources:
    seen = set()
    with open(f'{SRC_DIR}/{fname}', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        title = clean_text(row.get(tcol, ''))
        subtitle = clean_text(row.get(scol, ''))
        author = clean_text(row.get(acol, ''))
        if not title:
            continue
        tk = title_key(title)
        sk = subtitle_key(subtitle)
        ak = author_key(author)
        dup_key = (tk, sk, ak)
        if dup_key in seen:
            continue
        seen.add(dup_key)
        records.append({
            'tk': tk, 'sk': sk, 'ak': ak,
            'title': title, 'subtitle': subtitle, 'author': norm_author_display(author),
            'format': fmt,
        })

print(f'Records after within-source dedup: {len(records)}')

# Step 2: exact cross-format merge on (tk, sk, ak)
exact_groups = defaultdict(list)
for r in records:
    exact_groups[(r['tk'], r['sk'], r['ak'])].append(r)

# Step 3: determine ambiguity for (tk, ak). We only treat it as a genuine
# multi-volume/series situation (don't merge) if a SINGLE SOURCE lists more
# than one distinct subtitle under the same title+author -- that means the
# source itself is distinguishing separate books. If each source has at most
# one entry for that title+author, differing subtitle wording across
# platforms is just inconsistent metadata for the same book, and is safe to merge.
ta_source_subtitles = defaultdict(lambda: defaultdict(set))
for r in records:
    if r['sk']:
        ta_source_subtitles[(r['tk'], r['ak'])][r['format']].add(r['sk'])

def is_ambiguous(tk, ak):
    per_source = ta_source_subtitles.get((tk, ak), {})
    return any(len(subs) > 1 for subs in per_source.values())

# Step 4: union-find style merge — merge exact_groups further by (tk, ak) if unambiguous
# (i.e. at most one distinct non-empty subtitle exists for that tk+ak across all sources)
final_key_for_exact_group = {}
loose_groups = defaultdict(list)  # (tk, ak) -> list of exact_group keys
for key in exact_groups:
    tk, sk, ak = key
    loose_groups[(tk, ak)].append(key)

merged = defaultdict(list)  # final merge key -> list of records
used = set()
for (tk, ak), keys in loose_groups.items():
    if not is_ambiguous(tk, ak):
        # safe to merge all exact_groups under this tk+ak into one book
        final_key = (tk, ak, 'MERGED')
        for k in keys:
            merged[final_key].extend(exact_groups[k])
    else:
        # ambiguous (multi-volume/series) — keep each exact subtitle group separate
        for k in keys:
            merged[k].extend(exact_groups[k])

print(f'Final unique book groups (pre blank-author fold): {len(merged)}')

# Step 5: fold blank-author groups into a same-title group that HAS an author,
# when there is exactly one such candidate (handles source rows missing author
# metadata, e.g. Audible often omits AUTHOR for some titles).
tk_to_named_groups = defaultdict(set)
for gkey in merged:
    tk = gkey[0]
    ak = gkey[1] if gkey[2] == 'MERGED' else gkey[2]
    if ak:
        tk_to_named_groups[tk].add(gkey)

blank_keys = [gkey for gkey in merged if (gkey[1] if gkey[2] == 'MERGED' else gkey[2]) == '']
for gkey in blank_keys:
    tk = gkey[0]
    candidates = tk_to_named_groups.get(tk, set())
    if len(candidates) == 1:
        target = next(iter(candidates))
        merged[target].extend(merged.pop(gkey))

print(f'Final unique book groups: {len(merged)}')

# Step 5b: build output rows
output_rows = []
for gkey, recs in merged.items():
    titles = Counter(r['title'] for r in recs)
    subtitles = Counter(r['subtitle'] for r in recs if r['subtitle'])
    authors = Counter(r['author'] for r in recs)
    formats = sorted(set(r['format'] for r in recs), key=lambda f: ['Physical','Kindle','Audible'].index(f))

    best_title = titles.most_common(1)[0][0]
    best_subtitle = subtitles.most_common(1)[0][0] if subtitles else ''
    best_author = authors.most_common(1)[0][0]

    output_rows.append({
        'Title': best_title,
        'Subtitle': best_subtitle,
        'Author': best_author,
        'Format': ', '.join(formats),
        'Formats Owned': len(formats),
    })

output_rows.sort(key=lambda r: (r['Title'].lower(), r['Subtitle'].lower()))

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['Title', 'Subtitle', 'Author', 'Format', 'Formats Owned'])
    w.writeheader()
    w.writerows(output_rows)

multi = [r for r in output_rows if r['Formats Owned'] > 1]
print(f'Total unique books: {len(output_rows)}')
print(f'Owned in multiple formats: {len(multi)}')
print('Sample multi-format books:')
for r in multi[:15]:
    print(' ', r['Title'], '|', r['Author'], '|', r['Format'])
