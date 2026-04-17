# Better Kobo Metadata

Better Kobo Metadata is a calibre metadata source plugin focused on reliable manga volume matching for Kobo results.

## Highlights
- Volume-aware matching to avoid picking wrong volumes such as `1` vs `19`/`20`.
- Author-aware disambiguation for same-title collisions.
- Manga/light novel tie-break handling for ambiguous search results.
- Improved publisher/series/pubdate fallback extraction from Kobo pages.
- Higher-resolution cover URL normalization and caching fixes.

## Requirements
- calibre 5.0+

## Project Layout
- `__init__.py`: plugin entry and calibre option definitions
- `kobo_metadata.py`: search, ranking, metadata parsing, and cover logic
- `plugin-import-name-kobo_metadata.txt`: plugin import name for calibre
- `scripts/build.sh`: package build script
- `dist/`: generated plugin package output
- `logs/`: local debugging logs (ignored by git)

## Build
Run from repository root:

```bash
bash scripts/build.sh
```

Generated package:
- `dist/BetterKoboMetadata.zip`

## Install

```bash
/opt/calibre/calibre-customize -a dist/BetterKoboMetadata.zip
```

Or in calibre GUI:
- Preferences -> Plugins -> Load plugin from file

## Recommended Usage
- Prefer enabling only Better Kobo Metadata while validating matching quality.
- If a record already has a wrong `kobo:` identifier, clear it before re-downloading metadata.

## Troubleshooting
- If matching picks a wrong book, attach the relevant section from `logs/identify.log` or calibre identify log.
- Include query title, authors, identifiers, and expected vs actual match.

## Open Source Dependencies
- cloudscraper (MIT)
- requests (Apache-2.0)
- urllib3 (MIT)
- idna (BSD-3-Clause)

## License
See `LICENSE`.
