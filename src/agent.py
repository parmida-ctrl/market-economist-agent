"""
Financial Market Economist Research Agent
=========================================
A weekly research pipeline that:
1. Pulls RSS feeds from curated financial sources
2. Searches for breaking/trending market topics
3. Fetches FRED economic data series
4. Synthesizes findings via Claude API
5. Generates an HTML report with charts
6. Emails the report
"""

import os
import json
import logging
import datetime
from pathlib import Path

from sources import RSSCollector, WebSearchCollector, FREDDataCollector
from synthesizer import ReportSynthesizer
from report_builder import ReportBuilder
from email_report_builder import EmailReportBuilder
from charts import render_fred_charts
from emailer import ReportEmailer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agent")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# RSS feeds – curated for macro / markets / central-bank coverage
RSS_FEEDS = {
    # --- Central Banks & Official Sources ---
    "Federal Reserve":          "https://www.federalreserve.gov/feeds/press_all.xml",
    "Fed Speeches":             "https://www.federalreserve.gov/feeds/speeches.xml",
    "ECB Press":                "https://www.ecb.europa.eu/rss/press.html",
    "Bank of England":          "https://www.bankofengland.co.uk/rss/news",
    "BIS Research":             "https://www.bis.org/doclist/bis_fsi_publs.rss",
    "IMF Blog":                 "https://www.imf.org/en/Blogs/rss",
    "IMF Working Papers":       "https://www.imf.org/en/Publications/RSS?type=WP",

    # --- Government / Data Releases ---
    "US Treasury":              "https://home.treasury.gov/system/files/136/treasury-rss.xml",
    "BLS Press Releases":       "https://www.bls.gov/feed/bls_latest.rss",
    "BEA News":                 "https://www.bea.gov/rss/rss.xml",
    "Census Economic Indicators": "https://www.census.gov/economic-indicators/indicator.xml",

    # --- Financial Journalism ---
    "Reuters Business":         "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "FT Markets":               "https://www.ft.com/markets?format=rss",
    "WSJ Markets":              "https://feeds.a]wsj.com/wsj/xml/rss/3_7031.xml",
    "Bloomberg Markets":        "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC Economy":             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",

    # --- Research & Analysis ---
    "Brookings Economics":      "https://www.brookings.edu/topic/economy/feed/",
    "NBER New Papers":          "https://www.nber.org/rss/new.xml",
    "PIIE":                     "https://www.piie.com/rss.xml",
    "VoxEU / CEPR":             "https://cepr.org/rss/columns",
    "St. Louis Fed (FRED Blog)":"https://fredblog.stlouisfed.org/feed/",
    "NY Fed Liberty Street":    "https://libertystreeteconomics.newyorkfed.org/feed/",
    "SF Fed Economic Letters":  "https://www.frbsf.org/research-and-insights/publications/economic-letter/feed/",
    "Atlanta Fed macroblog":    "https://www.atlantafed.org/rss/macroblog",
    "Dallas Fed":               "https://www.dallasfed.org/rss/ecod.aspx",
    "Chicago Fed":              "https://www.chicagofed.org/rss/publications",
}

# FRED series for automated data pulls
FRED_SERIES = {
    # --- Rates & Yields ---
    "DFF":      "Fed Funds Effective Rate",
    "DGS2":     "2-Year Treasury Yield",
    "DGS10":    "10-Year Treasury Yield",
    "T10Y2Y":   "10Y–2Y Spread (Yield Curve)",
    "T10Y3M":   "10Y–3M Spread",
    "BAMLH0A0HYM2": "High Yield OAS Spread",

    # --- Inflation ---
    "CPIAUCSL": "CPI (All Urban Consumers)",
    "CPILFESL": "Core CPI (ex Food & Energy)",
    "PCEPILFE": "Core PCE Price Index",
    "MICH":     "U of Michigan Inflation Expectations",
    "T5YIE":    "5-Year Breakeven Inflation",
    "T10YIE":   "10-Year Breakeven Inflation",

    # --- Labor Market ---
    "UNRATE":   "Unemployment Rate",
    "PAYEMS":   "Total Nonfarm Payrolls",
    "ICSA":     "Initial Jobless Claims",
    "JTSJOL":   "JOLTS Job Openings",

    # --- Activity & Output ---
    "GDP":      "Real GDP",
    "INDPRO":   "Industrial Production",
    "RSXFS":    "Retail Sales (ex Food Services)",
    "UMCSENT":  "Consumer Sentiment (UMich)",

    # --- Money & Credit ---
    "M2SL":     "M2 Money Supply",
    "TOTRESNS": "Total Bank Reserves",
    "WALCL":    "Fed Balance Sheet (Total Assets)",

    # --- Housing ---
    "HOUST":    "Housing Starts",
    "CSUSHPISA":"Case-Shiller Home Price Index",

    # --- Financial Conditions ---
    "NFCI":     "Chicago Fed National Financial Conditions",
    "VIXCLS":   "VIX (Volatility Index)",
    "DTWEXBGS": "Trade-Weighted USD Index (Broad)",
    "DCOILWTICO":"WTI Crude Oil Price",
    "GOLDAMGBD228NLBM": "Gold Price (London Fix)",

    # --- Global ---
    "GEPUCURRENT": "Global Economic Policy Uncertainty",
}

