from calibre.ebooks.metadata.sources.base import Option, Source


class KoboMetadata(Source):
    name = "Better Kobo Metadata"
    author = "Jacob Hsu"
    version = (1, 0, 7)
    minimum_calibre_version = (5, 0, 0)
    description = _("Downloads metadata and covers from Kobo with accurate volume/series matching")

    capabilities = frozenset(("identify", "cover"))
    touched_fields = frozenset(
        (
            "title",
            "authors",
            "comments",
            "publisher",
            "pubdate",
            "languages",
            "series",
            "tags",
            "rating",
        )
    )
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    COUNTRIES = {
        "ca": _("Canada"),
        "us": _("United States"),
        "in": _("India"),
        "za": _("South Africa"),
        "au": _("Australia"),
        "hk": _("Hong Kong"),
        "jp": _("Japan"),
        "my": _("Malaysia"),
        "nz": _("New Zealand"),
        "ph": _("Phillipines"),
        "sg": _("Singapore"),
        "tw": _("Taiwan"),
        "th": _("Thailand"),
        "at": _("Austria"),
        "be": _("Belgium"),
        "cy": _("Cyprus"),
        "cz": _("Czech Republic"),
        "dk": _("Denmark"),
        "ee": _("Estonia"),
        "fi": _("Finland"),
        "fr": _("France"),
        "de": _("Germany"),
        "gr": _("Greece"),
        "ie": _("Ireland"),
        "it": _("Italy"),
        "lt": _("Lithuania"),
        "lu": _("Luxemburg"),
        "mt": _("Malta"),
        "nl": _("Netherlands"),
        "no": _("Norway"),
        "pl": _("Poland"),
        "pt": _("Portugal"),
        "ro": _("Romania"),
        "sk": _("Slovak Republic"),
        "si": _("Slovenia"),
        "es": _("Spain"),
        "se": _("Sweden"),
        "ch": _("Switzerland"),
        "tr": _("Turkey"),
        "gb": _("United Kingdom"),
        "br": _("Brazil"),
        "mx": _("Mexico"),
        "ww": _("Other"),
    }

    options = (
        Option(
            "country",
            "choices",
            "tw",
            _("Kobo country store to use"),
            _("Metadata from Kobo will be fetched from this store"),
            choices=COUNTRIES,
        ),
        Option("language", "string", "zh", _("2 Letter language code to search for"), _("Default: zh for Taiwan store")),
        Option(
            "num_matches",
            "number",
            5,
            _("Number of matches to fetch"),
            _(
                "How many possible matches to fetch metadata for. If applying metadata in bulk, "
                "there is no use setting this above 1. Otherwise, set this higher if you are "
                "having trouble matching a specific book."
            ),
        ),
        Option(
            "title_blacklist",
            "string",
            "",
            _("Blacklist words in the title"),
            _("Comma separated words to blacklist"),
        ),
        Option(
            "tag_blacklist",
            "string",
            "",
            _("Blacklist tags"),
            _("Comma separated tags to blacklist"),
        ),
        Option(
            "remove_leading_zeroes",
            "bool",
            False,
            _("Remove leading zeroes"),
            _("Remove leading zeroes from numbers in the title"),
        ),
        Option(
            "resize_cover",
            "bool",
            True,
            _("Resize cover"),
            _("Resize the cover to the maximum_cover_size tweak setting"),
        ),
        Option(
            "enable_volume_sort",
            "bool",
            True,
            _("Enable volume-aware ranking"),
            _("Prioritize candidates with the same volume number as the query title"),
        ),
        Option(
            "cover_search_num_matches",
            "number",
            5,
            _("Cover search candidate count"),
            _("How many candidates are checked when searching for a cover without identifiers"),
        ),
        Option(
            "cloudflare_retries",
            "number",
            15,
            _("Cloudflare retry attempts"),
            _("Maximum number of retries when Kobo challenge pages are encountered"),
        ),
    )

    _impl = None

    def __init__(self, *args, **kwargs):
        Source.__init__(self, *args, **kwargs)
        with self:
            from .kobo_metadata import KoboMetadataImpl

            self._impl = KoboMetadataImpl(self)

    def get_book_url(self, identifiers):
        isbn = identifiers.get("isbn", None)
        kobo = identifiers.get("kobo", None)

        if kobo:
            return ("kobo", kobo, self._impl.get_kobo_url(kobo, self.prefs))

        if isbn:
            # Example output:"https://www.kobo.com/au/en/search?query=9781761108105"
            return ("isbn", isbn, self._impl.get_search_url(isbn, 1, self.prefs))
        return None

    def get_cached_cover_url(self, identifiers):
        # Prefer kobo identifier as cache key (manga often has no ISBN)
        kobo = identifiers.get("kobo", None)
        if kobo is not None:
            url = self.cached_identifier_to_cover_url(kobo)
            if url:
                return url

        isbn = identifiers.get("isbn", None)
        if isbn is not None:
            return self.cached_identifier_to_cover_url(isbn)

        return None

    def identify(
        self,
        log,
        result_queue,
        abort,
        title=None,
        authors=None,
        identifiers={},
        timeout=30,
    ) -> None:
        self._impl.identify(result_queue, title, authors, identifiers, self.prefs, timeout, log)

    def download_cover(
        self,
        log,
        result_queue,
        abort,
        title=None,
        authors=None,
        identifiers={},
        timeout=30,
        get_best_cover=False,
    ) -> None:
        cover_url = self.get_cached_cover_url(identifiers)
        if not cover_url:
            log.info("KoboMetadata::download_cover: No cached url found, running identify")
            cover_url = self._impl.get_cover_url(title, authors, identifiers, self.prefs, timeout, log)

        # If we still dont have the cover, its over
        if not cover_url:
            log.error("KoboMetadata::download_cover: Could not get cover")
            return

        try:
            cover = self._impl.get_cover(cover_url, timeout)
            result_queue.put((self, cover))
        except Exception as e:
            log.error(f"KoboMetadata::download_cover: Got exception while opening cover url: {e}")
            return
