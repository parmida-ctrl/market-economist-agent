# 📊 Financial Market Economist Research Agent

A fully automated weekly research pipeline that collects financial data from 25+ sources, synthesizes insights via Claude, generates a publication-quality HTML report with charts, and emails it to you every Monday morning.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions (cron)                  │
│                  Every Monday 7:00 AM ET                │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │     1. COLLECT          │
          │  ┌──────────────────┐   │
          │  │ RSS Feeds (25+)  │   │
          │  │ Fed / ECB / BIS  │   │
          │  │ Reuters / FT     │   │
          │  │ NBER / Brookings │   │
          │  └──────────────────┘   │
          │  ┌──────────────────┐   │
          │  │ Web Search API   │   │
          │  │ Breaking topics  │   │
          │  │ Tavily / SerpAPI │   │
          │  └──────────────────┘   │
          │  ┌──────────────────┐   │
          │  │ FRED API (30+)   │   │
          │  │ Rates, CPI, GDP  │   │
          │  │ Jobs, VIX, USD   │   │
          │  └──────────────────┘   │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │     2. SYNTHESIZE       │
          │   Claude Sonnet 4       │
          │   Structured JSON out   │
          │   Consensus + contrarian│
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │     3. BUILD REPORT     │
          │   HTML + Chart.js       │
          │   Responsive (mobile)   │
          │   Dark theme, polished  │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │     4. DELIVER          │
          │   SendGrid / SMTP email │
          │   + GitHub artifact     │
          └─────────────────────────┘
```

## What You Get

Every Monday, you receive an HTML email containing:

- **Executive Summary** — 3-4 paragraph overview of the week's most important developments
- **Thematic Sections** — Deep analysis of 5-8 major macro/market themes
- **Consensus vs. Contrarian Views** — Balanced perspectives for each theme
- **Interactive Charts** — FRED data visualizations powered by Chart.js
- **Data Dashboard** — Quick-scan table of rates, inflation, labor, activity, and financial conditions
- **Week Ahead** — Upcoming catalysts, data releases, and risks to watch
- **Bottom Line** — Synthesis and what to focus on next

The report renders beautifully on both desktop and mobile.

## Setup

### 1. Get Your API Keys

| Service | Purpose | Get it at |
|---------|---------|-----------|
| **Anthropic** | Claude API for synthesis | [console.anthropic.com](https://console.anthropic.com) |
| **FRED** | Economic data | [fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html) (free) |
| **Tavily** | Web search | [tavily.com](https://tavily.com) (free tier available) |
| **SendGrid** | Email delivery | [sendgrid.com](https://sendgrid.com) (free 100 emails/day) |

### 2. Fork & Configure

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/market-economist-agent.git
cd market-economist-agent
```

### 3. Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Your Anthropic API key |
| `FRED_API_KEY` | ✅ | Your FRED API key |
| `TAVILY_API_KEY` | Recommended | Tavily search API key |
| `SENDGRID_API_KEY` | ✅* | SendGrid API key |
| `REPORT_EMAIL_TO` | ✅ | Your email address |
| `REPORT_EMAIL_FROM` | ✅ | Sender email (verified in SendGrid) |
| `SMTP_PASSWORD` | Alt* | Gmail app password (alternative to SendGrid) |
| `SMTP_HOST` | Alt* | `smtp.gmail.com` |
| `SMTP_PORT` | Alt* | `587` |

*Use either SendGrid OR SMTP, not both.

### 4. Test It

Trigger a manual run: Actions tab → "Weekly Market Economist Brief" → "Run workflow"

### 5. Customize

Edit `src/agent.py` to:
- Add or remove RSS feeds
- Change FRED series
- Modify search topics
- Adjust the schedule in `.github/workflows/weekly_brief.yml`

## Estimated Costs

| Component | Monthly Cost |
|-----------|-------------|
| Claude API (1 call/week, ~8K output tokens) | ~$2–4 |
| FRED API | Free |
| Tavily (12 searches/week) | Free tier (1,000/mo) |
| SendGrid (4 emails/month) | Free tier |
| GitHub Actions | Free (public repo) |
| **Total** | **~$2–4/month** |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="sk-..."
export FRED_API_KEY="..."
export TAVILY_API_KEY="tvly-..."
export REPORT_EMAIL_TO="you@email.com"
export REPORT_EMAIL_FROM="agent@yourdomain.com"
export SENDGRID_API_KEY="SG...."

# Run
cd src && python agent.py
```

The report will be saved to `src/output/` and emailed to you.

## Project Structure

```
market-economist-agent/
├── .github/
│   └── workflows/
│       └── weekly_brief.yml    # GitHub Actions schedule
├── src/
│   ├── agent.py                # Main pipeline orchestrator
│   ├── sources.py              # RSS, web search, FRED collectors
│   ├── synthesizer.py          # Claude API synthesis engine
│   ├── report_builder.py       # HTML report with Chart.js
│   └── emailer.py              # SendGrid / SMTP delivery
├── requirements.txt
└── README.md
```

## Extending

Ideas for future enhancements:
- **Earnings data**: Integrate Alpha Vantage or Financial Modeling Prep for earnings
- **Sentiment analysis**: Score article sentiment before synthesis
- **Historical archive**: Deploy to GitHub Pages for a browsable archive
- **Slack integration**: Post a summary to a Slack channel
- **PDF export**: Generate a PDF version via WeasyPrint
- **Custom themes**: Add light mode or custom branding
