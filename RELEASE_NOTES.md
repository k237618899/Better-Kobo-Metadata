# Release Notes

## 1.0.5
- Added strict same-volume candidate filtering when query includes explicit volume.
- Prevented wrong-volume picks caused by downstream result ordering.

## 1.0.4
- Added strongest author-overlap guard for same-title collisions.
- Prioritized highest author-overlap candidate group before score sorting.

## 1.0.3
- Fixed `source_relevance` semantics to align with calibre ordering.

## 1.0.2
- Added manga-preference tie-break for ambiguous multi-author queries.

## 1.0.1
- Added title-derived series fallback to reduce empty `series` values.

## 1.0.0
- Public baseline release.
- Included volume-aware matching improvements and Kobo parsing hardening.
