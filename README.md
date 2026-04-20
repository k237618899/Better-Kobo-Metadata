# Better Kobo Metadata

English | [繁體中文](README.zh-TW.md)

Better Kobo Metadata is a calibre metadata source plugin focused on reliable manga volume matching for Kobo results.

## Highlights
- Volume-aware matching: normalized CJK/western volume formats (第N卷, Vol.N, leading zeroes) to avoid wrong picks such as `1` vs `19`/`20`.
- Metadata-based re-ranking: scores candidates using fully parsed title and `series_index`, not just search-page snippets.
- Author-aware disambiguation: normalized multi-separator author matching with strong overlap tie-breaking.
- Manga vs light novel tie-break: tag/series/title-based manga detection for ambiguous multi-author results.
- Stronger fallback extraction: `ld+json` and inline JSON structured data for `publisher`, `series`, `series_index`, and `pubdate`.
- Series derivation from title: fallback series name when Kobo omits explicit series blocks.
- CJK spacing normalization: removes accidental spaces between CJK characters in extracted fields.
- Configurable cover candidate count for volume-aware cover fetching.

## Requirements
- calibre 5.0+

## Project Layout
- `__init__.py`: plugin entry and calibre options
- `kobo_metadata.py`: search, ranking, parsing, and cover logic
- `plugin-import-name-kobo_metadata.txt`: calibre plugin import name marker
- `scripts/build.sh`: package build script
- `dist/`: packaged plugin output
- `logs/`: local debug logs (gitignored)

## Build
Run from repository root:

```bash
bash scripts/build.sh
```

Output package:
- `dist/BetterKoboMetadata.zip`

## Install

```bash
/opt/calibre/calibre-customize -a dist/BetterKoboMetadata.zip
```

Or via calibre GUI:
- Preferences -> Plugins -> Load plugin from file

## Recommended Usage
- During validation, enable only Better Kobo Metadata to avoid source-merging noise.
- If a record already has a wrong `kobo:` identifier, clear it before re-downloading metadata.

## Troubleshooting
- If matching picks a wrong book, attach the relevant identify log segment.
- Include query title, authors, identifiers, expected result, and actual result.

## Open Source Dependencies
- cloudscraper (MIT)
- requests (Apache-2.0)
- urllib3 (MIT)
- idna (BSD-3-Clause)

## License
See `LICENSE`.
