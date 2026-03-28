"""
Data source collectors for the Financial Market Economist Agent.
Handles RSS feed parsing, web search API calls, and FRED data retrieval.
"""

import os
import json
import datetime
import logging
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
import trafilatura

logger = logging.getLogger("agent.sources")


@dataclass
class Article:
    """Represents a collected article or data point."""
    title: str
    source: str
    url: str
    published: str
    summary: str
    full_text: str = ""
    category: str = ""  # e.g., "central_bank", "research", "journalism", "data"

    @property
    def id(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()[:12]


@dataclass
class FREDSeries:
    """Represents a FRED data series with recent observations."""
    series_id: str
    name: str
    observations: list = field(default_factory=list)  # [{date, value}, ...]
    units: str = ""
    frequency: str = ""
    last_updated: str = ""


# ---------------------------------------------------------------------------
#  RSS Collector
# ---------------------------------------------------------------------------
class RSSCollector:
    """Collects and parses articles from curated RSS feeds."""

    def __init__(self, feeds: dict, lookback_days: int = 7):
        self.feeds = feeds
        self.cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=lookback_days)

    def collect(self) -> list[Article]:
        articles = []
        for source_name, feed_url in self.feeds.items():
            try:
                items = self._parse_feed(source_name, feed_url)
                articles.extend(items)
            except Exception as e:
                logger.warning(f"Failed to parse RSS feed '{source_name}': {e}")
        # Deduplicate by URL
        seen = set()
        unique = []
        for a in articles:
            if a.url not in seen:
                seen.add(a.url)
                unique.append(a)
        logger.info(f"RSS collected {len(unique)} unique articles from {len(self.feeds)} feeds")
        return unique

    def _parse_feed(self, source_name: str, feed_url: str) -> list[Article]:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:15]:  # Cap per feed
            pub_date = self._parse_date(entry)
            if pub_date and pub_date < self.cutoff:
                continue
            summary = entry.get("summary", entry.get("description", ""))
            # Clean HTML from summary
            if summary:
                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)[:500]

            url = entry.get("link", "")
            full_text = self._extract_full_text(url)

            items.append(Article(
                title=entry.get("title", "Untitled"),
                source=source_name,
                url=url,
                published=pub_date.isoformat() if pub_date else "",
                summary=summary,
                full_text=full_text[:3000],  # Cap to manage token budget
                category=self._categorize_source(source_name),
            ))
        return items

    def _extract_full_text(self, url: str) -> str:
        """Attempt to extract clean article text from URL."""
        if not url:
            return ""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, include_comments=False)
                return text or ""
        except Exception:
            pass
        return ""

    def _parse_date(self, entry) -> Optional[datetime.datetime]:
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if parsed:
                try:
                    return datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
                except Exception:
                    pass
        return None

    def _categorize_source(self, name: str) -> str:
        name_lower = name.lower()
        if any(k in name_lower for k in ("fed", "ecb", "boe", "bank of", "bis", "imf", "treasury", "bls", "bea", "census")):
            return "official"
        if any(k in name_lower for k in ("reuters", "ft", "wsj", "bloomberg", "cnbc")):
            return "journalism"
        return "research"


# ---------------------------------------------------------------------------
#  Web Search Collector (using Tavily or fallback)
# ---------------------------------------------------------------------------
class WebSearchCollector:
    """Searches for breaking/trending market topics via search API."""

    def __init__(self, topics: list[str]):
        self.topics = topics
        self.api_key = os.environ.get("TAVILY_API_KEY", "")
        self.serp_api_key = os.environ.get("SERP_API_KEY", "")

    def collect(self) -> list[Article]:
        articles = []
        for topic in self.topics:
            try:
                results = self._search(topic)
                articles.extend(results)
                time.sleep(0.5)  # Rate-limit courtesy
            except Exception as e:
                logger.warning(f"Search failed for '{topic}': {e}")

        # Deduplicate
        seen = set()
        unique = []
        for a in articles:
            if a.url not in seen:
                seen.add(a.url)
                unique.append(a)
        return unique

    def _search(self, query: str) -> list[Article]:
        """Try Tavily first, then SerpAPI, then skip."""
        if self.api_key:
            return self._search_tavily(query)
        elif self.serp_api_key:
            return self._search_serp(query)
        else:
            logger.warning("No search API key configured — skipping web search")
            return []

    def _search_tavily(self, query: str) -> list[Article]:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 5,
                "include_raw_content": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for r in data.get("results", []):
            articles.append(Article(
                title=r.get("title", ""),
                source="Web Search",
                url=r.get("url", ""),
                published="",
                summary=r.get("content", "")[:500],
                full_text=(r.get("raw_content") or "")[:3000],
                category="search",
            ))
        return articles

    def _search_serp(self, query: str) -> list[Article]:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": self.serp_api_key,
                "engine": "google",
                "num": 5,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for r in data.get("organic_results", []):
            articles.append(Article(
                title=r.get("title", ""),
                source="Web Search",
                url=r.get("link", ""),
                published=r.get("date", ""),
                summary=r.get("snippet", ""),
                full_text="",
                category="search",
            ))
        return articles


# ---------------------------------------------------------------------------
#  FRED Data Collector
# ---------------------------------------------------------------------------
class FREDDataCollector:
    """Fetches economic data series from the FRED API."""

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, series: dict, lookback_days: int = 90):
        self.series = series
        self.api_key = os.environ.get("FRED_API_KEY", "")
        self.lookback_days = lookback_days

    def collect(self) -> list[FREDSeries]:
        if not self.api_key:
            logger.warning("No FRED_API_KEY — skipping FRED data collection")
            return []

        end_date = datetime.date.today()
        # Use longer lookback for less-frequent series
        start_date = end_date - datetime.timedelta(days=max(self.lookback_days, 365))

        results = []
        for series_id, name in self.series.items():
            try:
                data = self._fetch_series(series_id, start_date, end_date)
                if data:
                    results.append(data)
                time.sleep(0.2)  # Rate-limit
            except Exception as e:
                logger.warning(f"FRED fetch failed for {series_id}: {e}")

        return results

    def _fetch_series(self, series_id: str, start: datetime.date, end: datetime.date) -> Optional[FREDSeries]:
        # Get series info
        info_resp = requests.get(
            f"{self.BASE_URL}/series",
            params={
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
            },
            timeout=15,
        )
        info_resp.raise_for_status()
        info = info_resp.json().get("seriess", [{}])[0]

        # Get observations
        obs_resp = requests.get(
            f"{self.BASE_URL}/series/observations",
            params={
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start.isoformat(),
                "observation_end": end.isoformat(),
                "sort_order": "desc",
            },
            timeout=15,
        )
        obs_resp.raise_for_status()
        raw_obs = obs_resp.json().get("observations", [])

        observations = []
        for o in raw_obs:
            val = o.get("value", ".")
            if val != ".":
                observations.append({
                    "date": o["date"],
                    "value": float(val),
                })

        return FREDSeries(
            series_id=series_id,
            name=self.series.get(series_id, series_id),
            observations=observations[:90],  # Keep recent
            units=info.get("units", ""),
            frequency=info.get("frequency", ""),
            last_updated=info.get("last_updated", ""),
        )
