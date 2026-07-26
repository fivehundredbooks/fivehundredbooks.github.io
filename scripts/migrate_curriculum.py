"""
Migrate the 500 Books curriculum from the project folder's Markdown drafts
into one YAML-frontmatter .md file per book under /data/curriculum/, per
the schema in 30_Data_Schema.md.

Run from the repo root, with INPUT_DIR pointed at the 500BOOKS project
folder (the one with 22_Full_125_Novels_List.md, 25_Levels_and_MiniThemes_Draft.md,
29_All_Books_Owned.csv, 31_All_125_Novels_NonFiction_Connections.md, and
32-35_PhaseN_Reading_Order.md).

Re-run this whenever the curriculum, reading order, or ownership file changes
-- it's idempotent for structural fields (category, level, sequence, etc.,
regenerated from source each time). Reading-progress data is NOT
regenerated: `review` (started_on, finished_on, key_takeaway, rating, ...), a
`status: confirmed` promotion, and any hand-written review body are read
back from the existing file (if one exists) and carried forward untouched,
so logging progress on a book is safe even if a category gets re-migrated
later. Legacy keys from an older schema (reading_status, finished_date) are
dropped rather than carried forward -- see DEFAULT_REVIEW/write_book() below.

Built 2026-07-26 as part of the first migration. Six passes:
  1. parse non-fiction (25_...) -> category/mini-theme/level per book
  2. parse novels (22_...) -> title/author/source lists
  3. parse novel<->category connections (31_...)
  4. parse the 4 phase files (32-35_...) -> global sequence 1-500
  5. cross-reference ownership (29_All_Books_Owned.csv)
  6. assign ids, compute connects_from/connects_to, write files
"""
import csv, json, os, re, unicodedata
from collections import defaultdict, Counter
import yaml

INPUT_DIR = os.environ.get("CURRICULUM_INPUT_DIR", "/tmp/work")
OUT_ROOT = os.environ.get("CURRICULUM_OUT_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "curriculum"))

def p(name):
    return os.path.join(INPUT_DIR, name)

CATEGORY_SLUGS = {
    "World History": "world-history",
    "British History": "british-history",
    "Biography": "biography",
    "Psychology": "psychology",
    "Science": "science",
    "Politics & Economics": "politics-economics",
    "Religion & Mythology": "religion-mythology",
    "Ancient Philosophy": "ancient-philosophy",
    "Modern Philosophy": "modern-philosophy",
    "Leadership, Business & Decision Making": "leadership-business-decision-making",
    "Military History": "military-history",
    "Technology & AI": "technology-ai",
    "Nature, Geography & Environment": "nature-geography-environment",
    "Health & Longevity": "health-longevity",
    "Exploration, Adventure & Travel": "exploration-adventure-travel",
}

ABBR = {
    "WH": "World History", "BH": "British History", "Bio": "Biography",
    "Psy": "Psychology", "Sci": "Science", "PE": "Politics & Economics",
    "RM": "Religion & Mythology", "AP": "Ancient Philosophy", "MP": "Modern Philosophy",
    "LBD": "Leadership, Business & Decision Making", "MH": "Military History",
    "Tech": "Technology & AI", "Nat": "Nature, Geography & Environment",
    "Health": "Health & Longevity", "Expl": "Exploration, Adventure & Travel",
}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r"[^a-z0-9]+", ' ', s)
    s = ' '.join(s.split())
    s = re.sub(r'^(the|a|an)\s+', '', s)
    return s

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", '-', s)
    return s.strip('-')

def last_name_slug(author):
    author = re.sub(r'\(.*?\)', '', author).strip()
    parts = author.replace('&', ',').split(',')[0].split()
    return slugify(parts[-1]) if parts else 'unknown'

def split_title_subtitle(title):
    if ': ' in title:
        t, sub = title.split(': ', 1)
        return t.strip(), sub.strip()
    return title, None

