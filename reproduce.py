"""Reproduce the numerical figures from "Chaos control and schedule of shuttle buses".

Run:
    python reproduce.py

The script writes CSV data and SVG figures to outputs/.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

from shuttle_bus import (
    classify_motion,
    equal_speed_transition_formula,
    estimate_equal_speed_transition,
    gamma_values,
    inclusive_window,
    mean,
    rms_variation,
    simulate,
)
from svg_plot import PALETTE, Panel, Series, save_svg_grid


SPEED_CASES = (
    ("a", "S1=S2=0", (0.0, 0.0)),
    ("b", "S1=S2=0.2", (0.2, 0.2)),
    ("c", "S1=0.3, S2=0.2", (0.3, 0.2)),
    ("d", "S1=0.5, S2=0.2", (0.5, 0.2)),
)
FOCUS_SPEEDS = (0.5, 0.2)
SAMPLE_START = 900
SAMPLE_STOP = 1000
RETURN_START = 1000
RETURN_STOP = 2000
GAMMA_FULL_DOMAIN = (0.0, 2.0)
GAMMA_ZOOM_DOMAIN = (0.0, 0.5)
GAMMA_FULL_FRAME = (0.0, 2.05)
GAMMA_ZOOM_FRAME = (0.0, 0.5)
GAMMA_FULL_TICKS = (0.0, 0.5, 1.0, 1.5, 2.0)
GAMMA_ZOOM_TICKS = (0.0, 0.2, 0.4)
HEADWAY_FULL_TICKS = (0.0, 2.0, 4.0, 6.0)
HEADWAY_ZOOM_TICKS = (0.0, 0.5, 1.0, 1.5)
TOUR_ZOOM_TICKS = (0.75, 1.0, 1.25, 1.5)
RETURN_TICKS = (0.0, 0.5, 1.0, 1.5)


def write_csv(path: Path, header: tuple[str, ...], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def fmt_param(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def in_open_domain(value: float, domain: tuple[float, float]) -> bool:
    low, high = domain
    return low < value < high


def headway_bifurcation(out_data: Path, out_fig: Path, gammas: tuple[float, ...]) -> None:
    full_panels = []
    zoom_panels = []
    for case_id, label, speeds in SPEED_CASES:
        rows = []
        points = []
        zoom_points = []
        for gamma in gammas:
            if not in_open_domain(gamma, GAMMA_FULL_DOMAIN):
                continue
            result = simulate(gamma, speeds, trips=SAMPLE_STOP + 1)
            h1 = inclusive_window(result.headways[0], SAMPLE_START, SAMPLE_STOP)
            for offset, value in enumerate(h1):
                trip = SAMPLE_START + offset
                rows.append((f"{gamma:.10g}", trip, f"{value:.12g}", result.diverged))
                points.append((gamma, value))
                if in_open_domain(gamma, GAMMA_ZOOM_DOMAIN):
                    zoom_points.append((gamma, value))
        write_csv(
            out_data / f"fig2_fig3_headway_case_{case_id}.csv",
            ("gamma", "trip_m", "H1_m", "diverged"),
            rows,
        )
        full_panels.append(
            Panel(
                title=f"({case_id}) {label}",
                xlabel="Loading parameter Gamma",
                ylabel="H1(m)",
                series=(Series("", tuple(points), "#000000", "points", radius=0.65, marker="square"),),
                xlim=GAMMA_FULL_FRAME,
                ylim=(0.0, 6.0),
                xticks=GAMMA_FULL_TICKS,
                yticks=HEADWAY_FULL_TICKS,
            )
        )
        zoom_panels.append(
            Panel(
                title=f"({case_id}) {label}",
                xlabel="Loading parameter Gamma",
                ylabel="H1(m)",
                series=(Series("", tuple(zoom_points), "#000000", "points", radius=0.9, marker="square"),),
                xlim=GAMMA_ZOOM_FRAME,
                ylim=(0.0, 1.5),
                xticks=GAMMA_ZOOM_TICKS,
                yticks=HEADWAY_ZOOM_TICKS,
            )
        )
    save_svg_grid(out_fig / "fig2_headway_bifurcation.svg", full_panels, title="Fig. 2 reproduction: H1(m), trips 900-1000")
    save_svg_grid(out_fig / "fig3_headway_bifurcation_zoom.svg", zoom_panels, title="Fig. 3 reproduction: enlargement 0 < Gamma < 0.5")


def tour_time_bifurcation(out_data: Path, out_fig: Path, gammas: tuple[float, ...]) -> None:
    rows = []
    bus_points = [[], []]
    bus_zoom_points = [[], []]
    for gamma in gammas:
        if not in_open_domain(gamma, GAMMA_FULL_DOMAIN):
            continue
        result = simulate(gamma, FOCUS_SPEEDS, trips=SAMPLE_STOP + 1)
        dt1 = inclusive_window(result.tour_times[0], SAMPLE_START, SAMPLE_STOP)
        dt2 = inclusive_window(result.tour_times[1], SAMPLE_START, SAMPLE_STOP)
        for offset, (v1, v2) in enumerate(zip(dt1, dt2)):
            trip = SAMPLE_START + offset
            rows.append((f"{gamma:.10g}", trip, f"{v1:.12g}", f"{v2:.12g}", result.diverged))
            bus_points[0].append((gamma, v1))
            bus_points[1].append((gamma, v2))
            if in_open_domain(gamma, GAMMA_ZOOM_DOMAIN):
                bus_zoom_points[0].append((gamma, v1))
                bus_zoom_points[1].append((gamma, v2))
    write_csv(
        out_data / "fig4_fig5_tour_times_s1_0p5_s2_0p2.csv",
        ("gamma", "trip_m", "DT1_m", "DT2_m", "diverged"),
        rows,
    )

    panels = [
        Panel("(a) Bus 1", "Loading parameter Gamma", "Delta T1(m)", (Series("", tuple(bus_points[0]), "#000000", "points", radius=0.65, marker="square"),), xlim=GAMMA_FULL_FRAME, ylim=(0, 6.0), xticks=GAMMA_FULL_TICKS, yticks=HEADWAY_FULL_TICKS),
        Panel("(b) Bus 2", "Loading parameter Gamma", "Delta T2(m)", (Series("", tuple(bus_points[1]), "#000000", "points", radius=0.65, marker="square"),), xlim=GAMMA_FULL_FRAME, ylim=(0, 6.0), xticks=GAMMA_FULL_TICKS, yticks=HEADWAY_FULL_TICKS),
    ]
    zoom_panels = [
        Panel("(a) Bus 1", "Loading parameter Gamma", "Delta T1(m)", (Series("", tuple(bus_zoom_points[0]), "#000000", "points", radius=0.9, marker="square"),), xlim=GAMMA_ZOOM_FRAME, ylim=(0.75, 1.5), xticks=GAMMA_ZOOM_TICKS, yticks=TOUR_ZOOM_TICKS),
        Panel("(b) Bus 2", "Loading parameter Gamma", "Delta T2(m)", (Series("", tuple(bus_zoom_points[1]), "#000000", "points", radius=0.9, marker="square"),), xlim=GAMMA_ZOOM_FRAME, ylim=(0.75, 1.5), xticks=GAMMA_ZOOM_TICKS, yticks=TOUR_ZOOM_TICKS),
    ]
    save_svg_grid(out_fig / "fig4_tour_times.svg", panels, columns=2, title="Fig. 4 reproduction: tour times, S1=0.5, S2=0.2")
    save_svg_grid(out_fig / "fig5_tour_times_zoom.svg", zoom_panels, columns=2, title="Fig. 5 reproduction: enlargement 0 < Gamma < 0.5")


def return_maps(out_data: Path, out_fig: Path) -> None:
    panels = []
    for idx, gamma in enumerate((0.2, 0.3, 0.5, 0.8), start=1):
        result = simulate(gamma, FOCUS_SPEEDS, trips=RETURN_STOP + 2)
        h1 = result.headways[0]
        rows = []
        points = []
        for m in range(RETURN_START, RETURN_STOP + 1):
            if m + 1 >= len(h1):
                continue
            x = h1[m]
            y = h1[m + 1]
            rows.append((m, f"{x:.12g}", f"{y:.12g}"))
            points.append((x, y))
        write_csv(out_data / f"fig6_return_map_gamma_{fmt_param(gamma)}.csv", ("trip_m", "H1_m", "H1_m_plus_1"), rows)
        motion = classify_motion(tuple(x for _, x in points))
        panels.append(
            Panel(
                f"({chr(96 + idx)}) Gamma={gamma:g}, {motion}",
                "H1(m)",
                "H1(m+1)",
                (
                    Series("", ((0.0, 0.0), (1.5, 1.5)), "#777777", "line", stroke_width=1.1),
                    Series("", tuple(points), "#000000", "points", radius=1.25, marker="square"),
                ),
                xlim=(0.0, 1.5),
                ylim=(0.0, 1.5),
                aspect=1.0,
                xticks=RETURN_TICKS,
                yticks=RETURN_TICKS,
            )
        )
    save_svg_grid(out_fig / "fig6_return_maps.svg", panels, title="Fig. 6 reproduction: return maps, S1=0.5, S2=0.2")


def mean_and_rms(out_data: Path, out_fig: Path, gammas: tuple[float, ...]) -> None:
    rows = []
    mean_series = {name: [] for name in ("H1a", "H2a", "DT1a", "DT2a")}
    rms_series = {name: [] for name in ("H1v", "H2v", "DT1v", "DT2v")}
    mean_zoom = {name: [] for name in mean_series}
    rms_zoom = {name: [] for name in rms_series}

    for gamma in gammas:
        if not in_open_domain(gamma, GAMMA_FULL_DOMAIN):
            continue
        result = simulate(gamma, FOCUS_SPEEDS, trips=SAMPLE_STOP + 1)
        samples = {
            "H1": inclusive_window(result.headways[0], SAMPLE_START, SAMPLE_STOP),
            "H2": inclusive_window(result.headways[1], SAMPLE_START, SAMPLE_STOP),
            "DT1": inclusive_window(result.tour_times[0], SAMPLE_START, SAMPLE_STOP),
            "DT2": inclusive_window(result.tour_times[1], SAMPLE_START, SAMPLE_STOP),
        }
        stats = {
            "H1a": mean(samples["H1"]),
            "H2a": mean(samples["H2"]),
            "DT1a": mean(samples["DT1"]),
            "DT2a": mean(samples["DT2"]),
            "H1v": rms_variation(samples["H1"]),
            "H2v": rms_variation(samples["H2"]),
            "DT1v": rms_variation(samples["DT1"]),
            "DT2v": rms_variation(samples["DT2"]),
        }
        rows.append((f"{gamma:.10g}",) + tuple(f"{stats[k]:.12g}" for k in ("H1a", "H2a", "DT1a", "DT2a", "H1v", "H2v", "DT1v", "DT2v")) + (result.diverged,))
        for name in mean_series:
            mean_series[name].append((gamma, stats[name]))
            if in_open_domain(gamma, GAMMA_ZOOM_DOMAIN):
                mean_zoom[name].append((gamma, stats[name]))
        for name in rms_series:
            rms_series[name].append((gamma, stats[name]))
            if in_open_domain(gamma, GAMMA_ZOOM_DOMAIN):
                rms_zoom[name].append((gamma, stats[name]))

    write_csv(
        out_data / "fig7_mean_rms_s1_0p5_s2_0p2.csv",
        ("gamma", "H1a", "H2a", "DT1a", "DT2a", "H1v", "H2v", "DT1v", "DT2v", "diverged"),
        rows,
    )

    def series_tuple(source: dict[str, list[tuple[float, float]]], names: tuple[str, ...]) -> tuple[Series, ...]:
        return tuple(Series(name, tuple(source[name]), PALETTE[i], "line", radius=0.0, stroke_width=2.0) for i, name in enumerate(names))

    panels = [
        Panel("(a) Means", "Loading parameter Gamma", "Mean value", series_tuple(mean_series, ("H1a", "H2a", "DT1a", "DT2a")), xlim=GAMMA_FULL_FRAME, ylim=(0, 5.0), xticks=GAMMA_FULL_TICKS),
        Panel("(b) Means zoom", "Loading parameter Gamma", "Mean value", series_tuple(mean_zoom, ("H1a", "H2a", "DT1a", "DT2a")), xlim=GAMMA_ZOOM_FRAME, ylim=(0, 1.5), xticks=GAMMA_ZOOM_TICKS),
        Panel("(c) RMS variations", "Loading parameter Gamma", "RMS variation", series_tuple(rms_series, ("H1v", "H2v", "DT1v", "DT2v")), xlim=GAMMA_FULL_FRAME, ylim=(0, 5.0), xticks=GAMMA_FULL_TICKS),
        Panel("(d) RMS zoom", "Loading parameter Gamma", "RMS variation", series_tuple(rms_zoom, ("H1v", "H2v", "DT1v", "DT2v")), xlim=GAMMA_ZOOM_FRAME, ylim=(0, 0.5), xticks=GAMMA_ZOOM_TICKS),
    ]
    save_svg_grid(out_fig / "fig7_mean_rms.svg", panels, title="Fig. 7 reproduction: means and RMS variations, S1=0.5, S2=0.2")


def phase_diagram(out_data: Path, out_fig: Path) -> None:
    speeds = tuple(i / 20 for i in range(0, 31))  # 0.00 ... 1.50
    rows = []
    sim_points = []
    formula_points = []
    for speed in speeds:
        formula = equal_speed_transition_formula(speed)
        transition = estimate_equal_speed_transition(speed)
        rows.append((f"{speed:.10g}", f"{transition:.12g}", f"{formula:.12g}"))
        if transition == transition:
            sim_points.append((transition, speed))
        formula_points.append((formula, speed))
    write_csv(out_data / "fig8_phase_transition_equal_speedup.csv", ("S_equal", "gamma_transition_sim", "gamma_transition_formula"), rows)
    panel = Panel(
        "S1 = S2",
        "Loading parameter Gamma",
        "Speedup parameter S",
        (
            Series("simulation", tuple(sim_points), "#000000", "points", radius=2.8),
            Series("Gamma=S/(1+S)", tuple(formula_points), "#d62728", "line", stroke_width=2.0),
        ),
        xlim=(0, 0.8),
        ylim=(0, 1.5),
    )
    save_svg_grid(out_fig / "fig8_phase_diagram.svg", (panel,), columns=1, width=900, panel_height=610, title="Fig. 8 reproduction: regular / periodic-chaotic transition")


def write_summary(out_root: Path) -> None:
    summary = out_root / "summary.md"
    summary.write_text(
        """# Reproduction summary

