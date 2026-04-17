import re
import string
import time
import json
import html as html_std
import unicodedata
from queue import Queue
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode


def _normalize_digits(text: str) -> str:
    """Normalize unicode/full-width digits and collapse leading zeroes in numeric tokens."""
    text = unicodedata.normalize("NFKC", text or "")

    def _strip_leading_zeroes(match):
        num = match.group(0)
        return str(int(num)) if num.isdigit() else num

    return re.sub(r"\d+", _strip_leading_zeroes, text)


def _normalize_title_for_match(title: str) -> str:
    """Normalize title text to improve fuzzy matching across volume formatting differences."""
    t = _normalize_digits(title)

    # Remove common volume markers while keeping the number itself for extraction.
    t = re.sub(r"第\s*(\d+)\s*[卷集册冊話话巻]", r" \1 ", t, flags=re.IGNORECASE)
    t = re.sub(r"[Vv](?:ol|OLUME)?\.?\s*(\d+)", r" \1 ", t)
    t = re.sub(r"(?:卷|集|册|冊|話|话|巻|篇)", " ", t)

    # Normalize punctuation/spacing variants.
    t = t.replace("（", "(").replace("）", ")")
    t = re.sub(r"[\[\]{}()_\-:：,，.。/\\]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _extract_volume(title: str):
    """Return (normalized_base_title, volume_number | None) for common CJK/western formats."""
    normalized = _normalize_title_for_match(title)
    patterns = [
        r"(?:^|\s)(\d+)(?:\s*$)",                 # trailing number
        r"(?:^|\s)(\d+)(?:\s*(?:卷|集|册|冊|話|话|巻))",  # 1卷
        r"(?:^|\s)(?:卷|集|册|冊|話|话|巻)\s*(\d+)",      # 卷1
        r"\(\s*(\d+)\s*\)",
    ]
    volume = None
    for pat in patterns:
        m = re.search(pat, normalized, flags=re.IGNORECASE)
        if m:
            volume = int(m.group(1))
            break

    # Remove recognized volume fragments from base title for fair comparison.
    base = re.sub(r"\(\s*\d+\s*\)", " ", normalized)
    base = re.sub(r"(?:^|\s)\d+(?:\s*$)", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base, volume


def _volume_score(query_title: str, candidate_title: str) -> int:
    """Higher score = better match. Ignores volume marker variants and leading zeroes."""
    q_norm = _normalize_title_for_match(query_title)
    c_norm = _normalize_title_for_match(candidate_title)
    if q_norm == c_norm:
        return 100

    q_base, q_vol = _extract_volume(query_title)
    c_base, c_vol = _extract_volume(candidate_title)

    # Base title similarity bonus/penalty.
    base_match = (q_base and c_base and (q_base == c_base or q_base in c_base or c_base in q_base))

    if q_vol is not None and c_vol is not None:
        if q_vol == c_vol:
            return 95 if base_match else 80
        return 10 if base_match else 1

    if q_vol is None:
        return 60 if base_match else 40

    # Query has volume but candidate does not.
    return 35 if base_match else 20


def _extract_series_index_from_text(text: str):
    """Extract numeric series index from Kobo sequence text across locales."""
    if not text:
        return None
    t = _normalize_digits(text)
    patterns = [
        r"Book\s*([0-9]+(?:\.[0-9]+)?)\s*-",                       # Book 8 -
        r"第\s*([0-9]+(?:\.[0-9]+)?)\s*[卷集册冊話话巻]",             # 第8卷
        r"([0-9]+(?:\.[0-9]+)?)\s*[卷集册冊話话巻]",                 # 8卷
        r"\b([0-9]+(?:\.[0-9]+)?)\b",                              # generic fallback
    ]
    for pattern in patterns:
        m = re.search(pattern, t, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None


def _derive_series_from_title(title: str) -> Optional[str]:
    """Fallback series name from title when Kobo page omits explicit series blocks."""
    if not title:
        return None
    t = _normalize_digits(title)
    # Remove common volume notations from title.
    t = re.sub(r"[\(（]\s*\d+\s*[\)）]", " ", t)
    t = re.sub(r"第\s*\d+\s*[卷集册冊話话巻]", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"[Vv](?:ol|OLUME)?\.?\s*\d+", " ", t)
    t = re.sub(r"\s+\d+\s*$", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _metadata_match_score(query_title: str, mi: Metadata) -> int:
    """Score using fully parsed metadata (title + series_index), not just search result snippets."""
    candidate_title = getattr(mi, "title", "") or ""
    score = _volume_score(query_title, candidate_title)

    _, q_vol = _extract_volume(query_title)
    if q_vol is not None:
        series_idx = getattr(mi, "series_index", None)
        if series_idx is not None:
            try:
                si = int(float(series_idx))
                if si == int(q_vol):
                    score += 25
                else:
                    score -= 25
            except Exception:
                pass

    return score


def _normalize_person_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFKC", name)
    n = re.sub(r"\s+", "", n)
    return n.lower()


def _author_match_bonus(query_authors: Optional[List[str]], candidate_authors: Optional[List[str]]) -> int:
    """Strong tie-breaker: prefer exact/normalized author matches."""
    if not query_authors:
        return 0
    qset = {_normalize_person_name(x) for x in query_authors if x}
    cset = {_normalize_person_name(x) for x in (candidate_authors or []) if x}
    if not cset:
        return -10
    if qset.intersection(cset):
        return 60
    return -80


def _author_overlap_count(query_authors: Optional[List[str]], candidate_authors: Optional[List[str]]) -> int:
    if not query_authors or not candidate_authors:
        return 0
    qset = {_normalize_person_name(x) for x in query_authors if x}
    cset = {_normalize_person_name(x) for x in candidate_authors if x}
    return len(qset.intersection(cset))


def _is_manga_candidate(mi: Metadata) -> bool:
    tags = {str(x).lower() for x in (getattr(mi, "tags", None) or [])}
    series = str(getattr(mi, "series", "") or "").lower()
    title = str(getattr(mi, "title", "") or "").lower()
    manga_markers = ["漫畫", "图画小说", "圖畫小說", "comic", "comics", "graphic novel"]
    for marker in manga_markers:
        if any(marker in t for t in tags):
            return True
        if marker in series or marker in title:
            return True
    return False


def _candidate_volume(mi: Metadata) -> Optional[int]:
    """Get candidate volume from title first, then series_index."""
    title = getattr(mi, "title", "") or ""
    _, vol_from_title = _extract_volume(title)
    if vol_from_title is not None:
        return int(vol_from_title)
    series_idx = getattr(mi, "series_index", None)
    if series_idx is not None:
        try:
            return int(float(series_idx))
        except Exception:
            return None
    return None


def _extract_first_regex(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _normalize_cjk_spacing(text: str) -> str:
    """Remove accidental spaces between CJK characters, keep normal latin spacing."""
    if not text:
        return text
    t = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", text)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.sources.base import fixauthors
from calibre.utils.config_base import tweaks
from calibre.utils.date import parse_only_date
from calibre.utils.logging import Log
from lxml import html

import cloudscraper
import requests


class KoboMetadataImpl:
    BASE_URL = "https://www.kobo.com/"
    session: Optional[requests.Session] = None

    def __init__(self, plugin):
        self.plugin = plugin

    def _base_url(self, prefs: Dict[str, any]) -> str:
        base = prefs.get("server", self.BASE_URL) or self.BASE_URL
        if not base.endswith("/"):
            base += "/"
        return base

    def _get_unescaped_page_text(self, page: html.Element) -> str:
        page_text = html.tostring(page, encoding="unicode")
        return html_std.unescape(page_text).replace('\\"', '"')

    def _extract_structured_fallback(self, page: html.Element, log: Log) -> Dict[str, any]:
        """Extract publisher/series/series_index from ld+json or escaped inline JSON."""
        out: Dict[str, any] = {}

        scripts = page.xpath("//script[@type='application/ld+json']/text()")
        for raw in scripts:
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                publisher = node.get("publisher")
                if isinstance(publisher, dict) and not out.get("publisher"):
                    name = publisher.get("name")
                    if isinstance(name, str) and name.strip():
                        out["publisher"] = _normalize_cjk_spacing(name)

                is_part_of = node.get("isPartOf")
                if isinstance(is_part_of, dict):
                    if not out.get("series"):
                        sname = is_part_of.get("name")
                        if isinstance(sname, str) and sname.strip():
                            out["series"] = _normalize_cjk_spacing(sname)
                    if out.get("series_index") is None:
                        pos = is_part_of.get("position") or node.get("position")
                        if pos is not None:
                            try:
                                out["series_index"] = float(pos)
                            except Exception:
                                pass

                if out.get("series_index") is None and node.get("position") is not None:
                    try:
                        out["series_index"] = float(node.get("position"))
                    except Exception:
                        pass

                if not out.get("pubdate"):
                    dp = node.get("datePublished") or node.get("releaseDate")
                    if dp:
                        try:
                            out["pubdate"] = parse_only_date(str(dp))
                        except Exception:
                            pass

        text = self._get_unescaped_page_text(page)
        if not out.get("publisher"):
            out["publisher"] = _extract_first_regex(text, [
                r'"publisher"\s*:\s*\{[^{}]*"name"\s*:\s*"([^"]+)"',
                r'"publisherName"\s*:\s*"([^"]+)"',
            ])
            if out.get("publisher"):
                out["publisher"] = _normalize_cjk_spacing(out["publisher"])
        if not out.get("series"):
            out["series"] = _extract_first_regex(text, [
                r'"isPartOf"\s*:\s*\{[^{}]*"name"\s*:\s*"([^"]+)"',
                r'"series"\s*:\s*\{[^{}]*"name"\s*:\s*"([^"]+)"',
            ])
            if out.get("series"):
                out["series"] = _normalize_cjk_spacing(out["series"])
        if out.get("series_index") is None:
            idx = _extract_first_regex(text, [
                r'"isPartOf"\s*:\s*\{[^{}]*"position"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?',
                r'"position"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?',
            ])
            if idx is not None:
                try:
                    out["series_index"] = float(idx)
                except Exception:
                    pass

        if not out.get("pubdate"):
            pub = _extract_first_regex(text, [
                r'"datePublished"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"\\]+)?)"',
                r'"releaseDate"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"\\]+)?)"',
            ])
            if pub:
                try:
                    out["pubdate"] = parse_only_date(pub)
                except Exception:
                    pass

        if out:
            log.info(f"KoboMetadata::structured_fallback: {out}")
        return out

    def get_search_url(self, search_str: str, page_number: int, prefs: Dict[str, any]) -> str:
        query = {"query": search_str, "fcmedia": "Book", "pageNumber": page_number, "fclanguages": prefs["language"]}
        return f"{self._base_url(prefs)}{prefs['country']}/{prefs['language']}/search?{urlencode(query)}"
    
    def get_kobo_url(self, kobo_id: str, prefs: Dict[str, any]) -> str:
        if prefs['language'] == 'all':
            url = f"{self._base_url(prefs)}{prefs['country']}/ebook/{kobo_id}"
        else:
            url = f"{self._base_url(prefs)}{prefs['country']}/{prefs['language']}/ebook/{kobo_id}"
        return url

    def identify(
        self,
        result_queue: Queue,
        title: str,
        authors: List[str],
        identifiers: Dict[str, any],
        prefs: Dict[str, any],
        timeout: int,
        log: Log,
    ) -> None:
        log.info(f"KoboMetadata::identify: title: {title}, authors: {authors}, identifiers: {identifiers}")

        id_urls = []
        isbn = check_isbn(identifiers.get("isbn", None))
        kobo = identifiers.get("kobo", None)

        if kobo:
            log.info(f"Searching with Kobo ID: {kobo}")
            id_urls.append(self.get_kobo_url(kobo, prefs))

        if isbn:
            log.info(f"Searching with ISBN: {isbn}")
            id_urls.extend(self._perform_isbn_search(isbn, prefs["num_matches"], prefs, timeout, log))

        if id_urls:
            unique_id_urls = list(dict.fromkeys(id_urls))
            fetched_metadata = self._fetch_metadata(unique_id_urls, prefs, timeout, log)

            if fetched_metadata:
                log.info(f"Found {len(fetched_metadata)} match(es) using identifiers. Prioritizing these results.")
                for metadata in fetched_metadata:
                    result_queue.put(metadata)
                return

        # If no identifiers were provided, or they yielded no results, fall back to a general search.
        log.info("No matches found with identifiers, falling back to general search.")
        search_urls = self._perform_search(title, authors, prefs["num_matches"], prefs, timeout, log)

        if search_urls:
            unique_search_urls = list(dict.fromkeys(search_urls))
            fetched_metadata = self._fetch_metadata(unique_search_urls, prefs, timeout, log)

            if fetched_metadata:
                # Hard guard: if query has explicit volume, keep only same-volume candidates.
                _, target_vol = _extract_volume(title or "")
                if target_vol is not None:
                    same_vol = [mi for mi in fetched_metadata if _candidate_volume(mi) == int(target_vol)]
                    if same_vol:
                        fetched_metadata = same_vol
                        log.info(
                            f"KoboMetadata::identify: Filtered to same-volume candidates target={target_vol}: "
                            f"{[(x.title, _candidate_volume(x)) for x in fetched_metadata]}"
                        )

                # Re-rank with parsed metadata fields to avoid search-page ties like 1/10/11 all picking volume 1.
                if title:
                    def _final_score(mi):
                        score = _metadata_match_score(title, mi)
                        score += _author_match_bonus(authors, getattr(mi, "authors", None))

                        # If query mixes manga + LN authors, both candidates may tie on author bonus.
                        # In that ambiguous case, prefer manga-labeled candidates.
                        if authors and len([a for a in authors if a]) > 1:
                            overlap = _author_overlap_count(authors, getattr(mi, "authors", None))
                            if overlap > 0 and _is_manga_candidate(mi):
                                score += 30

                        return score

                    scored = [
                        (
                            mi,
                            _author_overlap_count(authors, getattr(mi, "authors", None)),
                            _final_score(mi),
                        )
                        for mi in fetched_metadata
                    ]

                    # Strong guard: if at least one candidate overlaps query authors,
                    # drop candidates with lower overlap (prevents LN/manga same-title drift).
                    max_overlap = max((ov for _, ov, _ in scored), default=0)
                    if authors and max_overlap > 0:
                        scored = [x for x in scored if x[1] == max_overlap]

                    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    fetched_metadata = [x[0] for x in scored]
                    log.info(
                        "KoboMetadata::identify: Re-ranked candidates by metadata score: "
                        f"{[(x.title, getattr(x, 'authors', []), ov, sc) for x, ov, sc in scored]}"
                    )
                # Calibre treats smaller source_relevance as better; assign by final order.
                for idx, metadata in enumerate(fetched_metadata):
                    metadata.source_relevance = idx
                log.info(f"Found {len(fetched_metadata)} match(es) using general search.")
                for metadata in fetched_metadata:
                    result_queue.put(metadata)

    def get_cover_url(
        self,
        title: str,
        authors: List[str],
        identifiers: Dict[str, any],
        prefs: Dict[str, any],
        timeout: int,
        log: Log,
    ) -> None:
        log.info(f"KoboMetadata::get_cover_url: title: {title}, authors: {authors}, identifiers: {identifiers}")

        # Direct kobo ID lookup — fastest and most accurate
        kobo_id = identifiers.get("kobo", None)
        if kobo_id:
            url = self.get_kobo_url(kobo_id, prefs)
            page, is_search = self._get_webpage(url, timeout, log)
            if page and not is_search:
                return self._parse_book_page_for_cover(page, prefs, log)

        urls = []
        isbn = check_isbn(identifiers.get("isbn", None))
        if isbn:
            urls.extend(self._perform_isbn_search(isbn, 1, prefs, timeout, log))

        # Fetch multiple candidates, sort by volume score, take the best match
        if not urls:
            log.info("KoboMetadata::get_cover_url: No identifier - performing volume-aware search")
            # Use configurable candidate count to find the best cover match.
            max_candidates = int(prefs.get("cover_search_num_matches", 5) or 5)
            urls.extend(self._perform_search(title, authors, max_candidates, prefs, timeout, log))

        if not urls:
            log.error("KoboMetadata::get_cover_url:: No search results")
            return

        # urls are already sorted by _volume_score inside _perform_query; take first
        url = urls[0]
        page, is_search = self._get_webpage(url, timeout, log)
        if page is None or is_search:
            log.info(f"KoboMetadata::get_cover_url: Could not get url: {url}")
            return ""

        return self._parse_book_page_for_cover(page, prefs, log)

    def get_cover(self, cover_url: str, timeout: int) -> bytes:
        session = self._get_session()
        return session.get(cover_url, timeout=timeout).content

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = cloudscraper.create_scraper(
                browser={
                    "custom": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
                },
                interpreter="v8",
                ecdhCurve="secp384r1",
            )
        return self.session

    # Returns [lxml html element, is search result]
    def _get_webpage(self, url: str, timeout: int, log: Log) -> Tuple[Optional[html.Element], bool]:
        session = self._get_session()
        try:
            attempts = 0
            max_attempts = int(self.plugin.prefs.get("cloudflare_retries", 15) or 15)
            if max_attempts < 1:
                max_attempts = 1
            while attempts < max_attempts:
                resp = session.get(url, timeout=timeout)
                page = html.fromstring(resp.text)
                # If we failed to get past the cloudflare protection, we get a page with one of these classes
                if (
                    not page.xpath("//form[@class='challenge-form']")
                    and not page.xpath("//form[@id='challenge-form']")
                    and not page.xpath("//span[@id='challenge-error-text']")
                ):
                    is_search = "/search?" in resp.url
                    return (page, is_search)
                log.info(f"KoboMetadata::get_webpage: Could not defeat cloudflare protection - trying again for {url}")
                attempts += 1
                time.sleep(1.0)
            log.error(f"KoboMetadata::get_webpage: Could not defeat cloudflare protection after {max_attempts} attempts - giving up for {url}")
            return (None, False)
        except Exception as e:
            log.error(f"KoboMetadata::get_webpage: Got exception while opening url: {e}")
            return (None, False)

    def _perform_isbn_search(
        self, isbn: int, max_matches: int, prefs: Dict[str, any], timeout: int, log: Log
    ) -> List[str]:
        isbn = check_isbn(isbn)

        if isbn:
            log.info(f"KoboMetadata::perform_isbn_search: Getting metadata with isbn: {isbn}")
            return self._perform_query(isbn, max_matches, prefs, timeout, log)

    def _perform_search(
        self, title: str, authors: List[str], max_matches: int, prefs: Dict[str, any], timeout: int, log: Log
    ) -> List[str]:
        query = self._generate_query(title, authors, prefs)
        log.info(f"KoboMetadata::perform_search: Searching with query: {query}")
        # Stash the original title so _perform_query can score candidates
        prefs['_search_title'] = title
        return self._perform_query(query, max_matches, prefs, timeout, log)

    def _fetch_metadata(self, urls: List[str], prefs: Dict[str, any], timeout: int, log: Log) -> List[Metadata]:
        results = []
        index = 0
        for url in urls:
            log.info(f"KoboMetadata::fetch_metadata: Looking up metadata with url: {url}")
            try:
                page, is_search = self._get_webpage(url, timeout, log)
                if page is None or is_search:
                    log.info(f"KoboMetadata::fetch_metadata: Could not get url: {url}")
                    return
                metadata = self._parse_book_page(page, url, prefs, log)
            except Exception as e:
                log.error(f"KoboMetadata::fetch_metadata: Got exception looking up metadata: {e}")
                return

            if metadata:
                metadata.source_relevance = 0
                results.append(metadata)
            else:
                log.info("KoboMetadata::fetch_metadata:: Could not find matching book")
            index += 1
        return results

    def _generate_query(self, title: str, authors: list[str], prefs: Dict[str, any]) -> str:
        # Remove leading zeroes from the title if configured
        # Kobo search doesn't do a great job of matching numbers
        title = " ".join(
            x.lstrip("0") if prefs["remove_leading_zeroes"] else x
            for x in self.plugin.get_title_tokens(title, strip_joiners=False, strip_subtitle=False)
        )

        if authors:
            title += " " + " ".join(self.plugin.get_author_tokens(authors))

        return title

    # Returns a list of urls that match our search, sorted by volume relevance
    def _perform_query(self, query: str, max_matches: int, prefs: Dict[str, any], timeout: int, log: Log) -> list[str]:
        url = self.get_search_url(query, 1, prefs)
        log.info(f"KoboMetadata::perform_query: Searching for book with url: {url}")

        page, is_search = self._get_webpage(url, timeout, log)
        if page is None:
            log.info(f"KoboMetadata::perform_query: Could not get url: {url}")
            return []

        # Query redirected straight to product page
        if not is_search:
            return [url]

        results = self._parse_search_page(page, log)

        page_num = 2
        # a reasonable default for how many we should try before we give up
        max_page_num = 4
        while len(results) < max_matches and page_num < max_page_num:
            url = self.get_search_url(query, page_num, prefs)
            page, is_search = self._get_webpage(url, timeout, log)
            assert page and is_search
            results.extend(self._parse_search_page(page, log))
            page_num += 1

        # Sort by volume match score so the correct volume is fetched first
        original_query = prefs.get('_search_title', query)
        if prefs.get("enable_volume_sort", True):
            results.sort(key=lambda r: _volume_score(original_query, r[1]), reverse=True)
            log.info(f"KoboMetadata::perform_query: Sorted candidates: {[(t, _volume_score(original_query, t)) for _, t in results[:max_matches]]}")
        else:
            log.info("KoboMetadata::perform_query: Volume-aware ranking disabled by settings")

        return [url for url, _ in results[:max_matches]]

    # Returns a list of (url, title) tuples from the search web page
    def _parse_search_page(self, page: html.Element, log: Log) -> List[Tuple[str, str]]:
        # Kobo seems to have partially moved to a new webpage for their search pages
        if len(page.xpath("//div[@data-testid='search-result-widget']")):
            log.info("KoboMetadata::parse_search_page: Detected new search page")
            result_elements = page.xpath("//a[@data-testid='title']")
            # Only get every second because the page includes mobile and web urls
            return [(x.get("href"), (x.text_content() or '').strip()) for x in result_elements[::2]]

        # Old
        result_elements = page.xpath("//h2[@class='title product-field']/a")
        if len(result_elements):
            log.info("KoboMetadata::parse_search_page: Detected old search page")
            return [(x.get("href"), (x.text_content() or '').strip()) for x in result_elements]

        log.error("KoboMetadata::parse_search_page: Found no matches or bad page")
        log.error(html.tostring(page))
        return []

    # Given a page that has the details of a book, parse and return the Metadata
    def _parse_book_page(self, page: html.Element, page_url: str, prefs: Dict[str, any], log: Log) -> Metadata:
        title_elements = page.xpath("//h1[@class='title product-field']")
        title = title_elements[0].text.strip()
        log.info(f"KoboMetadata::parse_book_page: Got title: {title}")

        authors_elements = page.xpath("//span[@class='visible-contributors']/a")
        authors = fixauthors([x.text for x in authors_elements])
        log.info(f"KoboMetadata::parse_book_page: Got authors: {authors}")

        metadata = Metadata(title, authors)

        series_elements = page.xpath("//span[@class='series product-field']")
        if series_elements:
            # Books in series but without an index get a nested series product-field class
            # With index: https://www.kobo.com/au/en/ebook/fourth-wing-1
            # Without index: https://www.kobo.com/au/en/ebook/les-damnees-de-la-mer-femmes-et-frontieres-en-mediterranee
            series_name_element = series_elements[-1].xpath("span[@class='product-sequence-field']/a")
            if series_name_element:
                metadata.series = series_name_element[0].text
                log.info(f"KoboMetadata::parse_book_page: Got series: {metadata.series}")

            series_index_element = series_elements[-1].xpath("span[@class='sequenced-name-prefix']")
            if series_index_element:
                seq_text = (series_index_element[0].text_content() or "").strip()
                parsed_index = _extract_series_index_from_text(seq_text)
                if parsed_index is not None:
                    metadata.series_index = parsed_index
                    log.info(f"KoboMetadata::parse_book_page: Got series_index: {metadata.series_index}")

        # Fallback/correction: derive volume from title like '(08)' / '第8卷'.
        _, title_vol = _extract_volume(title)
        if title_vol is not None:
            current = getattr(metadata, "series_index", None)
            # If missing, or if Kobo gave a suspicious default (often 1) that conflicts with title.
            if current is None or float(current) != float(title_vol):
                metadata.series_index = float(title_vol)
                log.info(
                    f"KoboMetadata::parse_book_page: Corrected series_index from title volume: {metadata.series_index}"
                )

        if not getattr(metadata, "series", None):
            fallback_series = _derive_series_from_title(title)
            if fallback_series:
                metadata.series = fallback_series
                log.info(f"KoboMetadata::parse_book_page: Derived series from title: {metadata.series}")

        book_details_elements = page.xpath("//div[contains(@class, 'bookitem-secondary-metadata')]//li")
        if book_details_elements:
            publisher_labels = {"Publisher:", "Publisher", "出版社:", "出版社", "出版者:", "出版者"}
            date_labels = {
                "Release Date:",
                "Release date:",
                "Release Date",
                "Release date",
                "出版日期:",
                "發售日期:",
                "发行日期:",
                "上市日期:",
            }
            language_labels = {"Language:", "Language", "語言:", "语言:"}
            id_labels = {"ISBN:", "Book ID:", "ISBN", "Book ID"}

            for idx, x in enumerate(book_details_elements):
                descriptor = (x.xpath("normalize-space(text()[1])") or "").strip()
                span_nodes = x.xpath("span")
                value = (span_nodes[0].text_content() if span_nodes else x.text_content() or "").strip()
                if descriptor and value.startswith(descriptor):
                    value = value[len(descriptor):].strip()

                if descriptor in publisher_labels and value:
                    metadata.publisher = value
                    log.info(f"KoboMetadata::parse_book_page: Got publisher: {metadata.publisher}")
                    continue
                if idx == 0 and not getattr(metadata, "publisher", None) and value:
                    metadata.publisher = value
                    log.info(f"KoboMetadata::parse_book_page: Got publisher (first detail): {metadata.publisher}")
                    continue

                if descriptor in date_labels and value:
                    try:
                        metadata.pubdate = parse_only_date(value)
                        log.info(f"KoboMetadata::parse_book_page: Got pubdate: {metadata.pubdate}")
                    except Exception as e:
                        log.info(f"KoboMetadata::parse_book_page: Could not parse pubdate '{value}': {e}")
                elif descriptor in id_labels and value:
                    metadata.isbn = value
                    log.info(f"KoboMetadata::parse_book_page: Got isbn: {metadata.isbn}")
                elif descriptor in language_labels and value:
                    metadata.language = value
                    log.info(f"KoboMetadata::parse_book_page: Got language: {metadata.language}")

        # Structured fallback for pages with changed DOM (common in bulk and some volume-1 pages).
        structured = self._extract_structured_fallback(page, log)
        if not getattr(metadata, "publisher", None) and structured.get("publisher"):
            metadata.publisher = structured["publisher"]
            log.info(f"KoboMetadata::parse_book_page: Got publisher from structured data: {metadata.publisher}")
        if not getattr(metadata, "series", None) and structured.get("series"):
            metadata.series = structured["series"]
            log.info(f"KoboMetadata::parse_book_page: Got series from structured data: {metadata.series}")
        if getattr(metadata, "series_index", None) is None and structured.get("series_index") is not None:
            metadata.series_index = structured["series_index"]
            log.info(f"KoboMetadata::parse_book_page: Got series_index from structured data: {metadata.series_index}")
        if not getattr(metadata, "pubdate", None) and structured.get("pubdate") is not None:
            metadata.pubdate = structured["pubdate"]
            log.info(f"KoboMetadata::parse_book_page: Got pubdate from structured data: {metadata.pubdate}")

        # Fallback: Kobo pages often expose datePublished in JSON-LD.
        if not getattr(metadata, "pubdate", None):
            pubdate = self._extract_pubdate_from_jsonld(page, log)
            if pubdate:
                metadata.pubdate = pubdate
                log.info(f"KoboMetadata::parse_book_page: Got pubdate from JSON-LD: {metadata.pubdate}")

        tags_elements = page.xpath("//ul[@class='category-rankings']/meta[@property='genre']")
        if tags_elements:
            # Calibre doesnt like commas in tags
            metadata.tags = {x.get("content").replace(", ", " ") for x in tags_elements}
            log.info(f"KoboMetadata::parse_book_page: Got tags: {metadata.tags}")

        synopsis_elements = page.xpath("//div[@data-full-synopsis='']")
        if synopsis_elements:
            metadata.comments = "".join(
                html.tostring(child, encoding="unicode") 
                for child in synopsis_elements[0]
            )
            log.info(f"KoboMetadata::parse_book_page: Got comments: {metadata.comments}")

        # Kobo pages can omit ISBN/Book ID in some locales; extract the canonical kobo id from URL.
        kobo_id = None
        kobo_id_match = re.search(r"/ebook/([^/?#]+)", page_url)
        if kobo_id_match:
            kobo_id = kobo_id_match.group(1)
            metadata.set_identifier("kobo", kobo_id)
            log.info(f"KoboMetadata::parse_book_page: Got kobo id: {kobo_id}")

        cover_url = self._parse_book_page_for_cover(page, prefs, log)
        if cover_url:
            # Prefer kobo identifier as cache key (manga from Taiwan often has no ISBN)
            cache_key = kobo_id or metadata.get_identifiers().get("kobo") or metadata.isbn
            if cache_key:
                self.plugin.cache_identifier_to_cover_url(cache_key, cover_url)
                log.info(f"KoboMetadata::parse_book_page: Cached cover for key: {cache_key}")

        blacklisted_title = self._check_title_blacklist(title, prefs, log)
        if blacklisted_title:
            log.info(f"KoboMetadata::parse_book_page: Hit blacklisted word(s) in the title: {blacklisted_title}")
            return None

        blacklisted_tags = self._check_tag_blacklist(metadata.tags, prefs, log)
        if blacklisted_tags:
            log.info(f"KoboMetadata::parse_book_page: Hit blacklisted tag(s): {blacklisted_tags}")
            return None

        return metadata

    def _extract_pubdate_from_jsonld(self, page: html.Element, log: Log):
        scripts = page.xpath("//script[@type='application/ld+json']/text()")
        for raw in scripts:
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                value = node.get("datePublished") or node.get("releaseDate")
                if not value:
                    continue
                try:
                    return parse_only_date(str(value))
                except Exception as e:
                    log.info(f"KoboMetadata::extract_pubdate_from_jsonld: Could not parse '{value}': {e}")

        # Fallback: Kobo sometimes embeds schema fields in escaped JSON blocks, not ld+json scripts.
        # Example snippet contains: \&quot;datePublished\&quot;: \&quot;2017-06-02T00:00:00Z\&quot;
        page_text = html.tostring(page, encoding="unicode")
        unescaped_text = html_std.unescape(page_text)
        unescaped_text = unescaped_text.replace('\\"', '"')

        patterns = [
            r'"datePublished"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"\\]+)?)"',
            r'"releaseDate"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"\\]+)?)"',
            r'"datePublished"\s*:\s*"([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})"',
            r'"releaseDate"\s*:\s*"([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})"',
        ]
        for pattern in patterns:
            m = re.search(pattern, unescaped_text, re.IGNORECASE)
            if not m:
                continue
            value = m.group(1)
            try:
                return parse_only_date(value)
            except Exception as e:
                log.info(f"KoboMetadata::extract_pubdate_from_jsonld: Could not parse fallback '{value}': {e}")
        return None

    def _parse_book_page_for_cover(self, page: html.Element, prefs: Dict[str, any], log: Log) -> str:
        cover_elements = page.xpath("//img[contains(@class, 'cover-image')]")
        cover_url = ""
        if cover_elements:
            # Sample: https://cdn.kobo.com/book-images/44f0e8b9-3338-4d1c-bd6e-e88e82cb8fad/353/569/90/False/holly-23.jpg
            src = cover_elements[0].get("src") or cover_elements[0].get("data-src") or ""
            if src.startswith("https://"):
                cover_url = src
            elif src.startswith("//"):
                cover_url = "https:" + src
            elif src.startswith("/"):
                cover_url = "https://www.kobo.com" + src
            else:
                cover_url = src
            if prefs["resize_cover"]:
                # Request higher resolution regardless of the size currently in the URL.
                width, height = tweaks["maximum_cover_size"]
                # Common Kobo format: /<w>/<h>/<quality>/False/<slug>.jpg
                new_segment = f"/{width}/{height}/100/False/"
                cover_url, replaced = re.subn(r"/\d+/\d+/\d+/(?:False|True)/", new_segment, cover_url, count=1)
                if replaced == 0:
                    # Fallback format: /<w>/<h>/<quality>/<slug>.jpg
                    cover_url = re.sub(r"/\d+/\d+/\d+/", f"/{width}/{height}/100/", cover_url, count=1)
            else:
                # Remove resizing segment and use original CDN asset path.
                cover_url = re.sub(r"/\d+/\d+/\d+/(?:False|True)/", "/", cover_url, count=1)

        log.info(f"KoboMetadata::parse_book_page_for_cover: Got cover: {cover_url}")
        return cover_url

    # Returns the set of words in the title that are also blacklisted
    def _check_title_blacklist(self, title: str, prefs: Dict[str, any], log: Log) -> set[str]:
        if not prefs["title_blacklist"]:
            return None

        blacklisted_words = {x.strip().lower() for x in prefs["title_blacklist"].split(",")}
        log.info(f"KoboMetadata::_check_title_blacklist: blacklisted title words: {blacklisted_words}")
        # Remove punctuation from title string
        title_str = title.translate(str.maketrans("", "", string.punctuation))
        return blacklisted_words.intersection(title_str.lower().split(" "))

    # Returns the set of tags that are also blacklisted
    def _check_tag_blacklist(self, tags: set[str], prefs: Dict[str, any], log: Log) -> set[str]:
        if not prefs["tag_blacklist"]:
            return None

        blacklisted_tags = {x.strip().lower() for x in prefs["tag_blacklist"].split(",")}
        log.info(f"KoboMetadata::_check_tag_blacklist: blacklisted tags: {blacklisted_tags}")
        return blacklisted_tags.intersection({x.lower() for x in tags})
