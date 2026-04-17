# Better Kobo Metadata

English | [繁體中文](README.zh-TW.md)

Better Kobo Metadata is a calibre metadata source plugin focused on reliable manga volume matching for Kobo results.

## Highlights
- Volume-aware matching to avoid wrong picks such as `1` vs `19`/`20`.
- Author-aware disambiguation for same-title collisions.
- Manga vs light novel tie-break handling for ambiguous results.
- Stronger fallback extraction for `publisher`, `series`, and `pubdate`.
- Improved high-resolution cover URL normalization and cover cache behavior.

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
See [LICENSE](LICENSE).