Generated artifacts:

- `figures/fig2_headway_bifurcation.svg`
- `figures/fig3_headway_bifurcation_zoom.svg`
- `figures/fig4_tour_times.svg`
- `figures/fig5_tour_times_zoom.svg`
- `figures/fig6_return_maps.svg`
- `figures/fig7_mean_rms.svg`
- `figures/fig8_phase_diagram.svg`
- `data/*.csv`

Key checkpoints from the paper:

- Equal speedup `S1=S2=0.2` suppresses fluctuation until `Gamma ~= 0.167`.
- For `S1=0.5, S2=0.2`, the first transition is also near `Gamma ~= 0.167`.
- The reported later transitions are near `Gamma ~= 0.248` and `Gamma ~= 0.407`.
- For `Gamma > 2`, delays/headways diverge in this dimensionless model.

The SVG plots are dependency-free browser-viewable reproductions generated from
the CSV files.
""",
        encoding="utf-8",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="outputs", help="output directory relative to this project")
    parser.add_argument("--gamma-count", type=int, default=1001, help="number of Gamma samples in [0, 2]")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    project = Path(__file__).resolve().parent
    out_root = project / args.out
    out_data = out_root / "data"
    out_fig = out_root / "figures"
    out_data.mkdir(parents=True, exist_ok=True)
    out_fig.mkdir(parents=True, exist_ok=True)

    gammas = gamma_values(0.0, 2.0, args.gamma_count)
    print(f"Writing results to {out_root}")
    print("Generating Fig. 2 and Fig. 3 data...")
    headway_bifurcation(out_data, out_fig, gammas)
    print("Generating Fig. 4 and Fig. 5 data...")
    tour_time_bifurcation(out_data, out_fig, gammas)
    print("Generating Fig. 6 return maps...")
    return_maps(out_data, out_fig)
    print("Generating Fig. 7 means and RMS...")
    mean_and_rms(out_data, out_fig, gammas)
    print("Generating Fig. 8 phase diagram...")
    phase_diagram(out_data, out_fig)
    write_summary(out_root)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
