"""Small SVG plotting helpers with no third-party dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html
import math
from typing import Sequence


Color = str
Point = tuple[float, float]


@dataclass(frozen=True)
class Series:
    label: str
    points: tuple[Point, ...]
    color: Color = "#111111"
    mode: str = "points"  # points, line, both
    radius: float = 0.75
    stroke_width: float = 1.4
    opacity: float = 1.0
    marker: str = "circle"  # circle, square


@dataclass(frozen=True)
class Panel:
    title: str
    xlabel: str
    ylabel: str
    series: tuple[Series, ...]
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    grid: bool = False
    aspect: float | None = None
    xticks: tuple[float, ...] | None = None
    yticks: tuple[float, ...] | None = None


PALETTE = (
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#9467bd",
    "#ff7f0e",
    "#17becf",
)


def _nice_number(value: float, round_value: bool) -> float:
    if value == 0 or not math.isfinite(value):
        return 1.0
    exponent = math.floor(math.log10(abs(value)))
    fraction = abs(value) / 10**exponent
    if round_value:
        if fraction < 1.5:
            nice_fraction = 1
        elif fraction < 3:
            nice_fraction = 2
        elif fraction < 7:
            nice_fraction = 5
        else:
            nice_fraction = 10
    else:
        if fraction <= 1:
            nice_fraction = 1
        elif fraction <= 2:
            nice_fraction = 2
        elif fraction <= 5:
            nice_fraction = 5
        else:
            nice_fraction = 10
    return math.copysign(nice_fraction * 10**exponent, value)


def _ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    if not math.isfinite(lo) or not math.isfinite(hi) or lo == hi:
        return [lo]
    span = _nice_number(hi - lo, False)
    step = _nice_number(span / max(1, target - 1), True)
    first = math.ceil(lo / step) * step
    vals = []
    x = first
    while x <= hi + 0.5 * step:
        vals.append(0.0 if abs(x) < 1.0e-12 else x)
        x += step
    return vals


def _format_tick(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _bounds(panel: Panel) -> tuple[tuple[float, float], tuple[float, float]]:
    xs = [x for series in panel.series for x, _ in series.points if math.isfinite(x)]
    ys = [y for series in panel.series for _, y in series.points if math.isfinite(y)]
    xlim = panel.xlim if panel.xlim else (min(xs), max(xs))
    ylim = panel.ylim if panel.ylim else (min(ys), max(ys))
    if xlim[0] == xlim[1]:
        xlim = (xlim[0] - 0.5, xlim[1] + 0.5)
    if ylim[0] == ylim[1]:
        ylim = (ylim[0] - 0.5, ylim[1] + 0.5)
    return xlim, ylim


def _point_path(points: Sequence[Point], sx, sy, radius: float, marker: str) -> str:
    r = radius
    chunks = []
    for x, y in points:
        if math.isfinite(x) and math.isfinite(y):
            px = sx(x)
            py = sy(y)
            if marker == "square":
                chunks.append(f"M{px-r:.2f},{py-r:.2f}h{2*r:.2f}v{2*r:.2f}h-{2*r:.2f}z")
            else:
                chunks.append(f"M{px:.2f},{py:.2f}m-{r:.2f},0a{r:.2f},{r:.2f} 0 1,0 {2*r:.2f},0a{r:.2f},{r:.2f} 0 1,0 -{2*r:.2f},0")
    return "".join(chunks)


def _polyline(points: Sequence[Point], sx, sy) -> str:
    out = []
    current = []
    for x, y in points:
        if math.isfinite(x) and math.isfinite(y):
            current.append(f"{sx(x):.2f},{sy(y):.2f}")
        elif current:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def save_svg_grid(
    path: str | Path,
    panels: Sequence[Panel],
    *,
    columns: int = 2,
    width: int = 1200,
    panel_height: int = 430,
    title: str | None = None,
) -> None:
    """Save a grid of panels as a self-contained SVG file."""

    path = Path(path)
    rows = math.ceil(len(panels) / columns)
    height = rows * panel_height + (58 if title else 18)
    panel_width = width / columns
    top_offset = 52 if title else 12
    margin = dict(left=74, right=22, top=44, bottom=62)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:'Times New Roman',Times,serif;fill:#111}",
        ".axis{stroke:#111;stroke-width:1.7}",
        ".grid{stroke:#d8d8d8;stroke-width:.75}",
        ".title{font-size:20px;font-weight:700}",
        ".panel-title{font-size:15px;font-weight:700}",
        ".label{font-size:13px}",
        ".tick{font-size:11px;fill:#444}",
        ".legend{font-size:12px}",
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    if title:
        parts.append(f'<text class="title" x="{width/2:.1f}" y="30" text-anchor="middle">{html.escape(title)}</text>')

    for idx, panel in enumerate(panels):
        col = idx % columns
        row = idx // columns
        ox = col * panel_width
        oy = top_offset + row * panel_height
        plot_x = ox + margin["left"]
        plot_y = oy + margin["top"]
        plot_w = panel_width - margin["left"] - margin["right"]
        plot_h = panel_height - margin["top"] - margin["bottom"]
        if panel.aspect is not None:
            current = plot_w / plot_h
            if current > panel.aspect:
                adjusted_w = plot_h * panel.aspect
                plot_x += 0.5 * (plot_w - adjusted_w)
                plot_w = adjusted_w
            else:
                adjusted_h = plot_w / panel.aspect
                plot_y += 0.5 * (plot_h - adjusted_h)
                plot_h = adjusted_h
        xlim, ylim = _bounds(panel)
        xmin, xmax = xlim
        ymin, ymax = ylim
        xpad = 0 if panel.xlim else 0.03 * (xmax - xmin)
        ypad = 0 if panel.ylim else 0.05 * (ymax - ymin)
        xmin -= xpad
        xmax += xpad
        ymin -= ypad
        ymax += ypad

        def sx(x, xmin=xmin, xmax=xmax, plot_x=plot_x, plot_w=plot_w):
            return plot_x + (x - xmin) / (xmax - xmin) * plot_w

        def sy(y, ymin=ymin, ymax=ymax, plot_y=plot_y, plot_h=plot_h):
            return plot_y + plot_h - (y - ymin) / (ymax - ymin) * plot_h

        clip_id = f"clip-panel-{idx+1}"
        parts.append(f'<g id="panel-{idx+1}">')
        parts.append("<defs>")
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}"/></clipPath>'
        )
        parts.append("</defs>")
        parts.append(
            f'<text class="panel-title" x="{plot_x + plot_w/2:.1f}" y="{oy + 21:.1f}" text-anchor="middle">{html.escape(panel.title)}</text>'
        )
        parts.append(f'<rect x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}" fill="#fff"/>')

        xticks = panel.xticks if panel.xticks is not None else tuple(_ticks(xmin, xmax))
        yticks = panel.yticks if panel.yticks is not None else tuple(_ticks(ymin, ymax))

        for xtick in xticks:
            x = sx(xtick)
            if panel.grid:
                parts.append(f'<line class="grid" x1="{x:.1f}" y1="{plot_y:.1f}" x2="{x:.1f}" y2="{plot_y+plot_h:.1f}"/>')
            parts.append(f'<line class="axis" x1="{x:.1f}" y1="{plot_y+plot_h:.1f}" x2="{x:.1f}" y2="{plot_y+plot_h+5:.1f}"/>')
            parts.append(f'<text class="tick" x="{x:.1f}" y="{plot_y+plot_h+20:.1f}" text-anchor="middle">{_format_tick(xtick)}</text>')
        for ytick in yticks:
            y = sy(ytick)
            if panel.grid:
                parts.append(f'<line class="grid" x1="{plot_x:.1f}" y1="{y:.1f}" x2="{plot_x+plot_w:.1f}" y2="{y:.1f}"/>')
            parts.append(f'<line class="axis" x1="{plot_x-5:.1f}" y1="{y:.1f}" x2="{plot_x:.1f}" y2="{y:.1f}"/>')
            parts.append(f'<text class="tick" x="{plot_x-9:.1f}" y="{y+4:.1f}" text-anchor="end">{_format_tick(ytick)}</text>')

        parts.append(f'<rect class="axis" x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}" fill="none"/>')

        parts.append(f'<g clip-path="url(#{clip_id})">')
        for series in panel.series:
            escaped_label = html.escape(series.label)
            if series.mode in ("line", "both"):
                for line in _polyline(series.points, sx, sy):
                    parts.append(
                        f'<polyline points="{line}" fill="none" stroke="{series.color}" stroke-width="{series.stroke_width:.2f}" stroke-linejoin="round" stroke-linecap="round"><title>{escaped_label}</title></polyline>'
                    )
            if series.mode in ("points", "both"):
                path_data = _point_path(series.points, sx, sy, series.radius, series.marker)
                parts.append(f'<path d="{path_data}" fill="{series.color}" opacity="{series.opacity:.3f}"><title>{escaped_label}</title></path>')
        parts.append("</g>")

        parts.append(
            f'<text class="label" x="{plot_x + plot_w/2:.1f}" y="{plot_y + plot_h + 46:.1f}" text-anchor="middle">{html.escape(panel.xlabel)}</text>'
        )
        parts.append(
            f'<text class="label" transform="translate({plot_x - 54:.1f},{plot_y + plot_h/2:.1f}) rotate(-90)" text-anchor="middle">{html.escape(panel.ylabel)}</text>'
        )

        if any(s.label for s in panel.series):
            lx = plot_x + 9
            ly = plot_y + 17
            for si, series in enumerate(panel.series):
                if not series.label:
                    continue
                yy = ly + si * 17
                parts.append(f'<line x1="{lx:.1f}" y1="{yy-4:.1f}" x2="{lx+17:.1f}" y2="{yy-4:.1f}" stroke="{series.color}" stroke-width="2"/>')
                parts.append(f'<text class="legend" x="{lx+23:.1f}" y="{yy:.1f}">{html.escape(series.label)}</text>')

        parts.append("</g>")

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")
