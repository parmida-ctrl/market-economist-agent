"""
Chart renderer — creates static PNG chart images using matplotlib.
These are embedded as base64 in the email since Gmail can't run JavaScript.
"""

import io
import base64
import logging
from typing import Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime

logger = logging.getLogger("agent.charts")

# -- Dark theme matching the report aesthetic --
COLORS = {
    "bg": "#0f172a",
    "card_bg": "#1e293b",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
    "accent": "#3b82f6",
    "green": "#10b981",
    "red": "#ef4444",
    "purple": "#8b5cf6",
    "amber": "#f59e0b",
    "grid": "#334155",
    "border": "#475569",
}

LINE_COLORS = [
    COLORS["accent"],
    COLORS["purple"],
    COLORS["green"],
    COLORS["red"],
    COLORS["amber"],
]


def _setup_style():
    """Apply dark theme styling to matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": COLORS["card_bg"],
        "axes.facecolor": COLORS["card_bg"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text_muted"],
        "text.color": COLORS["text"],
        "xtick.color": COLORS["text_muted"],
        "ytick.color": COLORS["text_muted"],
        "grid.color": COLORS["grid"],
        "grid.alpha": 0.3,
        "font.family": ["DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "figure.dpi": 150,
    })


def render_chart_to_base64(
    dates: list[str],
    values: list[float],
    title: str,
    units: str = "",
    color: str = None,
    target_line: float = None,
    target_label: str = None,
    fill: bool = True,
    width: float = 7.5,
    height: float = 2.8,
) -> str:
    """
    Render a line chart and return it as a base64-encoded PNG string.

    Returns a string like: data:image/png;base64,iVBOR...
    """
    _setup_style()

    fig, ax = plt.subplots(figsize=(width, height))

    line_color = color or COLORS["accent"]

    # Parse dates
    try:
        parsed_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
    except ValueError:
        # Fallback: use as-is for x-axis
        parsed_dates = list(range(len(dates)))

    ax.plot(
        parsed_dates, values,
        color=line_color,
        linewidth=2,
        solid_capstyle="round",
    )

    if fill:
        ax.fill_between(
            parsed_dates, values,
            alpha=0.08,
            color=line_color,
        )

    # Target / reference line
    if target_line is not None:
        ax.axhline(
            y=target_line,
            color=COLORS["green"],
            linewidth=1,
            linestyle="--",
            alpha=0.6,
            label=target_label or "",
        )
        if target_label:
            ax.legend(
                loc="upper right",
                fontsize=8,
                facecolor=COLORS["card_bg"],
                edgecolor=COLORS["grid"],
                labelcolor=COLORS["text_muted"],
            )

    ax.set_title(title, pad=12, loc="left")

    if units:
        ax.set_ylabel(units, fontsize=9)

    ax.grid(True, axis="y", linewidth=0.5)
    ax.grid(False, axis="x")

    # Format x-axis dates
    if isinstance(parsed_dates[0], datetime):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        fig.autofmt_xdate(rotation=0, ha="center")

    ax.tick_params(axis="both", which="major", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout(pad=1.5)

    # Export to base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def render_fred_charts(sections: list, fred_data: list) -> dict:
    """
    Render all chart suggestions from the synthesis output.

    Returns: dict mapping chart_id → base64 PNG string
    """
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
            chart_title = cs.get("title", series_data["name"])
            units = series_data["units"]

            # Use a target line for inflation charts
            target = None
            target_label = None
            if "pce" in series_id.lower() or "cpi" in series_id.lower() or "inflation" in chart_title.lower():
                target = 2.0
                target_label = "2% Target"

            try:
                b64_img = render_chart_to_base64(
                    dates=dates,
                    values=values,
                    title=chart_title,
                    units=units,
                    color=LINE_COLORS[color_index % len(LINE_COLORS)],
                    target_line=target,
                    target_label=target_label,
                )
                charts[chart_id] = b64_img
                color_index += 1
            except Exception as e:
                logger.warning(f"Failed to render chart {chart_id}: {e}")

    return charts
