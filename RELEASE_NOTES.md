# Release Notes

English | [繁體中文](RELEASE_NOTES.zh-TW.md)

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
