"""
Report builder — produces a self-contained HTML report with embedded
Chart.js charts, responsive design for desktop + mobile, and inline styles.
"""

import json
import logging
from dataclasses import asdict

logger = logging.getLogger("agent.report_builder")


class ReportBuilder:
    """Builds a self-contained HTML report with charts and responsive design."""

    def build(self, content: dict, fred_data: list, report_date: str, week_label: str) -> str:
        """Assemble the full HTML report."""
        sections_html = self._build_sections(content.get("sections", []))
        dashboard_html = self._build_dashboard(content.get("data_dashboard", {}))
        charts_js = self._build_charts(content.get("sections", []), fred_data)
        week_ahead_html = self._build_week_ahead(content.get("week_ahead", {}))

        return self._wrap_html(
            executive_summary=content.get("executive_summary", ""),
            sections_html=sections_html,
            dashboard_html=dashboard_html,
            charts_js=charts_js,
            week_ahead_html=week_ahead_html,
            bottom_line=content.get("bottom_line", ""),
            report_date=report_date,
            week_label=week_label,
        )

    def _build_sections(self, sections: list) -> str:
        html_parts = []
        for section in sections:
            icon = section.get("icon", "📊")
            title = section.get("title", "")
            analysis = section.get("analysis", "").replace("\n", "<br>")

            # Key data points
            data_points_html = ""
            for dp in section.get("key_data_points", []):
                direction = dp.get("direction", "flat")
                arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(direction, "→")
                color = {"up": "#10b981", "down": "#ef4444", "flat": "#6b7280"}.get(direction, "#6b7280")
                data_points_html += f"""
                <div class="data-chip">
                    <span class="chip-label">{dp.get('label', '')}</span>
                    <span class="chip-value">{dp.get('value', '')}</span>
                    <span class="chip-change" style="color:{color}">{arrow} {dp.get('change', '')}</span>
                </div>"""

            # Consensus vs contrarian
            consensus = section.get("consensus_view", "")
            contrarian = section.get("contrarian_view", "")
            views_html = ""
            if consensus or contrarian:
                views_html = f"""
                <div class="views-grid">
                    <div class="view-box consensus">
                        <div class="view-label">🎯 Consensus View</div>
                        <p>{consensus}</p>
                    </div>
                    <div class="view-box contrarian">
                        <div class="view-label">⚡ Contrarian View</div>
                        <p>{contrarian}</p>
                    </div>
                </div>"""

            # Chart placeholder
            chart_html = ""
            for i, cs in enumerate(section.get("chart_suggestions", [])):
                chart_id = f"chart_{title.replace(' ', '_').replace('&', 'and')}_{i}".lower()
                chart_html += f"""
                <div class="chart-container">
                    <div class="chart-title">{cs.get('title', '')}</div>
                    <canvas id="{chart_id}" height="140"></canvas>
                    <div class="chart-interpretation">{cs.get('interpretation', '')}</div>
                </div>"""

            html_parts.append(f"""
            <section class="report-section">
                <h2>{icon} {title}</h2>
                <div class="section-body">
                    <div class="analysis-text">{analysis}</div>
                    {f'<div class="data-chips">{data_points_html}</div>' if data_points_html else ''}
                    {chart_html}
                    {views_html}
                </div>
            </section>""")

        return "\n".join(html_parts)

    def _build_dashboard(self, dashboard: dict) -> str:
        if not dashboard:
            return ""

        categories = {
            "rates": ("📈 Rates & Yields", "#2563eb"),
            "inflation": ("🔥 Inflation", "#dc2626"),
            "labor": ("👷 Labor Market", "#7c3aed"),
            "activity": ("🏭 Activity & Output", "#059669"),
            "financial_conditions": ("⚖️ Financial Conditions", "#d97706"),
            "global": ("🌍 Global", "#0891b2"),
        }

        panels = []
        for key, (label, color) in categories.items():
            items = dashboard.get(key, [])
            if not items:
                continue
            rows = ""
            for item in items:
                direction = item.get("direction", "flat")
                arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(direction, "→")
                change_color = {"up": "#10b981", "down": "#ef4444", "flat": "#6b7280"}.get(direction, "#6b7280")
                rows += f"""
                <tr>
                    <td class="dash-label">{item.get('label', '')}</td>
                    <td class="dash-value">{item.get('value', '')}</td>
                    <td class="dash-change" style="color:{change_color}">{arrow} {item.get('change', '')}</td>
                </tr>"""

            panels.append(f"""
            <div class="dashboard-panel">
                <div class="panel-header" style="border-left: 4px solid {color}">{label}</div>
                <table class="dash-table">
                    {rows}
                </table>
            </div>""")

        return f"""
        <section class="report-section">
            <h2>📊 Data Dashboard</h2>
            <div class="dashboard-grid">
                {"".join(panels)}
            </div>
        </section>"""

    def _build_charts(self, sections: list, fred_data: list) -> str:
        """Generate Chart.js initialization code for suggested charts."""
        # Build a lookup from series ID → observations
        fred_lookup = {}
        for series in fred_data:
            fred_lookup[series.series_id] = {
                "name": series.name,
                "observations": list(reversed(series.observations[:60])),  # Chronological
                "units": series.units,
            }

        chart_configs = []
        for section in sections:
            title_slug = section.get("title", "").replace(" ", "_").replace("&", "and").lower()
            for i, cs in enumerate(section.get("chart_suggestions", [])):
                chart_id = f"chart_{title_slug}_{i}"
                series_id = cs.get("fred_series", "")
                series_data = fred_lookup.get(series_id)
                if not series_data or not series_data["observations"]:
                    continue

                labels = json.dumps([o["date"] for o in series_data["observations"]])
                values = json.dumps([o["value"] for o in series_data["observations"]])
                series_name = series_data["name"]
                units = series_data["units"]

                chart_configs.append(f"""
    (function() {{
        const ctx = document.getElementById('{chart_id}');
        if (!ctx) return;
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: '{series_name}',
                    data: {values},
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.08)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    fill: true,
                    tension: 0.3,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: '#1e293b',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{
                            maxTicksLimit: 8,
                            font: {{ size: 10 }},
                            color: '#94a3b8',
                        }}
                    }},
                    y: {{
                        grid: {{ color: 'rgba(148,163,184,0.12)' }},
                        ticks: {{
                            font: {{ size: 10 }},
                            color: '#94a3b8',
                        }},
                        title: {{
                            display: true,
                            text: '{units}',
                            color: '#94a3b8',
                            font: {{ size: 10 }},
                        }}
                    }}
                }}
            }}
        }});
    }})();""")

        return "\n".join(chart_configs)

    def _build_week_ahead(self, week_ahead: dict) -> str:
        if not week_ahead:
            return ""

        catalysts = week_ahead.get("catalysts", [])
        releases = week_ahead.get("data_releases", [])
        risks = week_ahead.get("risks", [])

        catalysts_html = "".join(f'<li class="catalyst-item">📌 {c}</li>' for c in catalysts)

        releases_html = ""
        for r in releases:
            releases_html += f"""
            <tr>
                <td class="release-date">{r.get('date', '')}</td>
                <td class="release-name">{r.get('release', '')}</td>
                <td class="release-prior">{r.get('prior', '—')}</td>
                <td class="release-consensus">{r.get('consensus', '—')}</td>
            </tr>"""

        risks_html = "".join(f'<li class="risk-item">⚠️ {r}</li>' for r in risks)

        return f"""
        <section class="report-section">
            <h2>🔭 Week Ahead</h2>
            <div class="week-ahead-grid">
                <div class="wa-panel">
                    <h3>Key Catalysts</h3>
                    <ul class="catalyst-list">{catalysts_html}</ul>
                </div>
                <div class="wa-panel wide">
                    <h3>Data Calendar</h3>
                    <table class="release-table">
                        <thead>
                            <tr><th>Date</th><th>Release</th><th>Prior</th><th>Consensus</th></tr>
                        </thead>
                        <tbody>{releases_html}</tbody>
                    </table>
                </div>
                <div class="wa-panel">
                    <h3>Risks to Watch</h3>
                    <ul class="risk-list">{risks_html}</ul>
                </div>
            </div>
        </section>"""

    def _wrap_html(self, **kwargs) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Economist Brief — {kwargs['week_label']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0f172a;
    --bg-card: #1e293b;
    --bg-card-alt: #162032;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --text-bright: #f8fafc;
    --accent: #3b82f6;
    --accent-glow: rgba(59, 130, 246, 0.15);
    --green: #10b981;
    --red: #ef4444;
    --amber: #f59e0b;
    --border: #334155;
    --font-serif: 'Instrument Serif', Georgia, serif;
    --font-sans: 'DM Sans', -apple-system, system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}}

