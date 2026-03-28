"""
Email report builder — Gmail-compatible HTML with:
- Light theme (Gmail forces white backgrounds anyway)
- All inline styles (Gmail strips <style> tags)
- Chart images referenced by GitHub Pages URL
"""

import logging

logger = logging.getLogger("agent.email_report")

BG = "#ffffff"
BG_CARD = "#f8fafc"
BG_CARD_ALT = "#f1f5f9"
TEXT = "#1e293b"
TEXT_MUTED = "#64748b"
TEXT_BRIGHT = "#0f172a"
ACCENT = "#2563eb"
GREEN = "#059669"
RED = "#dc2626"
AMBER = "#d97706"
BORDER = "#e2e8f0"
FONT = "Helvetica, Arial, sans-serif"


class EmailReportBuilder:
    def __init__(self, chart_base_url=""):
        self.chart_base_url = chart_base_url

    def build(self, content, charts, report_date, week_label):
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

    def _build_sections(self, sections, charts):
        parts = []
        for section in sections:
            icon = section.get("icon", "")
            title = section.get("title", "")
            analysis = section.get("analysis", "").replace("\n", "<br>")
            title_slug = title.replace(" ", "_").replace("&", "and").lower()

            chips_html = ""
            for dp in section.get("key_data_points", []):
                direction = dp.get("direction", "flat")
                arrow = {"up": "▲", "down": "▼", "flat": "—"}.get(direction, "—")
                color = {"up": GREEN, "down": RED, "flat": TEXT_MUTED}.get(direction, TEXT_MUTED)
                chips_html += f'<tr><td style="padding:6px 12px;font-family:{FONT};font-size:13px;color:{TEXT_MUTED};border-bottom:1px solid {BORDER};">{dp.get("label","")}</td><td style="padding:6px 12px;font-family:{FONT};font-size:15px;font-weight:700;color:{TEXT_BRIGHT};text-align:right;border-bottom:1px solid {BORDER};">{dp.get("value","")}</td><td style="padding:6px 12px;font-family:{FONT};font-size:12px;color:{color};text-align:right;border-bottom:1px solid {BORDER};">{arrow} {dp.get("change","")}</td></tr>'

            chips_block = ""
            if chips_html:
                chips_block = f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;margin:16px 0;">{chips_html}</table>'

            chart_html = ""
            for i, cs in enumerate(section.get("chart_suggestions", [])):
                chart_id = f"chart_{title_slug}_{i}"
                filename = charts.get(chart_id)
                if filename and self.chart_base_url:
                    img_url = f"{self.chart_base_url}/{filename}"
                    chart_html += f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;border:1px solid {BORDER};border-radius:8px;overflow:hidden;"><tr><td style="padding:4px;"><img src="{img_url}" alt="{cs.get("title","Chart")}" width="640" style="width:100%;max-width:640px;height:auto;display:block;"></td></tr><tr><td style="padding:8px 14px 14px;font-family:{FONT};font-size:12px;color:{TEXT_MUTED};font-style:italic;line-height:1.5;">{cs.get("interpretation","")}</td></tr></table>'

            consensus = section.get("consensus_view", "")
            contrarian = section.get("contrarian_view", "")
            views_html = ""
            if consensus or contrarian:
                views_html = f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;"><tr><td valign="top" style="width:49%;padding-right:6px;"><table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {ACCENT};border-radius:6px;"><tr><td style="padding:12px 14px 4px;font-family:{FONT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:{ACCENT};">Consensus View</td></tr><tr><td style="padding:4px 14px 14px;font-family:{FONT};font-size:13px;line-height:1.6;color:{TEXT};">{consensus}</td></tr></table></td><td valign="top" style="width:49%;padding-left:6px;"><table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {AMBER};border-radius:6px;"><tr><td style="padding:12px 14px 4px;font-family:{FONT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:{AMBER};">Contrarian View</td></tr><tr><td style="padding:4px 14px 14px;font-family:{FONT};font-size:13px;line-height:1.6;color:{TEXT};">{contrarian}</td></tr></table></td></tr></table>'

            parts.append(f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;"><tr><td style="padding-bottom:10px;border-bottom:2px solid {BORDER};font-family:{FONT};font-size:20px;font-weight:700;color:{TEXT_BRIGHT};">{icon} {title}</td></tr><tr><td style="padding-top:14px;font-family:{FONT};font-size:14px;line-height:1.8;color:{TEXT};">{analysis}</td></tr><tr><td>{chips_block}</td></tr><tr><td>{chart_html}</td></tr><tr><td>{views_html}</td></tr></table>')
        return "\n".join(parts)

    def _build_dashboard(self, dashboard):
        if not dashboard:
            return ""
        categories = {
            "rates": ("Rates & Yields", ACCENT),
            "inflation": ("Inflation", RED),
            "labor": ("Labor Market", "#7c3aed"),
            "activity": ("Activity & Output", GREEN),
            "financial_conditions": ("Financial Conditions", AMBER),
            "global": ("Global", "#0891b2"),
        }
        panels = []
        for key, (label, color) in categories.items():
            items = dashboard.get(key, [])
            if not items:
                continue
            rows = ""
            for item in items:
                direction = item.get("direction", "flat")
                arrow = {"up": "▲", "down": "▼", "flat": "—"}.get(direction, "—")
                chg_color = {"up": GREEN, "down": RED, "flat": TEXT_MUTED}.get(direction, TEXT_MUTED)
                rows += f'<tr><td style="padding:6px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">{item.get("label","")}</td><td style="padding:6px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;font-weight:600;color:{TEXT_BRIGHT};text-align:right;">{item.get("value","")}</td><td style="padding:6px 10px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:12px;color:{chg_color};text-align:right;white-space:nowrap;">{arrow} {item.get("change","")}</td></tr>'
            panels.append(f'<td valign="top" style="width:49%;padding:0 4px 12px;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:8px;overflow:hidden;"><tr><td style="padding:10px 12px;background:{BG_CARD_ALT};border-left:4px solid {color};font-family:{FONT};font-size:13px;font-weight:700;color:{TEXT_BRIGHT};">{label}</td></tr><tr><td><table width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr></table></td>')
        grid_rows = []
        for i in range(0, len(panels), 2):
            pair = panels[i:i+2]
            if len(pair) == 1:
                pair.append("<td></td>")
            grid_rows.append(f"<tr>{''.join(pair)}</tr>")
        return f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;"><tr><td style="padding-bottom:10px;border-bottom:2px solid {BORDER};font-family:{FONT};font-size:20px;font-weight:700;color:{TEXT_BRIGHT};">Data Dashboard</td></tr><tr><td style="padding-top:16px;"><table width="100%" cellpadding="0" cellspacing="0">{"".join(grid_rows)}</table></td></tr></table>'

    def _build_week_ahead(self, week_ahead):
        if not week_ahead:
            return ""
        catalysts = week_ahead.get("catalysts", [])
        releases = week_ahead.get("data_releases", [])
        risks = week_ahead.get("risks", [])
        cat_rows = "".join(f'<tr><td style="padding:7px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">&#8226; {c}</td></tr>' for c in catalysts)
        risk_rows = "".join(f'<tr><td style="padding:7px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">&#9888; {r}</td></tr>' for r in risks)
        release_rows = ""
        for r in releases:
            release_rows += f'<tr><td style="padding:6px 8px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:12px;color:{TEXT_MUTED};white-space:nowrap;">{r.get("date","")}</td><td style="padding:6px 8px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT};">{r.get("release","")}</td><td style="padding:6px 8px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT_BRIGHT};text-align:right;">{r.get("prior","—")}</td><td style="padding:6px 8px;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{TEXT_BRIGHT};text-align:right;">{r.get("consensus","—")}</td></tr>'
        return f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;"><tr><td style="padding-bottom:10px;border-bottom:2px solid {BORDER};font-family:{FONT};font-size:20px;font-weight:700;color:{TEXT_BRIGHT};">Week Ahead</td></tr><tr><td style="padding-top:16px;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td valign="top" style="width:49%;padding-right:6px;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:8px;"><tr><td style="padding:12px 14px 6px;font-family:{FONT};font-size:14px;font-weight:700;color:{TEXT_BRIGHT};">Key Catalysts</td></tr><tr><td style="padding:0 14px 12px;"><table width="100%" cellpadding="0" cellspacing="0">{cat_rows}</table></td></tr></table></td><td valign="top" style="width:49%;padding-left:6px;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:8px;"><tr><td style="padding:12px 14px 6px;font-family:{FONT};font-size:14px;font-weight:700;color:{TEXT_BRIGHT};">Risks to Watch</td></tr><tr><td style="padding:0 14px 12px;"><table width="100%" cellpadding="0" cellspacing="0">{risk_rows}</table></td></tr></table></td></tr></table></td></tr><tr><td style="padding-top:12px;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:8px;"><tr><td style="padding:12px 14px 6px;font-family:{FONT};font-size:14px;font-weight:700;color:{TEXT_BRIGHT};">Data Calendar</td></tr><tr><td style="padding:0 14px 12px;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:6px 8px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:2px solid {BORDER};">Date</td><td style="padding:6px 8px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:2px solid {BORDER};">Release</td><td style="padding:6px 8px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:2px solid {BORDER};text-align:right;">Prior</td><td style="padding:6px 8px;font-family:{FONT};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{TEXT_MUTED};border-bottom:2px solid {BORDER};text-align:right;">Consensus</td></tr>{release_rows}</table></td></tr></table></td></tr></table>'

    def _wrap_email(self, **kw):
        exec_paragraphs = "".join(
            f'<p style="margin:0 0 12px;font-family:{FONT};font-size:14px;line-height:1.7;color:{TEXT};">{p.strip()}</p>'
            for p in kw["executive_summary"].split("\n") if p.strip()
        )
        return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;">
<tr><td align="center" style="padding:24px 12px;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:660px;background:{BG};">
<tr><td align="center" style="padding:36px 28px 28px;border-bottom:2px solid {BORDER};">
<div style="font-family:{FONT};font-size:11px;letter-spacing:3px;text-transform:uppercase;color:{ACCENT};margin-bottom:12px;">Weekly Market Economist Brief</div>
<div style="font-family:Georgia,serif;font-size:28px;font-weight:400;color:{TEXT_BRIGHT};line-height:1.2;margin-bottom:8px;">{kw["week_label"]}</div>
<div style="font-family:{FONT};font-size:13px;color:{TEXT_MUTED};">Published {kw["report_date"]}</div>
</td></tr>
<tr><td style="padding:28px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;border-top:3px solid {ACCENT};">
<tr><td style="padding:22px 22px 6px;font-family:Georgia,serif;font-size:18px;font-weight:700;color:{TEXT_BRIGHT};">Executive Summary</td></tr>
<tr><td style="padding:6px 22px 22px;">{exec_paragraphs}</td></tr>
</table>
</td></tr>
<tr><td style="padding:0 28px;">{kw["sections_html"]}</td></tr>
<tr><td style="padding:0 28px;">{kw["dashboard_html"]}</td></tr>
<tr><td style="padding:0 28px;">{kw["week_ahead_html"]}</td></tr>
<tr><td style="padding:0 28px 28px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid {ACCENT};border-radius:8px;">
<tr><td style="padding:18px 20px 6px;font-family:{FONT};font-size:16px;font-weight:700;color:{TEXT_BRIGHT};">The Bottom Line</td></tr>
<tr><td style="padding:6px 20px 18px;font-family:{FONT};font-size:14px;line-height:1.8;color:{TEXT};">{kw["bottom_line"]}</td></tr>
</table>
</td></tr>
<tr><td align="center" style="padding:24px 28px;border-top:1px solid {BORDER};">
<div style="font-family:{FONT};font-size:11px;color:{TEXT_MUTED};line-height:1.8;">
Generated by Financial Market Economist Agent<br>
This report is for informational purposes only and does not constitute investment advice.
</div>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>'''
