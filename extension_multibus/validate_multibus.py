"""Validation checks for the optional N-bus extension."""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory


EXTENSION_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EXTENSION_ROOT.parent
for path in (PROJECT_ROOT, EXTENSION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_multibus import (  # noqa: E402
    default_initial_times,
    parse_speeds,
    run_gamma_sweep,
    run_single_case,
    sample_window,
)
from shuttle_bus import simulate  # noqa: E402


def assert_close(actual: float, expected: float, tol: float, label: str) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def main() -> None:
    speeds = parse_speeds("0.5,0.2,0.3,0.4", 4, None)
    if speeds != (0.5, 0.2, 0.3, 0.4):
        raise AssertionError("speed parser failed")

    starts = default_initial_times(4)
    expected_starts = (0.0, 0.25, 0.5, 0.75)
    for actual, expected in zip(starts, expected_starts):
        assert_close(actual, expected, 1.0e-12, "initial time")

    result = simulate(0.2, speeds, trips=120, initial_times=starts)
    if result.bus_count != 4:
        raise AssertionError("simulate did not preserve bus count")
    if result.diverged:
        raise AssertionError("basic four-bus case unexpectedly diverged")
    if min(len(series) for series in result.headways) < 120:
        raise AssertionError("not every bus completed the requested trips")

    sample = sample_window(result.headways[0], 20, 40)
    if len(sample) != 21:
        raise AssertionError("sample window should be inclusive")

    with TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        run_single_case(
            gamma=0.2,
            speeds=speeds,
            trips=120,
            sample_start=20,
            sample_stop=40,
            out_dir=out_dir,
        )
        if not any((out_dir / "data").glob("single_summary_N4_gamma_0p2.csv")):
            raise AssertionError("single-run summary was not generated")
        if not any((out_dir / "data").glob("single_events_N4_gamma_0p2.csv")):
            raise AssertionError("single-run event file was not generated")

        run_gamma_sweep(
            gamma_start=0.0,
            gamma_stop=0.3,
            gamma_count=5,
            speeds=speeds,
            trips=120,
            sample_start=20,
            sample_stop=40,
            out_dir=out_dir,
        )
        if not any((out_dir / "data").glob("sweep_summary_N4_*_gamma_0_0p3.csv")):
            raise AssertionError("sweep summary was not generated")
        expected_patterns = (
            "multibus_fig2_headway_bifurcation_N4_*.svg",
            "multibus_fig3_headway_zoom_N4_*.svg",
            "multibus_fig4_tour_times_N4_*.svg",
            "multibus_fig5_tour_times_zoom_N4_*.svg",
            "multibus_fig6_return_maps_N4_*.svg",
            "multibus_fig7_mean_rms_N4_*.svg",
        )
        for pattern in expected_patterns:
            if not any((out_dir / "figures").glob(pattern)):
                raise AssertionError(f"expected SVG was not generated: {pattern}")

    print("All multi-bus extension checks passed.")


if __name__ == "__main__":
    main()
