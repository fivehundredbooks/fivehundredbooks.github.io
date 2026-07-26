---
title: "Built With Claude: The Weekend Behind the 500 Books Challenge"
description: "How the curriculum, the reading order, the site, and the progress tracker actually got built this weekend — and how much of it was Claude, not me."
pubDate: 2026-07-26
---

I'm Jez, and this weekend I built the entire backbone of the 500 Books Challenge with Claude. Not "used an AI tool to help." Built with — I made the calls, Claude did almost all of the actual work, and I want to be upfront about that rather than quietly taking credit for code and research I didn't personally type.

Here's what that looked like in practice. I gave Claude the mission and the rules: 500 books, 10-20 years, no shortcuts, no single "best of" list treated as gospel. From there, Claude cross-referenced 538 novel candidates across nine respected lists — BBC, Guardian, Modern Library, Le Monde, TIME, and more — down to a curated 125, then did the same for 375 non-fiction books across 15 categories, using Tom Butler-Bowdon's classics collections as one gatekeeper among several, never the sole authority. Every category got split into five mini-themes of five books, and every book got a level from 0 to 10, so the whole thing reads like a syllabus instead of a pile.

Then came the hard part: sequencing all 500 into a single reading order, round-robin across all 15 categories plus interleaved novels, so a book about a war leads into the military history behind it, which leads into the economics of the peace after. Four phases, verified programmatically so nothing got dropped or duplicated.

Claude also cross-referenced my actual library — 2,179 books across Kindle, Audible, and physical shelves — against the curriculum, purely so the site can flag what I already own, never to bias which books made the cut.

Then it built the website you're reading this on. Astro, GitHub Pages, one data file per book, category pages, the full reading order, a library browser, dark mode, the whole thing. Today we added the piece I actually asked for: a proper way to log progress. Not just a checkbox, but started_on and finished_on dates per book, so ten years from now I can look back and see not just what I read, but when, and a running Reading Log page with room for a one-line takeaway on anything I finish.

I also had Claude write a checklist for adding new books later — cross-reference sources, test against significance/influence/practical value, check where it fits in the reading order — so future additions follow the same rules as everything already here, not vibes. And a weekly Sunday nudge, so logging progress doesn't quietly stop being a habit in month three.

None of this replaces the actual point of the project, which is reading. I haven't finished a single book yet — the counter genuinely reads zero. What this weekend bought me is infrastructure: a curriculum I trust was built on real cross-referencing rather than one list I liked, an order that builds on itself instead of jumping randomly between subjects, and a way to actually see the decade unfold instead of losing track of it.

The reading starts now. I'll post again once there's something real to report.
