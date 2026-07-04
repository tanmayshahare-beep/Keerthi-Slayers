"""Retail-relevant news via Google News RSS - free, no API key required.

https://news.google.com/rss/search?q=<query> returns a standard RSS feed for
any search query. This is the same mechanism news.google.com's own search box
uses; no key, quota, or account is needed.
"""

import time
import xml.etree.ElementTree as ET

import requests

RSS_URL = "https://news.google.com/rss/search"
REQUEST_TIMEOUT = 8
CACHE_TTL_SECONDS = 15 * 60
MAX_ITEMS = 12

# Google News RSS wants a locale even for an English query; querying with the
# right country surfaces more locally-relevant results than a bare query.
_LOCALES = {
    "US": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "IN": {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
}

_cache: dict[str, tuple[float, list[dict]]] = {}


def _query_for_location(location: str, label: str | None) -> tuple[str, str]:
    """Returns (search query, locale key) for a given location value."""
    if location == "main":
        return "grocery retail industry news", "US"
    if location == "all":
        return "Tamil Nadu retail industry news", "IN"
    if label:
        return f"{label} retail business news", "IN"
    return "retail industry news", "IN"


def _parse_rss(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    articles = []
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        source_el = item.find("source")
        articles.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
            "source": (source_el.text or "").strip() if source_el is not None else "",
        })
    return articles


def fetch_news(location: str, label: str | None = None) -> dict:
    """Returns {"query": str, "articles": [...]}. Never raises - a network
    failure or empty result just yields an empty article list so the UI can
    show a clear "no news right now" state instead of crashing the page."""
    query, locale_key = _query_for_location(location, label)

    cached = _cache.get(query)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return {"query": query, "articles": cached[1]}

    params = {"q": query, **_LOCALES[locale_key]}
    try:
        resp = requests.get(
            RSS_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AROS-Retail-Insights/1.0)"},
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"  # requests sometimes mis-detects this feed's encoding, mangling smart quotes
        articles = _parse_rss(resp.text)
    except (requests.RequestException, ET.ParseError):
        articles = []

    _cache[query] = (time.time(), articles)
    return {"query": query, "articles": articles}
