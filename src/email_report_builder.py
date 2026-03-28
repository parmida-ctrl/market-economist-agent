"""
Email report builder — Gmail-compatible HTML with inline styles and
embedded chart images (base64 PNGs from matplotlib).

Gmail strips <style> tags, blocks external fonts, ignores CSS variables,
and won't run JavaScript. This builder uses ONLY inline styles.
"""

import json
import logging

logger = logging.getLogger("agent.email_report")

# ── Color palette (used inline since CSS variables don't work in Gmail) ──
BG = "#0f172a"
BG_CARD = "#1e293b"
BG_CARD_ALT = "#162032"
TEXT = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
TEXT_BRIGHT = "#f8fafc"
ACCENT = "#3b82f6"
GREEN = "#10b981"
RED = "#ef4444"
AMBER = "#f59e0b"
BORDER = "#334155"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"


class EmailReportBuilder:
    """Builds a Gmail-compatible HTML email report."""

    def build(self, content: dict, charts: dict, report_date: str, week_label: str) -> str:
        sections_html = self._build_sections(content.get("sections", []), charts)
        dashboard_html = self._build_dashboard(content.get("data_dashboard", {}))
        week_ahead_html = self._build_week_ahead(content.get("week_ahead", {}))

        return self._wrap_email(
            executive_summary=content.get("executive_summary", ""),
            sections_html=sections_html,
            dashboard_html=dashboard_html,
            week_ahead_html=week_ahead_html,
            bottom_line=content.get("bottom_line", ""),
            report_date=report_date,
            week_label=week_label,
        )

    # ── Sections ──────────────────────────────────────────────────────────

    def _build_sections(self, sections: list, charts: dict) -> str:
        parts = []
        for section in sections:
            icon = section.get("icon", "📊")
            title = section.get("title", "")
            analysis = section.get("analysis", "").replace("\n", "<br>")
            title_slug = title.replace(" ", "_").replace("&", "and").lower()

            # Data chips
            chips_html = ""
            for dp in section.get("key_data_points", []):
                direction = dp.get("direction", "flat")
                arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(direction, "→")
                color = {"up": GREEN, "down": RED, "flat": TEXT_MUTED}.get(direction, TEXT_MUTED)
                chips_html += f'''
                <td style="padding:0 8px 8px 0;">
                    <table cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;min-width:130px;">
                        <tr><td style="padding:10px 14px 2px;font-family:{FONT};font-size:11px;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.5px;">{dp.get("label","")}</td></tr>
                        <tr><td style="padding:0 14px 2px;font-family:{FONT};font-size:18px;font-weight:700;color:{TEXT_BRIGHT};">{dp.get("value","")}</td></tr>
                        <tr><td style="padding:0 14px 10px;font-family:{FONT};font-size:12px;color:{color};">{arrow} {dp.get("change","")}</td></tr>
                    </table>
                </td>'''

            # Charts (embedded PNGs)
            chart_html = ""
            for i, cs in enumerate(section.get("chart_suggestions", [])):
                chart_id = f"chart_{title_slug}_{i}"
                b64_img = charts.get(chart_id)
                if b64_img:
                    interpretation = cs.get("interpretation", "")
                    chart_html += f'''
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;margin:16px 0;">
                        <tr><td style="padding:16px 20px 8px;">
                            <img src="{b64_img}" alt="{cs.get('title','Chart')}" style="width:100%;height:auto;display:block;border-radius:4px;">
                        </td></tr>
                        <tr><td style="padding:4px 20px 16px;font-family:{FONT};font-size:12px;color:{TEXT_MUTED};font-style:italic;">{interpretation}</td></tr>
                    </table>'''

            # Consensus vs Contrarian
            consensus = section.get("consensus_view", "")
            contrarian = section.get("contrarian_view", "")
            views_html = ""
            if consensus or contrarian:
                views_html = f'''
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
                    <tr>
                        <td width="49%" valign="top" style="padding-right:8px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {ACCENT};border-radius:10px;">
                                <tr><td style="padding:16px 16px 4px;font-family:{FONT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">🎯 Consensus View</td></tr>
                                <tr><td style="padding:4px 16px 16px;font-family:{FONT};font-size:13px;line-height:1.6;color:{TEXT};">{consensus}</td></tr>
                            </table>
                        </td>
                        <td width="2%"></td>
                        <td width="49%" valign="top" style="padding-left:8px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {AMBER};border-radius:10px;">
                                <tr><td style="padding:16px 16px 4px;font-family:{FONT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">⚡ Contrarian View</td></tr>
                                <tr><td style="padding:4px 16px 16px;font-family:{FONT};font-size:13px;line-height:1.6;color:{TEXT};">{contrarian}</td></tr>
                            </table>
                        </td>
                    </tr>
                </table>'''

            parts.append(f'''
            <!-- Section: {title} -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
                <tr><td style="padding-bottom:12px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:22px;font-weight:400;color:{TEXT_BRIGHT};">{icon} {title}</td></tr>
                <tr><td style="padding-top:16px;font-family:{FONT};font-size:14px;line-height:1.8;color:{TEXT};">{analysis}</td></tr>
                {"<tr><td style='padding-top:16px;'><table cellpadding='0' cellspacing='0'><tr>" + chips_html + "</tr></table></td></tr>" if chips_html else ""}
                <tr><td>{chart_html}</td></tr>
                <tr><td>{views_html}</td></tr>
            </table>''')

        return "\n".join(parts)

    # ── Dashboard ─────────────────────────────────────────────────────────

    def _build_dashboard(self, dashboard: dict) -> str:
        if not dashboard:
            return ""

        categories = {
            "rates":                ("📈 Rates & Yields",       ACCENT),
            "inflation":            ("🔥 Inflation",            RED),
            "labor":                ("👷 Labor Market",         "#7c3aed"),
            "activity":             ("🏭 Activity & Output",    GREEN),
            "financial_conditions": ("⚖️ Financial Conditions", AMBER),
            "global":               ("🌍 Global",               "#0891b2"),
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
                chg_color = {"up": GREEN, "down": RED, "flat": TEXT_MUTED}.get(direction, TEXT_MUTED)
                rows += f'''
                <tr>
                    <td style="padding:7px 12px;border-top:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">{item.get("label","")}</td>
                    <td style="padding:7px 12px;border-top:1px solid {BORDER};font-family:{FONT};font-size:13px;font-weight:600;color:{TEXT_BRIGHT};text-align:right;">{item.get("value","")}</td>
                    <td style="padding:7px 12px;border-top:1px solid {BORDER};font-family:{FONT};font-size:12px;color:{chg_color};text-align:right;white-space:nowrap;">{arrow} {item.get("change","")}</td>
                </tr>'''

            panels.append(f'''
            <td width="49%" valign="top" style="padding:0 4px 12px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;overflow:hidden;">
                    <tr><td style="padding:10px 14px;background:{BG_CARD_ALT};border-left:4px solid {color};font-family:{FONT};font-size:13px;font-weight:600;color:{TEXT_BRIGHT};">{label}</td></tr>
                    <tr><td>
                        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
                    </td></tr>
                </table>
            </td>''')

        # Arrange in 2-column rows
        grid_rows = []
        for i in range(0, len(panels), 2):
            pair = panels[i:i+2]
            if len(pair) == 1:
                pair.append("<td></td>")
            grid_rows.append(f"<tr>{''.join(pair)}</tr>")

        return f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
            <tr><td style="padding-bottom:12px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:22px;color:{TEXT_BRIGHT};">📊 Data Dashboard</td></tr>
            <tr><td style="padding-top:16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    {"".join(grid_rows)}
                </table>
            </td></tr>
        </table>'''

    # ── Week Ahead ────────────────────────────────────────────────────────

    def _build_week_ahead(self, week_ahead: dict) -> str:
        if not week_ahead:
            return ""

        catalysts = week_ahead.get("catalysts", [])
        releases = week_ahead.get("data_releases", [])
        risks = week_ahead.get("risks", [])

        cat_rows = "".join(
            f'<tr><td style="padding:8px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">📌 {c}</td></tr>'
            for c in catalysts
        )

        risk_rows = "".join(
            f'<tr><td style="padding:8px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">⚠️ {r}</td></tr>'
            for r in risks
        )

        release_rows = ""
        for r in releases:
            release_rows += f'''
            <tr>
                <td style="padding:7px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:12px;color:{TEXT_MUTED};white-space:nowrap;">{r.get("date","")}</td>
                <td style="padding:7px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">{r.get("release","")}</td>
                <td style="padding:7px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT_BRIGHT};text-align:right;">{r.get("prior","—")}</td>
                <td style="padding:7px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT_BRIGHT};text-align:right;">{r.get("consensus","—")}</td>
            </tr>'''

        return f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
            <tr><td style="padding-bottom:12px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:22px;color:{TEXT_BRIGHT};">🔭 Week Ahead</td></tr>
            <tr><td style="padding-top:16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="49%" valign="top" style="padding-right:8px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;">
                                <tr><td style="padding:14px 16px 8px;font-family:{FONT};font-size:14px;font-weight:600;color:{TEXT_BRIGHT};">Key Catalysts</td></tr>
                                <tr><td style="padding:0 16px 14px;"><table width="100%" cellpadding="0" cellspacing="0">{cat_rows}</table></td></tr>
                            </table>
                        </td>
                        <td width="2%"></td>
                        <td width="49%" valign="top" style="padding-left:8px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;">
                                <tr><td style="padding:14px 16px 8px;font-family:{FONT};font-size:14px;font-weight:600;color:{TEXT_BRIGHT};">Risks to Watch</td></tr>
                                <tr><td style="padding:0 16px 14px;"><table width="100%" cellpadding="0" cellspacing="0">{risk_rows}</table></td></tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td></tr>
            <tr><td style="padding-top:12px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;">
                    <tr><td style="padding:14px 16px 8px;font-family:{FONT};font-size:14px;font-weight:600;color:{TEXT_BRIGHT};">Data Calendar</td></tr>
                    <tr><td style="padding:0 16px 14px;">
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="padding:7px 10px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:1px solid {BORDER};">Date</td>
                                <td style="padding:7px 10px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:1px solid {BORDER};">Release</td>
                                <td style="padding:7px 10px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:1px solid {BORDER};text-align:right;">Prior</td>
                                <td style="padding:7px 10px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:1px solid {BORDER};text-align:right;">Consensus</td>
                            </tr>
                            {release_rows}
                        </table>
                    </td></tr>
                </table>
            </td></tr>
        </table>'''

    # ── Full email wrapper ────────────────────────────────────────────────

    def _wrap_email(self, **kw) -> str:
        exec_paragraphs = "".join(
            f'<p style="margin:0 0 12px;font-family:{FONT};font-size:14px;line-height:1.7;color:{TEXT};">{p.strip()}</p>'
            for p in kw["executive_summary"].split("\n") if p.strip()
        )

        return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:{BG};-webkit-font-smoothing:antialiased;">

<!-- Outer wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:{BG};">
<tr><td align="center" style="padding:24px 16px;">

<!-- Content container -->
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;">

    <!-- Header -->
    <tr><td align="center" style="padding:40px 20px 32px;border-bottom:1px solid {BORDER};">
        <div style="font-family:{FONT};font-size:11px;letter-spacing:3px;text-transform:uppercase;color:{ACCENT};margin-bottom:14px;">Weekly Market Economist Brief</div>
        <div style="font-family:Georgia,serif;font-size:32px;font-weight:400;color:{TEXT_BRIGHT};line-height:1.2;margin-bottom:10px;">{kw["week_label"]}</div>
        <div style="font-family:{FONT};font-size:13px;color:{TEXT_MUTED};">Published {kw["report_date"]} · Automated Research Agent</div>
    </td></tr>

    <!-- Executive Summary -->
    <tr><td style="padding:32px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;">
            <tr><td style="height:3px;background:linear-gradient(90deg,{ACCENT},#8b5cf6,{ACCENT});border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td></tr>
            <tr><td style="padding:28px 28px 8px;font-family:Georgia,serif;font-size:20px;color:{TEXT_BRIGHT};">Executive Summary</td></tr>
            <tr><td style="padding:8px 28px 28px;">{exec_paragraphs}</td></tr>
        </table>
    </td></tr>

    <!-- Sections -->
    <tr><td>{kw["sections_html"]}</td></tr>

    <!-- Dashboard -->
    <tr><td>{kw["dashboard_html"]}</td></tr>

    <!-- Week Ahead -->
    <tr><td>{kw["week_ahead_html"]}</td></tr>

    <!-- Bottom Line -->
    <tr><td style="padding-top:16px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {ACCENT};border-radius:12px;">
            <tr><td style="padding:24px 28px 8px;font-family:Georgia,serif;font-size:18px;color:{TEXT_BRIGHT};">🎯 The Bottom Line</td></tr>
            <tr><td style="padding:8px 28px 24px;font-family:{FONT};font-size:14px;line-height:1.8;color:{TEXT};">{kw["bottom_line"]}</td></tr>
        </table>
    </td></tr>

    <!-- Footer -->
    <tr><td align="center" style="padding:36px 20px;border-top:1px solid {BORDER};margin-top:32px;">
        <div style="font-family:{FONT};font-size:11px;color:{TEXT_MUTED};line-height:1.8;">
            Generated by Financial Market Economist Agent · Powered by Claude &amp; FRED<br>
            This report is for informational purposes only and does not constitute investment advice.
        </div>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''