def parse_nonfiction():
    text = open(p('25_Levels_and_MiniThemes_Draft.md'), encoding='utf-8').read()
    cat_pattern = re.compile(r'^## \d+\.\s+(.+?)\s*$', re.M)
    matches = list(cat_pattern.finditer(text))
    books = []
    for i, m in enumerate(matches):
        cat_name = m.group(1).strip()
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[start:end]
        if cat_name not in CATEGORY_SLUGS:
            continue
        mt_pattern = re.compile(r'\*\*Mini-theme (\d+):\s*(.+?)\.\*\*\s*(.*?)(?=\n\n\|)', re.S)
        mt_matches = list(mt_pattern.finditer(block))
        for mi, mtm in enumerate(mt_matches):
            mt_num = int(mtm.group(1))
            mt_name = mtm.group(2).strip()
            mt_start = mtm.end()
            mt_end = mt_matches[mi+1].start() if mi+1 < len(mt_matches) else len(block)
            table_block = block[mt_start:mt_end]
            row_pattern = re.compile(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$', re.M)
            for level_s, title_raw, author_raw in row_pattern.findall(table_block):
                title = title_raw.strip()
                author_field = author_raw.strip()
                note = None
                note_m = re.match(r'^(.*?)\s+—\s+\*(.+?)\*\s*$', author_field)
                if note_m:
                    author, note = note_m.group(1).strip(), note_m.group(2).strip()
                else:
                    author = author_field
                books.append({
                    "category": cat_name, "mini_theme": mt_num, "mini_theme_name": mt_name,
                    "level": int(level_s), "title": title, "author": author, "note": note,
                })
    return books

def parse_novels():
    text = open(p('22_Full_125_Novels_List.md'), encoding='utf-8').read()
    row_pattern = re.compile(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$', re.M)
    novels = []
    for num_s, title, author, sources in row_pattern.findall(text):
        if num_s == '#':
            continue
        note = None
        note_m = re.search(r'\s+—\s+\*(.+?)\*\s*$', sources)
        if note_m:
            note = note_m.group(1).strip()
            sources = sources[:note_m.start()].strip()
        novels.append({
            "num": int(num_s), "title": title.strip(), "author": author.strip(),
            "source_lists": [s.strip() for s in sources.split(',')] if sources else [],
            "note": note,
        })
    return novels

def parse_connections():
    text = open(p('31_All_125_Novels_NonFiction_Connections.md'), encoding='utf-8').read()
    row_pattern = re.compile(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$', re.M)
    conns = {}
    for num_s, title, author, connects, link in row_pattern.findall(text):
        if num_s == '#':
            continue
        codes = [c.strip() for c in connects.split(',')]
        conns[int(num_s)] = {"categories": [ABBR.get(c, c) for c in codes], "link": link.strip()}
    return conns

def parse_sequence(nf_lookup, nov_lookup):
    PHASE_FILES = [
        ('Phase 1', p('32_Phase1_Reading_Order.md')), ('Phase 2', p('33_Phase2_Reading_Order.md')),
        ('Phase 3', p('34_Phase3_Reading_Order.md')), ('Phase 4', p('35_Phase4_Reading_Order.md')),
    ]
    head_re = re.compile(r'^(\d+)\.\s+(\*\*|\*)(.+?)\2\s+—\s+(.*)$')
    trailing_note_re = re.compile(r'^(.*\))\s+—\s+\*(.+?)\*\s*$')
    round_re = re.compile(r'^##\s+Round\s+(\d+)')
    seq = 0
    entries = []
    current_round = None
    for phase_name, path in PHASE_FILES:
        text = open(path, encoding='utf-8').read()
        for line in text.split('\n'):
            rm = round_re.match(line)
            if rm:
                current_round = int(rm.group(1))
                continue
            hm = head_re.match(line.strip())
            if not hm:
                continue
            item_num, marker, title, rest = hm.groups()
            note = None
            nm = trailing_note_re.match(rest)
            if nm:
                rest, note = nm.group(1), nm.group(2)
            if not rest.endswith(')'):
                continue
            last_open = rest.rfind('(')
            category_raw = rest[last_open+1:-1].strip()
            author = rest[:last_open].strip()
            seq += 1
            is_novel = category_raw.lower() == 'novel'
            entry = {"sequence": seq, "phase": phase_name, "round": current_round,
                      "title": title.strip(), "author": author.strip(),
                      "category_raw": category_raw, "is_novel": is_novel,
                      "note": note.strip() if note else None}
            if is_novel:
                cands = nov_lookup.get(norm(title))
                if cands:
                    entry["matched_num"] = cands[0]["num"]
            entries.append(entry)
    return entries

def match_ownership(title, author, owned_by_title):
    cands = owned_by_title.get(norm(title))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    ln = last_name_slug(author).replace('-', ' ')
    for c in cands:
        if ln and ln in norm(c['Author']):
            return c
    return cands[0]

def main():
    nonfiction = parse_nonfiction()
    novels = parse_novels()
    connections = parse_connections()

    nf_lookup = defaultdict(list)
    for b in nonfiction:
        nf_lookup[(norm(b['title']), norm(b['category']))].append(b)
    nov_lookup = defaultdict(list)
    for n in novels:
        nov_lookup[norm(n['title'])].append(n)

    seq_entries = parse_sequence(nf_lookup, nov_lookup)
    seq_nf, seq_nov = {}, {}
    for e in seq_entries:
        if e['is_novel']:
            if 'matched_num' in e:
                seq_nov[e['matched_num']] = e
        else:
            seq_nf[(norm(e['title']), norm(e['category_raw']))] = e

    owned_by_title = defaultdict(list)
    with open(p('29_All_Books_Owned.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            owned_by_title[norm(row['Title'])].append(row)

    for b in nonfiction:
        m = match_ownership(b['title'], b['author'], owned_by_title)
        b['owned'] = bool(m)
    for n in novels:
        m = match_ownership(n['title'], n['author'], owned_by_title)
        n['owned'] = bool(m)

    used_ids = set()
    def make_id(title, author, disambiguator=None):
        base = slugify(title)
        if base not in used_ids:
            used_ids.add(base); return base
        cand = f"{base}-{last_name_slug(author)}"
        if cand not in used_ids:
            used_ids.add(cand); return cand
        if disambiguator:
            cand2 = f"{base}-{slugify(disambiguator)}"
            if cand2 not in used_ids:
                used_ids.add(cand2); return cand2
        i = 2
        while f"{cand}-{i}" in used_ids:
            i += 1
        used_ids.add(f"{cand}-{i}")
        return f"{cand}-{i}"

    nf_by_category = defaultdict(list)
    for b in nonfiction:
        nf_by_category[b['category']].append(b)
    for b in nonfiction:
        b['id'] = make_id(b['title'], b['author'], disambiguator=b['category'])
    for cat, books_in_cat in nf_by_category.items():
        for i, b in enumerate(books_in_cat):
            b['connects_from'] = books_in_cat[i-1]['id'] if i > 0 else None
            b['connects_to'] = books_in_cat[i+1]['id'] if i < len(books_in_cat)-1 else None
    for b in nonfiction:
        e = seq_nf.get((norm(b['title']), norm(b['category'])))
        b['sequence'] = e['sequence'] if e else None
        b['phase'] = e['phase'] if e else None
        b['round'] = e['round'] if e else None

    novels_sorted = sorted(novels, key=lambda n: n['num'])
    for n in novels_sorted:
        n['id'] = make_id(n['title'], n['author'])
    for i, n in enumerate(novels_sorted):
        n['connects_from'] = novels_sorted[i-1]['id'] if i > 0 else None
        n['connects_to'] = novels_sorted[i+1]['id'] if i < len(novels_sorted)-1 else None
    for n in novels_sorted:
        e = seq_nov.get(n['num'])
        n['sequence'] = e['sequence'] if e else None
        n['phase'] = e['phase'] if e else None
        n['round'] = e['round'] if e else None
        n['placement_note'] = e['note'] if e else None
        conn = connections.get(n['num'])
        n['connects_to_categories'] = conn['categories'] if conn else []
        n['connects_to_categories_note'] = conn['link'] if conn else None

    FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n(.*)$', re.S)
    DEFAULT_REVIEW = {"own_site_url": None, "medium_url": None, "linkedin_posted": None,
                      "rating": None, "started_on": None, "finished_on": None,
                      "key_takeaway": None}
    DEFAULT_REST = "\n<!-- Review body goes here once written. Empty until then. -->\n"

    def load_existing(out_path):
        """Read back whatever a previous run (or a hand-edit) left in place, so a
        re-migration never clobbers logged reading progress. Returns None for a
        book that's never been written before."""
        if not os.path.exists(out_path):
            return None
        text = open(out_path, encoding='utf-8').read()
        m = FRONTMATTER_RE.match(text)
        if not m:
            return None
        front_text, rest = m.groups()
        try:
            front = yaml.safe_load(front_text) or {}
        except yaml.YAMLError:
            return None
        return {"status": front.get("status"), "review": front.get("review") or {}, "rest": rest}

    def write_book(out_path, data):
        existing = load_existing(out_path)
        if existing:
            # Drop any keys from an older schema (e.g. the retired
            # reading_status/finished_date fields) rather than carrying them
            # forward as dead cruft in every file.
            old_review = {k: v for k, v in (existing["review"] or {}).items() if k in DEFAULT_REVIEW}
            data["review"] = {**DEFAULT_REVIEW, **old_review}
            if existing.get("status") == "confirmed":
                data["status"] = "confirmed"
            rest = existing["rest"] if existing["rest"].strip() != DEFAULT_REST.strip() else DEFAULT_REST
        else:
            data["review"] = dict(DEFAULT_REVIEW)
            rest = DEFAULT_REST
        front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"---\n{front}---\n{rest}")

    count = 0
    for b in nonfiction:
        title, subtitle = split_title_subtitle(b['title'])
        data = {
            "id": b['id'], "title": title, "subtitle": subtitle, "author": b['author'],
            "type": "nonfiction", "category": b['category'], "mini_theme": b['mini_theme'],
            "mini_theme_name": b['mini_theme_name'], "level": b['level'], "sequence": b['sequence'],
            "phase": b['phase'], "round": b['round'], "status": "draft", "why_chosen": b['note'],
            "connects_from": b['connects_from'], "connects_to": b['connects_to'],
            "source_lists": [], "owned": b['owned'],
        }
        cat_slug = CATEGORY_SLUGS[b['category']]
        out_dir = os.path.join(OUT_ROOT, cat_slug)
        os.makedirs(out_dir, exist_ok=True)
        write_book(os.path.join(out_dir, f"{b['id']}.md"), data)
        count += 1

    nov_count = 0
    for n in novels_sorted:
        title, subtitle = split_title_subtitle(n['title'])
        data = {
            "id": n['id'], "title": title, "subtitle": subtitle, "author": n['author'],
            "type": "fiction", "category": "Novels", "mini_theme": None, "mini_theme_name": None,
            "level": None, "sequence": n['sequence'], "phase": n['phase'], "round": n['round'],
            "status": "draft", "why_chosen": n['note'], "connects_from": n['connects_from'],
            "connects_to": n['connects_to'], "source_lists": n['source_lists'], "owned": n['owned'],
            "connects_to_nonfiction": n['connects_to_categories'],
            "connects_to_nonfiction_note": n['connects_to_categories_note'],
            "placement_note": n['placement_note'],
        }
        out_dir = os.path.join(OUT_ROOT, "novels")
        os.makedirs(out_dir, exist_ok=True)
        write_book(os.path.join(out_dir, f"{n['id']}.md"), data)
        nov_count += 1

    print(f"Wrote {count} non-fiction files, {nov_count} novel files, total {count + nov_count}")

if __name__ == '__main__':
    main()
