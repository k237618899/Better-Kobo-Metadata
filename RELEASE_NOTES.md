# Release Notes

English | [繁體中文](RELEASE_NOTES.zh-TW.md)

## v1.0.6 - Improved title normalization, structured data extraction, and CJK support

### Highlights
- Added `_normalize_digits`: normalizes Unicode/full-width digits and collapses leading zeroes in numeric tokens.
- Added `_normalize_title_for_match`: robust fuzzy title matching across CJK/western volume formatting differences (第N卷, Vol.N, etc.).
- Added `_extract_volume`: extracts base title and volume number for fair cross-format comparison.
- Improved `_volume_score`: cleaner scoring based on extracted volume and base title similarity.
- Added `_extract_series_index_from_text`: multi-locale series index parsing (CJK and western patterns).
- Added `_derive_series_from_title`: fallback series name derived from title when Kobo omits explicit series blocks.
- Added `_metadata_match_score`: re-ranks candidates using fully parsed metadata (title + series_index) instead of raw search-page snippets; eliminates volume-1/10/11 confusion.
- Added `_normalize_person_name` / `_normalized_author_set`: robust author normalization with multi-separator splitting (`,`, `、`, `/`, `&`, etc.).
- Added `_author_match_bonus` / `_author_overlap_count`: strong author-overlap tie-breaker to reduce same-title cross-author drift.
- Added `_is_manga_candidate`: tag/series/title-based manga detection for multi-author ambiguity resolution.
- Added `_candidate_volume`: unified volume extraction from both title and `series_index`.
- Added `_extract_first_regex`: generic multi-pattern regex extraction helper.
- Added `_normalize_cjk_spacing`: removes accidental spaces between CJK characters in extracted fields.
- Improved `_extract_structured_fallback`: comprehensive `ld+json` and inline JSON extraction for `publisher`, `series`, `series_index`, and `pubdate`.
- Cover search now uses a configurable candidate count (`cover_search_num_matches`) for volume-aware cover fetching.
- `identify` re-rank pipeline now applies author-overlap guard before score sort for more stable bulk results.

---

## v1.0.5 - Stable public release (volume-safe matching)

First stable public release focused on accurate manga metadata matching from Kobo.

### Highlights
- Added strict same-volume candidate filtering when query includes explicit volume.
- Improved author-aware disambiguation for same-title collisions.
- Added manga-safe tie-break behavior in ambiguous multi-author scenarios.
- Hardened publisher, series, and publication-date fallback extraction.
- Improved high-resolution cover URL normalization and cache behavior.

### Why this release
This release targets real-world bulk metadata workflows where wrong picks commonly happen with:
- Same title across manga and light novel editions.
- Volume number ambiguity, such as 1 vs 19/20.
- Kobo page structure differences causing missing fields.

### Known behavior
- If a book already has an incorrect kobo identifier, identifier lookup can still force a wrong match.
- Clear or correct identifiers before re-running metadata download.

### Package
- Plugin zip: dist/BetterKoboMetadata.zip

### Reserved assets
- Will Add before/after screenshots that show wrong-volume selection fixed in bulk matching.

---

## 1.0.4
- Added strongest author-overlap guard for same-title collisions.
- Prioritized highest author-overlap candidate group before score sorting.

## 1.0.3
- Fixed source_relevance semantics to align with calibre ordering.

## 1.0.2
- Added manga-preference tie-break for ambiguous multi-author queries.

## 1.0.1
- Added title-derived series fallback to reduce empty series values.

## 1.0.0
- Public baseline release.
- Included volume-aware matching improvements and Kobo parsing hardening.
