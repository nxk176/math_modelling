"""Lightweight validation checks for the shuttle-bus reproduction."""

from __future__ import annotations

from shuttle_bus import (
    estimate_equal_speed_transition,
    estimate_equal_speed_required_speed,
    inclusive_window,
    rms_variation,
    simulate,
)


def assert_close(value: float, expected: float, tolerance: float, label: str) -> None:
    if abs(value - expected) > tolerance:
        raise AssertionError(f"{label}: got {value:.8f}, expected {expected:.8f} +/- {tolerance}")


def main() -> int:
    # The paper reports the first transition near Gamma ~= 0.167 for the
    # equal-speed case S1=S2=0.2 in the headway bifurcation plots.
    estimated = estimate_equal_speed_transition(0.2, iterations=26)
    assert_close(estimated, 1.0 / 6.0, 2.0e-4, "simulated first transition S=0.2")

    # Fig. 8 is generated from a numerical scan because the paper does not give
    # a closed-form transition curve or the exact classification tolerance.
    required_speed = estimate_equal_speed_required_speed(0.2)
    if not (0.0 <= required_speed <= 2.5):
        raise AssertionError("Fig. 8 speed scan should find a finite transition candidate for Gamma=0.2")

    regular = simulate(0.1, (0.5, 0.2), trips=1001)
    regular_sample = inclusive_window(regular.headways[0], 900, 1000)
    if rms_variation(regular_sample) > 1.0e-7:
        raise AssertionError("Gamma=0.1 should be regular for S1=0.5, S2=0.2")

    periodic = simulate(0.2, (0.5, 0.2), trips=2002)
    periodic_sample = inclusive_window(periodic.headways[0], 1000, 2000)
    if rms_variation(periodic_sample) <= 1.0e-3:
        raise AssertionError("Gamma=0.2 should fluctuate after the first transition")

    divergent = simulate(2.1, (0.0, 0.0), trips=1001, divergence_limit=1.0e6)
    if not divergent.diverged:
        raise AssertionError("Gamma > 2 should diverge for the no-speedup case")

    print("All validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
