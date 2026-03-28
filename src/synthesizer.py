"""
Report synthesizer using Claude API.
Takes collected articles and data, produces structured analysis.
"""

import os
import json
import logging
from dataclasses import asdict

import anthropic

logger = logging.getLogger("agent.synthesizer")

SYSTEM_PROMPT = """You are a senior financial market economist producing a weekly research brief. 
Your audience is a finance professional building deep investment expertise. 

Your mandate:
1. ANALYZE — Identify the 5–8 most significant macro and market developments of the week
2. CONTEXTUALIZE — Connect each development to the broader economic cycle, policy trajectory, or market regime
3. BALANCE — For each major theme, present BOTH the consensus view AND credible contrarian perspectives
4. QUANTIFY — Reference specific data points, levels, and changes wherever possible
5. LOOK AHEAD — Flag upcoming catalysts, data releases, and risk events for the week ahead

Your output MUST be valid JSON with this exact structure:

{
  "executive_summary": "3-4 paragraph overview of the week's most important market and economic developments. Lead with the single most significant theme.",
  
  "sections": [
    {
      "title": "Section title (e.g., 'Monetary Policy & Rates')",
      "icon": "emoji for this section",
      "analysis": "4-6 paragraph deep analysis of this theme. Include specific data points.",
      "consensus_view": "What the mainstream / sell-side consensus believes and why",
      "contrarian_view": "Credible alternative interpretation and what would make it right",
      "key_data_points": [
        {"label": "Data point name", "value": "Current value", "change": "+/- change description", "direction": "up|down|flat"}
      ],
      "chart_suggestions": [
        {"fred_series": "SERIES_ID", "title": "Chart title", "interpretation": "What this chart shows and why it matters"}
      ]
    }
  ],
  
  "data_dashboard": {
    "rates": [
      {"label": "Name", "value": "Current", "change": "Δ description", "direction": "up|down|flat"}
    ],
    "inflation": [...],
    "labor": [...],
    "activity": [...],
    "financial_conditions": [...],
    "global": [...]
  },
  
  "week_ahead": {
    "catalysts": ["Key event 1", "Key event 2"],
    "data_releases": [
      {"date": "Day, Month Date", "release": "Name", "prior": "Previous value", "consensus": "Expected value"}
    ],
    "risks": ["Upside or downside risk to watch"]
  },
  
  "bottom_line": "2-3 sentence synthesis: What does this all mean for an economist watching these markets? What's the single most important thing to track next week?"
}

Guidelines:
- Be specific: use numbers, basis points, percentages, levels
- Think like a sell-side macro strategist — precise, opinionated but balanced
- Distinguish between signal and noise
- If data is stale or missing, note it and use your knowledge
- Chart suggestions should reference actual FRED series IDs from the data provided
- Each section should be 4-6 substantial paragraphs, not bullet points
- The executive summary should be publication-quality prose
"""


class ReportSynthesizer:
    """Uses Claude to synthesize collected research into a structured report."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.model = "claude-sonnet-4-20250514"

    def synthesize(
        self,
        rss_articles: list,
        search_articles: list,
        fred_data: list,
        report_date: str,
    ) -> dict:
        """Send all collected data to Claude for synthesis."""

        # Build the user prompt with all collected data
        user_prompt = self._build_prompt(rss_articles, search_articles, fred_data, report_date)

        logger.info(f"Sending synthesis request to Claude ({self.model})...")
        logger.info(f"  Input size: ~{len(user_prompt)} chars")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text

        # Parse JSON from response
        try:
            # Handle potential markdown code fences
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Raw response (first 500 chars): {raw_text[:500]}")
            # Return a minimal fallback
            return {
                "executive_summary": raw_text[:2000],
                "sections": [],
                "data_dashboard": {},
                "week_ahead": {"catalysts": [], "data_releases": [], "risks": []},
                "bottom_line": "Report generation encountered an error. Please review the executive summary above.",
            }

    def _build_prompt(self, rss_articles, search_articles, fred_data, report_date) -> str:
        parts = [f"Today is {report_date}. Produce the weekly market economist brief.\n"]

        # RSS articles
        parts.append("=" * 60)
        parts.append("RSS FEED ARTICLES (curated financial sources)")
        parts.append("=" * 60)
        for i, a in enumerate(rss_articles[:60]):  # Cap for token budget
            parts.append(f"\n--- Article {i+1} ---")
            parts.append(f"Source: {a.source}")
            parts.append(f"Title: {a.title}")
            parts.append(f"Published: {a.published}")
            parts.append(f"Category: {a.category}")
            if a.full_text:
                parts.append(f"Text: {a.full_text[:1500]}")
            elif a.summary:
                parts.append(f"Summary: {a.summary}")

        # Search results
        parts.append("\n" + "=" * 60)
        parts.append("WEB SEARCH RESULTS (breaking/trending topics)")
        parts.append("=" * 60)
        for i, a in enumerate(search_articles[:30]):
            parts.append(f"\n--- Search Result {i+1} ---")
            parts.append(f"Title: {a.title}")
            parts.append(f"URL: {a.url}")
            if a.full_text:
                parts.append(f"Text: {a.full_text[:1000]}")
            elif a.summary:
                parts.append(f"Summary: {a.summary}")

        # FRED data
        parts.append("\n" + "=" * 60)
        parts.append("FRED ECONOMIC DATA (recent observations)")
        parts.append("=" * 60)
        for series in fred_data:
            parts.append(f"\n{series.series_id} — {series.name}")
            parts.append(f"  Units: {series.units} | Frequency: {series.frequency}")
            if series.observations:
                latest = series.observations[0]
                parts.append(f"  Latest: {latest['value']} ({latest['date']})")
                if len(series.observations) >= 2:
                    prev = series.observations[1]
                    chg = latest["value"] - prev["value"]
                    parts.append(f"  Prior:  {prev['value']} ({prev['date']}) | Δ {chg:+.4f}")
                # Include last 10 observations for trend context
                recent_vals = [(o["date"], o["value"]) for o in series.observations[:10]]
                parts.append(f"  Recent: {recent_vals}")

        parts.append("\n" + "=" * 60)
        parts.append("Please produce the full weekly brief as a JSON object following the specified schema.")

        return "\n".join(parts)
