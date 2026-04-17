# Contributing

Thanks for contributing.

## Development Flow
1. Make changes in `kobo_metadata.py` and/or `__init__.py`.
2. Build package:
   - `bash scripts/build.sh`
3. Install package locally:
   - `/opt/calibre/calibre-customize -a dist/BetterKoboMetadata.zip`
4. Validate with calibre identify logs.

## Bug Reports
Please include:
- Query title/authors/identifiers
- Relevant identify log section
- Expected result vs actual result

## Notes
- Keep matching logic deterministic and explainable.
- Prefer small, focused changes.
- Avoid breaking existing calibre option names when possible.