# Topics the search API should look for each week
SEARCH_TOPICS = [
    "Federal Reserve monetary policy this week",
    "US economic data releases this week",
    "Treasury market bond yields analysis",
    "global central bank decisions this week",
    "US earnings season results analysis",
    "IMF World Bank economic outlook",
    "inflation expectations markets",
    "credit markets corporate bonds spreads",
    "emerging markets currencies macro",
    "fiscal policy government spending deficit",
    "geopolitical risks financial markets",
    "labor market wages employment trends",
]


def run_pipeline():
    """Execute the full research agent pipeline."""
    today = datetime.date.today()
    report_date = today.strftime("%B %d, %Y")
    week_label = f"Week of {today.strftime('%B %d, %Y')}"

    logger.info(f"=== Starting Financial Market Economist Agent — {report_date} ===")

    # ------------------------------------------------------------------
    # 1  COLLECT
    # ------------------------------------------------------------------
    logger.info("Phase 1: Collecting data from all sources...")

    rss = RSSCollector(feeds=RSS_FEEDS, lookback_days=7)
    rss_articles = rss.collect()
    logger.info(f"  RSS: {len(rss_articles)} articles")

    search = WebSearchCollector(topics=SEARCH_TOPICS)
    search_articles = search.collect()
    logger.info(f"  Search: {len(search_articles)} articles")

    fred = FREDDataCollector(series=FRED_SERIES, lookback_days=90)
    fred_data = fred.collect()
    logger.info(f"  FRED: {len(fred_data)} data series")

    # ------------------------------------------------------------------
    # 2  SYNTHESIZE
    # ------------------------------------------------------------------
    logger.info("Phase 2: Synthesizing research via Claude...")

    synthesizer = ReportSynthesizer()
    report_content = synthesizer.synthesize(
        rss_articles=rss_articles,
        search_articles=search_articles,
        fred_data=fred_data,
        report_date=report_date,
    )
    logger.info("  Synthesis complete.")

    # ------------------------------------------------------------------
    # 3  BUILD REPORT
    # ------------------------------------------------------------------
    logger.info("Phase 3: Rendering charts and building reports...")

    # Render charts as static PNGs (Gmail can't run JavaScript)
    charts = render_fred_charts(
        sections=report_content.get("sections", []),
        fred_data=fred_data,
    )
    logger.info(f"  Rendered {len(charts)} charts as PNG images")

    # Build Gmail-compatible email (inline styles, embedded chart images)
    email_builder = EmailReportBuilder()
    email_html = email_builder.build(
        content=report_content,
        charts=charts,
        report_date=report_date,
        week_label=week_label,
    )

    # Also build the interactive browser version (Chart.js, dark theme)
    browser_builder = ReportBuilder()
    browser_html = browser_builder.build(
        content=report_content,
        fred_data=fred_data,
        report_date=report_date,
        week_label=week_label,
    )

    # Save both versions
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / f"market_brief_{today.isoformat()}_email.html").write_text(email_html, encoding="utf-8")
    (output_dir / f"market_brief_{today.isoformat()}_browser.html").write_text(browser_html, encoding="utf-8")
    logger.info(f"  Reports saved → {output_dir}")

    # ------------------------------------------------------------------
    # 4  EMAIL
    # ------------------------------------------------------------------
    logger.info("Phase 4: Emailing report...")

    emailer = ReportEmailer()
    emailer.send(
        subject=f"📊 Weekly Market Economist Brief — {week_label}",
        html_body=email_html,
    )

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
