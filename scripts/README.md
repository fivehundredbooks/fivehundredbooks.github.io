# Scripts

- `consolidate_libraries.py` — dedupes and merges the Kindle/Audible/Physical
  library exports into `data/ownership.csv`, tagging each book with which
  format(s) it's owned in. Source CSVs are exported from LibraryThing,
  Amazon's Kindle library page, and Audible's library page, and currently
  live outside this repo in the working project folder — update the
  `SRC_DIR` path at the top of the script to point at them, then rerun.
