"""Nonlinear shuttle-bus map from Nagatani (Physica A 371, 2006).

The model is event driven.  At each arrival at the origin, the currently
arriving bus looks back to the bus that arrived immediately before it.  The
time difference is the headway H_i(m), and the next return to the origin is

    T_i(m+1) = T_i(m) + Gamma H_i(m) + 1 / (1 + S_i H_i(m)).

All variables are dimensionless as in the paper.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from statistics import fmean
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SimulationResult:
    """Trip-indexed simulation histories for each bus."""

    gamma: float
    speeds: tuple[float, ...]
    arrivals: tuple[tuple[float, ...], ...]
    headways: tuple[tuple[float, ...], ...]
    tour_times: tuple[tuple[float, ...], ...]
    events: tuple[tuple[float, int, int, float, float], ...]
    diverged: bool

    @property
    def bus_count(self) -> int:
        return len(self.speeds)

    @property
    def completed_trips(self) -> int:
        return min(len(x) for x in self.arrivals)


def default_initial_times(bus_count: int, initial_headway: float = 0.5) -> tuple[float, ...]:
    """Return staggered initial arrivals at the origin.

    The paper does not prescribe initial conditions.  A staggered pair
    (0, 0.5) for two buses avoids an artificial simultaneous first arrival and
    the long transient is discarded before measurements are taken.
    """

    if bus_count < 1:
        raise ValueError("bus_count must be positive")
    return tuple(i * initial_headway for i in range(bus_count))


def simulate(
    gamma: float,
    speeds: Sequence[float],
    *,
    trips: int = 2200,
    initial_times: Sequence[float] | None = None,
    initial_headway: float = 0.5,
    divergence_limit: float = 1.0e8,
) -> SimulationResult:
    """Iterate the shuttle-bus map until each bus completes ``trips`` trips.

    Parameters
    ----------
    gamma:
        Loading parameter Gamma.
    speeds:
        Speedup parameters S_i, one per bus.
    trips:
        Minimum number of arrivals to record for every bus.
    initial_times:
        Optional first arrival times.  If omitted, buses are staggered.
    initial_headway:
        Used only when ``initial_times`` is omitted.
    divergence_limit:
        Stops the run when a generated time exceeds this magnitude.
    """

    if gamma < 0:
        raise ValueError("gamma must be non-negative")
    if not speeds:
        raise ValueError("at least one bus is required")
    if any(s < 0 for s in speeds):
        raise ValueError("speedup parameters must be non-negative")
    if trips < 1:
        raise ValueError("trips must be positive")

    bus_count = len(speeds)
    starts = tuple(initial_times) if initial_times is not None else default_initial_times(bus_count, initial_headway)
    if len(starts) != bus_count:
        raise ValueError("initial_times length must match speeds length")
    if tuple(starts) != tuple(sorted(starts)):
        raise ValueError("initial_times must be sorted increasingly")

    arrivals: list[list[float]] = [[] for _ in speeds]
    headways: list[list[float]] = [[] for _ in speeds]
    tour_times: list[list[float]] = [[] for _ in speeds]
    events: list[tuple[float, int, int, float, float]] = []
    trip_index = [0 for _ in speeds]
    queue: list[tuple[float, int]] = []

    for bus, t0 in enumerate(starts):
        heapq.heappush(queue, (float(t0), bus))

    if bus_count == 1:
        last_time = starts[0] - 1.0
    else:
        first_gap = starts[1] - starts[0]
        last_time = starts[0] - first_gap

    diverged = False
    max_events = max(1000, trips * bus_count * 20)

    while min(trip_index) < trips and queue:
        current_time, bus = heapq.heappop(queue)
        if not math.isfinite(current_time) or abs(current_time) > divergence_limit:
            diverged = True
            break

        m = trip_index[bus]
        headway = current_time - last_time
        if headway < 0:
            # This should not happen with the event queue, but numerical noise
            # near identical arrivals can produce a tiny negative value.
            headway = 0.0

        denom = 1.0 + speeds[bus] * headway
        if denom <= 0:
            diverged = True
            break

        tour = gamma * headway + 1.0 / denom
        next_time = current_time + tour
        if not math.isfinite(next_time) or abs(next_time) > divergence_limit:
            diverged = True
            break

        arrivals[bus].append(current_time)
        headways[bus].append(headway)
        tour_times[bus].append(tour)
        events.append((current_time, bus, m, headway, tour))

        trip_index[bus] += 1
        heapq.heappush(queue, (next_time, bus))
        last_time = current_time

        if len(events) > max_events:
            diverged = True
            break

    return SimulationResult(
        gamma=float(gamma),
        speeds=tuple(float(s) for s in speeds),
        arrivals=tuple(tuple(x) for x in arrivals),
        headways=tuple(tuple(x) for x in headways),
        tour_times=tuple(tuple(x) for x in tour_times),
        events=tuple(events),
        diverged=diverged,
    )


def inclusive_window(values: Sequence[float], start: int, stop: int) -> tuple[float, ...]:
    """Return values for trip indices start, ..., stop."""

    if start < 0 or stop < start:
        raise ValueError("invalid window")
    return tuple(values[start : stop + 1])


def mean(values: Iterable[float]) -> float:
    data = tuple(values)
    return fmean(data) if data else math.nan


def rms_variation(values: Iterable[float]) -> float:
    """Root-mean-square fluctuation around the sample mean.

    The paper calls this quantity rms.  It is zero in regular motion, so it is
    the RMS deviation, not sqrt(mean(x^2)).
    """

    data = tuple(values)
    if not data:
        return math.nan
    avg = fmean(data)
    return math.sqrt(fmean((x - avg) ** 2 for x in data))


def unique_count(values: Iterable[float], digits: int = 7) -> int:
    return len({round(x, digits) for x in values})


def classify_motion(
    values: Sequence[float],
    *,
    regular_tol: float = 1.0e-7,
    periodic_unique_limit: int = 32,
    digits: int = 6,
) -> str:
    """Classify a sampled orbit as regular, periodic, or chaotic-like."""

    variation = rms_variation(values)
    if not math.isfinite(variation):
        return "diverged"
    if variation <= regular_tol:
        return "regular"
    if unique_count(values, digits=digits) <= periodic_unique_limit:
        return "periodic"
    return "chaotic"


def gamma_values(start: float, stop: float, count: int) -> tuple[float, ...]:
    if count < 2:
        raise ValueError("count must be at least 2")
    step = (stop - start) / (count - 1)
    return tuple(start + i * step for i in range(count))


def estimate_equal_speed_transition(
    speed: float,
    *,
    gamma_low: float = 0.0,
    gamma_high: float = 2.0,
    iterations: int = 32,
    trips: int = 1300,
    sample_start: int = 900,
    sample_stop: int = 1000,
    regular_tol: float = 2.0e-3,
) -> float:
    """Binary-search the first Gamma where equal-speed buses stop being regular."""

    def is_regular(gamma: float) -> bool:
        result = simulate(gamma, (speed, speed), trips=trips)
        sample = inclusive_window(result.headways[0], sample_start, sample_stop)
        return (not result.diverged) and rms_variation(sample) <= regular_tol

    lo = gamma_low
    hi = gamma_high
    if not is_regular(lo):
        return lo
    if is_regular(hi):
        return math.nan

    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if is_regular(mid):
            lo = mid
        else:
            hi = mid
    return hi


def equal_speed_transition_formula(speed: float) -> float:
    """Analytic transition curve reported by the simulation pattern.

    The paper's Fig. 8 transition points are reproduced by Gamma = S/(1+S),
    which also gives Gamma=0.167 at S=0.2.
    """

    return speed / (1.0 + speed)
