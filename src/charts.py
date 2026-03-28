"""
Chart renderer — creates static PNG chart images using matplotlib.
Saves them to disk so they can be uploaded to GitHub Pages and
referenced by URL in the email (Gmail blocks base64 images).
"""

import os
import logging
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

logger = logging.getLogger("agent.charts")

COLORS = {
    "bg": "#ffffff",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "accent": "#2563eb",
    "green": "#059669",
    "red": "#dc2626",
    "purple": "#7c3aed",
    "amber": "#d97706",
    "grid": "#e2e8f0",
}

LINE_COLORS = [
    COLORS["accent"],
    COLORS["purple"],
    COLORS["green"],
    COLORS["red"],
    COLORS["amber"],
]


def _setup_style():
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["bg"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text_muted"],
        "text.color": COLORS["text"],
        "xtick.color": COLORS["text_muted"],
        "ytick.color": COLORS["text_muted"],
        "grid.color": COLORS["grid"],
        "grid.alpha": 0.6,
        "font.family": ["DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "figure.dpi": 150,
    })


def render_chart_to_file(dates, values, title, filepath, units="", color=None, target_line=None, target_label=None, fill=True, width=7.0, height=2.5):
    _setup_style()
    fig, ax = plt.subplots(figsize=(width, height))
    line_color = color or COLORS["accent"]

    try:
        parsed_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
    except ValueError:
        parsed_dates = list(range(len(dates)))

    ax.plot(parsed_dates, values, color=line_color, linewidth=2, solid_capstyle="round")
    if fill:
        ax.fill_between(parsed_dates, values, alpha=0.06, color=line_color)
    if target_line is not None:
        ax.axhline(y=target_line, color=COLORS["green"], linewidth=1, linestyle="--", alpha=0.7, label=target_label or "")
        if target_label:
            ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    ax.set_title(title, pad=10, loc="left")
    if units:
        ax.set_ylabel(units, fontsize=9)
    ax.grid(True, axis="y", linewidth=0.5)
    ax.grid(False, axis="x")
    if isinstance(parsed_dates[0], datetime):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        fig.autofmt_xdate(rotation=0, ha="center")
    ax.tick_params(axis="both", which="major", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout(pad=1.2)
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filepath, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"  Chart saved: {filepath}")


def render_fred_charts(sections, fred_data, output_dir="output/charts"):
    fred_lookup = {}
    for series in fred_data:
        fred_lookup[series.series_id] = {
            "name": series.name,
            "observations": list(reversed(series.observations[:60])),
            "units": series.units,
        }

    charts = {}
    color_index = 0
    for section in sections:
        title_slug = section.get("title", "").replace(" ", "_").replace("&", "and").lower()
        for i, cs in enumerate(section.get("chart_suggestions", [])):
            chart_id = f"chart_{title_slug}_{i}"
            series_id = cs.get("fred_series", "")
            series_data = fred_lookup.get(series_id)
            if not series_data or not series_data["observations"]:
                continue
            dates = [o["date"] for o in series_data["observations"]]
            values = [o["value"] for o in series_data["observations"]]
            target = None
            target_label = None
            if "pce" in series_id.lower() or "cpi" in series_id.lower():
                target = 2.0
                target_label = "2% Target"
            filename = f"{chart_id}.png"
            filepath = os.path.join(output_dir, filename)
            try:
                render_chart_to_file(
                    dates=dates, values=values, title=cs.get("title", series_data["name"]),
                    filepath=filepath, units=series_data["units"],
                    color=LINE_COLORS[color_index % len(LINE_COLORS)],
                    target_line=target, target_label=target_label,
                )
                charts[chart_id] = filename
                color_index += 1
            except Exception as e:
                logger.warning(f"Failed to render chart {chart_id}: {e}")
    return charts