.report-container {{
    max-width: 860px;
    margin: 0 auto;
    padding: 24px 20px 60px;
}}

/* Header */
.report-header {{
    text-align: center;
    padding: 48px 20px 40px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 40px;
}}
.report-header .overline {{
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 16px;
}}
.report-header h1 {{
    font-family: var(--font-serif);
    font-size: clamp(28px, 5vw, 42px);
    font-weight: 400;
    color: var(--text-bright);
    line-height: 1.2;
    margin-bottom: 12px;
}}
.report-header .date {{
    font-size: 14px;
    color: var(--text-muted);
}}

/* Executive Summary */
.exec-summary {{
    background: linear-gradient(135deg, var(--bg-card), var(--bg-card-alt));
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 32px;
    margin-bottom: 40px;
    position: relative;
}}
.exec-summary::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, var(--accent), #8b5cf6, var(--accent));
    border-radius: 12px 12px 0 0;
}}
.exec-summary h2 {{
    font-family: var(--font-serif);
    font-size: 22px;
    color: var(--text-bright);
    margin-bottom: 16px;
}}
.exec-summary p {{
    margin-bottom: 12px;
    color: var(--text);
}}

/* Sections */
.report-section {{
    margin-bottom: 40px;
}}
.report-section h2 {{
    font-family: var(--font-serif);
    font-size: 24px;
    color: var(--text-bright);
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}}
.section-body {{
    padding: 0 4px;
}}
.analysis-text {{
    margin-bottom: 20px;
    line-height: 1.8;
}}

