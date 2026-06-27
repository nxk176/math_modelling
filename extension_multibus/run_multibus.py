"""Exploratory N-bus extension for the two-station shuttle model.

This script does not replace the paper reproduction in ``reproduce.py``.
It reuses the same nonlinear map from ``shuttle_bus.py`` and runs additional
experiments with an arbitrary number of buses on the same origin-destination
shuttle structure.

Examples
--------
Run one four-bus experiment:

    python extension_multibus/run_multibus.py --bus-count 4 --gamma 0.2 \
        --speeds 0.5,0.2,0.3,0.4

Run a Gamma sweep and generate figures:

    python extension_multibus/run_multibus.py --bus-count 4 --speeds 0.5,0.2,0.3,0.4 \
        --sweep --gamma-count 101
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shuttle_bus import (  # noqa: E402
    classify_motion,
    gamma_values,
    inclusive_window,
    mean,
    rms_variation,
    simulate,
)
from svg_plot import PALETTE, Panel, Series, save_svg_grid  # noqa: E402


GAMMA_ZOOM_STOP = 0.5
RETURN_MAP_GAMMAS = (0.2, 0.3, 0.5, 0.8)


def parse_speeds(raw: str | None, bus_count: int, equal_speed: float | None) -> tuple[float, ...]:
    """Parse speedup parameters for N buses."""

    if bus_count < 1:
        raise ValueError("bus_count must be positive")

    if raw:
        speeds = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
        if len(speeds) != bus_count:
            raise ValueError(
                f"--speeds must contain exactly {bus_count} values; got {len(speeds)}"
            )
        return speeds

    if equal_speed is not None:
        return tuple(float(equal_speed) for _ in range(bus_count))

    # A conservative default: equal speedup for every bus.
    return tuple(0.2 for _ in range(bus_count))


def default_initial_times(bus_count: int) -> tuple[float, ...]:
    """Evenly stagger buses over one dimensionless base tour."""

    if bus_count < 1:
        raise ValueError("bus_count must be positive")
    return tuple(i / bus_count for i in range(bus_count))


def format_param(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".").replace(".", "p")


def case_label(speeds: Sequence[float]) -> str:
    return "N{}_{}".format(
        len(speeds),
        "_".join(f"S{idx + 1}_{format_param(speed)}" for idx, speed in enumerate(speeds)),
    )


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def sample_window(values: Sequence[float], start: int, stop: int) -> tuple[float, ...]:
    """Return the requested sample window, clipped to available values."""

    if start < 0 or stop < start:
        raise ValueError("invalid sample window")
    if len(values) <= start:
        return ()
    return tuple(values[start : min(stop + 1, len(values))])


def summarize_bus(values: Sequence[float]) -> tuple[float, float, float, float, str]:
    """Return mean, RMS, min, max, and qualitative motion label."""

    if not values:
        return float("nan"), float("nan"), float("nan"), float("nan"), "missing"
    return (
        mean(values),
        rms_variation(values),
        min(values),
        max(values),
        classify_motion(values),
    )


def run_single_case(
    *,
    gamma: float,
    speeds: tuple[float, ...],
    trips: int,
    sample_start: int,
    sample_stop: int,
    out_dir: Path,
) -> None:
    """Run one N-bus experiment and write event-level and bus-level CSV files."""

    bus_count = len(speeds)
    initial_times = default_initial_times(bus_count)
    data_dir = out_dir / "data"
    result = simulate(
        gamma,
        speeds,
        trips=trips,
        initial_times=initial_times,
    )

    label = f"N{bus_count}_gamma_{format_param(gamma)}"
    summary_rows = []
    for bus in range(result.bus_count):
        h = sample_window(result.headways[bus], sample_start, sample_stop)
        dt = sample_window(result.tour_times[bus], sample_start, sample_stop)
        h_mean, h_rms, h_min, h_max, motion = summarize_bus(h)
        dt_mean, dt_rms, dt_min, dt_max, _ = summarize_bus(dt)
        summary_rows.append(
            (
                bus + 1,
                f"{speeds[bus]:.12g}",
                f"{initial_times[bus]:.12g}",
                len(h),
                f"{h_mean:.12g}",
                f"{h_rms:.12g}",
                f"{h_min:.12g}",
                f"{h_max:.12g}",
                f"{dt_mean:.12g}",
                f"{dt_rms:.12g}",
                f"{dt_min:.12g}",
                f"{dt_max:.12g}",
                motion,
                result.diverged,
            )
        )

    write_csv(
        data_dir / f"single_summary_{label}.csv",
        (
            "bus_id",
            "speedup_S",
            "initial_time",
            "sample_count",
            "mean_headway",
            "rms_headway",
            "min_headway",
            "max_headway",
            "mean_tour_time",
            "rms_tour_time",
            "min_tour_time",
            "max_tour_time",
            "motion",
            "diverged",
        ),
        summary_rows,
    )

    event_rows = (
        (
            idx,
            f"{time:.12g}",
            bus + 1,
            trip,
            f"{headway:.12g}",
            f"{tour:.12g}",
        )
        for idx, (time, bus, trip, headway, tour) in enumerate(result.events)
    )
    write_csv(
        data_dir / f"single_events_{label}.csv",
        ("event_index", "arrival_time", "bus_id", "trip_m", "headway", "tour_time"),
        event_rows,
    )

    print(f"Single run written to {data_dir}")
    print(f"  - data/single_summary_{label}.csv")
    print(f"  - data/single_events_{label}.csv")


def run_gamma_sweep(
    *,
    gamma_start: float,
    gamma_stop: float,
    gamma_count: int,
    speeds: tuple[float, ...],
    trips: int,
    sample_start: int,
    sample_stop: int,
    out_dir: Path,
) -> None:
    """Sweep Gamma and write N-bus CSV data plus SVG diagnostics."""

    bus_count = len(speeds)
    initial_times = default_initial_times(bus_count)
    data_dir = out_dir / "data"
    figure_dir = out_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    label = case_label(speeds)
    rows = []
    mean_headway_points = [[] for _ in range(bus_count)]
    rms_headway_points = [[] for _ in range(bus_count)]
    mean_tour_points = [[] for _ in range(bus_count)]
    rms_tour_points = [[] for _ in range(bus_count)]
    headway_points = [[] for _ in range(bus_count)]
    headway_zoom_points = [[] for _ in range(bus_count)]
    tour_points = [[] for _ in range(bus_count)]
    tour_zoom_points = [[] for _ in range(bus_count)]

    for gamma in gamma_values(gamma_start, gamma_stop, gamma_count):
        result = simulate(
            gamma,
            speeds,
            trips=trips,
            initial_times=initial_times,
        )
        for bus in range(result.bus_count):
            h = sample_window(result.headways[bus], sample_start, sample_stop)
            dt = sample_window(result.tour_times[bus], sample_start, sample_stop)
            h_mean, h_rms, h_min, h_max, motion = summarize_bus(h)
            dt_mean, dt_rms, dt_min, dt_max, _ = summarize_bus(dt)
            for value in h:
                headway_points[bus].append((gamma, value))
                if gamma <= GAMMA_ZOOM_STOP:
                    headway_zoom_points[bus].append((gamma, value))
            for value in dt:
                tour_points[bus].append((gamma, value))
                if gamma <= GAMMA_ZOOM_STOP:
                    tour_zoom_points[bus].append((gamma, value))
            rows.append(
                (
                    f"{gamma:.12g}",
                    bus_count,
                    bus + 1,
                    f"{speeds[bus]:.12g}",
                    f"{initial_times[bus]:.12g}",
                    len(h),
                    f"{h_mean:.12g}",
                    f"{h_rms:.12g}",
                    f"{h_min:.12g}",
                    f"{h_max:.12g}",
                    f"{dt_mean:.12g}",
                    f"{dt_rms:.12g}",
                    f"{dt_min:.12g}",
                    f"{dt_max:.12g}",
                    motion,
                    result.diverged,
                )
            )
            mean_headway_points[bus].append((gamma, h_mean))
            rms_headway_points[bus].append((gamma, h_rms))
            mean_tour_points[bus].append((gamma, dt_mean))
            rms_tour_points[bus].append((gamma, dt_rms))

    write_csv(
        data_dir / f"sweep_summary_{label}_gamma_{format_param(gamma_start)}_{format_param(gamma_stop)}.csv",
        (
            "gamma",
            "bus_count",
            "bus_id",
            "speedup_S",
            "initial_time",
            "sample_count",
            "mean_headway",
            "rms_headway",
            "min_headway",
            "max_headway",
            "mean_tour_time",
            "rms_tour_time",
            "min_tour_time",
            "max_tour_time",
            "motion",
            "diverged",
        ),
        rows,
    )

    def series_from(points_by_bus: list[list[tuple[float, float]]]) -> tuple[Series, ...]:
        return tuple(
            Series(
                f"Bus {bus + 1}",
                tuple(points),
                PALETTE[bus % len(PALETTE)],
                "line",
                stroke_width=1.7,
            )
            for bus, points in enumerate(points_by_bus)
        )

    def point_series(points: list[tuple[float, float]], bus: int, radius: float = 0.75) -> tuple[Series, ...]:
        return (
            Series(
                f"Bus {bus + 1}",
                tuple(points),
                "#000000",
                "points",
                radius=radius,
                marker="square",
                stride=2,
            ),
        )

    full_xlim = (gamma_start, gamma_stop)
    zoom_xlim = (gamma_start, min(GAMMA_ZOOM_STOP, gamma_stop))
    headway_full_panels = []
    headway_zoom_panels = []
    tour_full_panels = []
    tour_zoom_panels = []
    for bus in range(bus_count):
        headway_full_panels.append(
            Panel(
                f"Bus {bus + 1}, S={speeds[bus]:g}",
                "Loading parameter Gamma",
                f"H{bus + 1}(m)",
                point_series(headway_points[bus], bus),
                xlim=full_xlim,
            )
        )
        headway_zoom_panels.append(
            Panel(
                f"Bus {bus + 1}, S={speeds[bus]:g}",
                "Loading parameter Gamma",
                f"H{bus + 1}(m)",
                point_series(headway_zoom_points[bus], bus, radius=0.9),
                xlim=zoom_xlim,
            )
        )
        tour_full_panels.append(
            Panel(
                f"Bus {bus + 1}, S={speeds[bus]:g}",
                "Loading parameter Gamma",
                f"Delta T{bus + 1}(m)",
                point_series(tour_points[bus], bus),
                xlim=full_xlim,
            )
        )
        tour_zoom_panels.append(
            Panel(
                f"Bus {bus + 1}, S={speeds[bus]:g}",
                "Loading parameter Gamma",
                f"Delta T{bus + 1}(m)",
                point_series(tour_zoom_points[bus], bus, radius=0.9),
                xlim=zoom_xlim,
            )
        )

    save_svg_grid(
        figure_dir / f"multibus_fig2_headway_bifurcation_{label}.svg",
        headway_full_panels,
        title=f"Multi-bus Fig. 2 analogue: headway bifurcation, N={bus_count}",
    )
    save_svg_grid(
        figure_dir / f"multibus_fig3_headway_zoom_{label}.svg",
        headway_zoom_panels,
        title=f"Multi-bus Fig. 3 analogue: headway zoom, N={bus_count}",
    )
    save_svg_grid(
        figure_dir / f"multibus_fig4_tour_times_{label}.svg",
        tour_full_panels,
        title=f"Multi-bus Fig. 4 analogue: tour times, N={bus_count}",
    )
    save_svg_grid(
        figure_dir / f"multibus_fig5_tour_times_zoom_{label}.svg",
        tour_zoom_panels,
        title=f"Multi-bus Fig. 5 analogue: tour-time zoom, N={bus_count}",
    )

    return_map_panels = []
    return_rows = []
    for gamma in RETURN_MAP_GAMMAS:
        if gamma < gamma_start or gamma > gamma_stop:
            continue
        result = simulate(gamma, speeds, trips=max(trips, sample_stop + 2), initial_times=initial_times)
        for bus in range(bus_count):
            h = sample_window(result.headways[bus], sample_start, sample_stop + 1)
            points = tuple((h[idx], h[idx + 1]) for idx in range(max(0, len(h) - 1)))
            for idx, (x_val, y_val) in enumerate(points):
                return_rows.append((f"{gamma:.12g}", bus + 1, sample_start + idx, f"{x_val:.12g}", f"{y_val:.12g}"))
            return_map_panels.append(
                Panel(
                    f"Gamma={gamma:g}, Bus {bus + 1}",
                    f"H{bus + 1}(m)",
                    f"H{bus + 1}(m+1)",
                    (
                        Series("", ((0.0, 0.0), (1.5, 1.5)), "#777777", "line", stroke_width=1.1),
                        Series("", points, PALETTE[bus % len(PALETTE)], "points", radius=1.1, marker="square", stride=2),
                    ),
                    xlim=(0.0, 1.5),
                    ylim=(0.0, 1.5),
                    aspect=1.0,
                    xticks=(0.0, 0.5, 1.0, 1.5),
                    yticks=(0.0, 0.5, 1.0, 1.5),
                )
            )
    if return_map_panels:
        write_csv(
            data_dir / f"return_maps_{label}.csv",
            ("gamma", "bus_id", "trip_m", "H_i_m", "H_i_m_plus_1"),
            return_rows,
        )
        save_svg_grid(
            figure_dir / f"multibus_fig6_return_maps_{label}.svg",
            return_map_panels,
            title=f"Multi-bus Fig. 6 analogue: return maps, N={bus_count}",
        )

    panels = (
        Panel(
            "(a) Mean headway",
            "Loading parameter Gamma",
            "Mean H_i",
            series_from(mean_headway_points),
            xlim=(gamma_start, gamma_stop),
        ),
        Panel(
            "(b) Mean tour time",
            "Loading parameter Gamma",
            "Mean Delta T_i",
            series_from(mean_tour_points),
            xlim=(gamma_start, gamma_stop),
        ),
        Panel(
            "(c) RMS headway",
            "Loading parameter Gamma",
            "RMS H_i",
            series_from(rms_headway_points),
            xlim=(gamma_start, gamma_stop),
        ),
        Panel(
            "(d) RMS tour time",
            "Loading parameter Gamma",
            "RMS Delta T_i",
            series_from(rms_tour_points),
            xlim=(gamma_start, gamma_stop),
        ),
    )
    save_svg_grid(
        figure_dir / f"multibus_fig7_mean_rms_{label}.svg",
        panels,
        title=f"Multi-bus Fig. 7 analogue: mean and RMS, N={bus_count}",
    )

    print(f"Gamma sweep written to {out_dir}")
    print(f"  - data/sweep_summary_{label}_gamma_{format_param(gamma_start)}_{format_param(gamma_stop)}.csv")
    print("  - figures/multibus_fig2_headway_bifurcation_*.svg")
    print("  - figures/multibus_fig3_headway_zoom_*.svg")
    print("  - figures/multibus_fig4_tour_times_*.svg")
    print("  - figures/multibus_fig5_tour_times_zoom_*.svg")
    print("  - figures/multibus_fig6_return_maps_*.svg")
    print("  - figures/multibus_fig7_mean_rms_*.svg")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an exploratory N-bus extension of the two-station shuttle model."
    )
    parser.add_argument("--bus-count", type=int, default=4, help="number of buses N")
    parser.add_argument(
        "--speeds",
        type=str,
        default=None,
        help="comma-separated speedups, e.g. 0.5,0.2,0.3,0.4",
    )
    parser.add_argument(
        "--equal-speed",
        type=float,
        default=None,
        help="use the same speedup value for every bus when --speeds is omitted",
    )
    parser.add_argument("--gamma", type=float, default=0.2, help="Gamma for a single run")
    parser.add_argument("--trips", type=int, default=1500, help="trips per bus")
    parser.add_argument("--sample-start", type=int, default=1000, help="first sampled trip index")
    parser.add_argument(
        "--sample-stop",
        type=int,
        default=None,
        help="last sampled trip index; default is trips-1",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
        help="directory for generated extension outputs",
    )
    parser.add_argument("--sweep", action="store_true", help="also run a Gamma sweep")
    parser.add_argument("--gamma-start", type=float, default=0.0, help="Gamma sweep start")
    parser.add_argument("--gamma-stop", type=float, default=2.0, help="Gamma sweep stop")
    parser.add_argument("--gamma-count", type=int, default=101, help="number of Gamma sweep samples")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sample_stop = args.sample_stop if args.sample_stop is not None else args.trips - 1
    if sample_stop >= args.trips:
        raise ValueError("--sample-stop must be smaller than --trips")
    if args.sample_start > sample_stop:
        raise ValueError("--sample-start must be <= --sample-stop")

    speeds = parse_speeds(args.speeds, args.bus_count, args.equal_speed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("Two-station N-bus extension")
    print("  route: origin -> destination -> origin")
    print(f"  bus_count: {args.bus_count}")
    print(f"  speeds: {speeds}")
    print(f"  initial_times: {default_initial_times(args.bus_count)}")
    print(f"  sample window: trips {args.sample_start}..{sample_stop}")

    run_single_case(
        gamma=args.gamma,
        speeds=speeds,
        trips=args.trips,
        sample_start=args.sample_start,
        sample_stop=sample_stop,
        out_dir=args.out_dir,
    )

    if args.sweep:
        run_gamma_sweep(
            gamma_start=args.gamma_start,
            gamma_stop=args.gamma_stop,
            gamma_count=args.gamma_count,
            speeds=speeds,
            trips=args.trips,
            sample_start=args.sample_start,
            sample_stop=sample_stop,
            out_dir=args.out_dir,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