/* Data chips */
.data-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 24px;
}}
.data-chip {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 140px;
}}
.chip-label {{
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.chip-value {{
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-bright);
}}
.chip-change {{
    font-family: var(--font-mono);
    font-size: 12px;
}}

/* Views grid */
.views-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 20px;
}}
.view-box {{
    background: var(--bg-card);
    border-radius: 10px;
    padding: 20px;
    border: 1px solid var(--border);
}}
.view-box.consensus {{
    border-left: 3px solid var(--accent);
}}
.view-box.contrarian {{
    border-left: 3px solid var(--amber);
}}
.view-label {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    color: var(--text-muted);
}}
.view-box p {{
    font-size: 14px;
    line-height: 1.7;
}}

/* Charts */
.chart-container {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;max-height:240px;overflow:hidden;
}}
.chart-title {{
    font-family: var(--font-sans);
    font-weight: 600;
    font-size: 14px;
    color: var(--text-bright);
    margin-bottom: 12px;
}}
.chart-interpretation {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 12px;
    font-style: italic;
}}

/* Dashboard */
.dashboard-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
}}
.dashboard-panel {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
}}
.panel-header {{
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    background: var(--bg-card-alt);
    letter-spacing: 0.3px;
}}
.dash-table {{
    width: 100%;
    border-collapse: collapse;
}}
.dash-table td {{
    padding: 8px 16px;
    border-top: 1px solid rgba(51, 65, 85, 0.5);
    font-size: 13px;
}}
.dash-label {{ color: var(--text); }}
.dash-value {{
    font-family: var(--font-mono);
    font-weight: 500;
    color: var(--text-bright);
    text-align: right;
}}
.dash-change {{
    font-family: var(--font-mono);
    font-size: 12px;
    text-align: right;
    white-space: nowrap;
}}

/* Week Ahead */
.week-ahead-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}
.wa-panel {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
}}
.wa-panel.wide {{
    grid-column: 1 / -1;
}}
.wa-panel h3 {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--text-bright);
}}
.catalyst-list, .risk-list {{
    list-style: none;
}}
.catalyst-item, .risk-item {{
    padding: 8px 0;
    border-bottom: 1px solid rgba(51, 65, 85, 0.4);
    font-size: 14px;
}}
.release-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.release-table th {{
    text-align: left;
    padding: 8px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
}}
.release-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.3);
}}
.release-date {{
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
}}

/* Bottom Line */
.bottom-line {{
    background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1));
    border: 1px solid var(--accent);
    border-radius: 12px;
    padding: 28px 32px;
    margin-top: 40px;
}}
.bottom-line h2 {{
    font-family: var(--font-serif);
    font-size: 20px;
    color: var(--text-bright);
    margin-bottom: 12px;
    border: none;
    padding: 0;
}}
.bottom-line p {{
    font-size: 15px;
    line-height: 1.8;
}}

/* Footer */
.report-footer {{
    text-align: center;
    padding: 40px 20px;
    font-size: 12px;
    color: var(--text-muted);
    border-top: 1px solid var(--border);
    margin-top: 40px;
}}

/* Responsive */
@media (max-width: 640px) {{
    .report-container {{ padding: 16px 14px 40px; }}
    .report-header {{ padding: 32px 12px 28px; }}
    .exec-summary {{ padding: 20px; }}
    .views-grid {{ grid-template-columns: 1fr; }}
    .week-ahead-grid {{ grid-template-columns: 1fr; }}
    .data-chip {{ min-width: 120px; }}
    .dashboard-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="report-container">

    <header class="report-header">
        <div class="overline">Weekly Market Economist Brief</div>
        <h1>{kwargs['week_label']}</h1>
        <div class="date">Published {kwargs['report_date']} · Automated Research Agent</div>
    </header>

    <div class="exec-summary">
        <h2>Executive Summary</h2>
        {"".join(f"<p>{p.strip()}</p>" for p in kwargs['executive_summary'].split(chr(10)) if p.strip())}
    </div>

    {kwargs['sections_html']}

    {kwargs['dashboard_html']}

    {kwargs['week_ahead_html']}

    <div class="bottom-line">
        <h2>🎯 The Bottom Line</h2>
        <p>{kwargs['bottom_line']}</p>
    </div>

    <footer class="report-footer">
        <p>Generated by Financial Market Economist Agent · Powered by Claude &amp; FRED</p>
        <p>This report is for informational purposes only and does not constitute investment advice.</p>
    </footer>

</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
    {kwargs['charts_js']}
}});
</script>
</body>
</html>"""
