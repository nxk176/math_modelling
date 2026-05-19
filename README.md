# Shuttle Bus Chaos Reproduction

This repository reproduces the numerical model and the main figures from:

Takashi Nagatani, "Chaos control and schedule of shuttle buses",
*Physica A: Statistical Mechanics and its Applications*, 371(2), 683-691,
2006. DOI: `10.1016/j.physa.2006.04.056`.

The goal is not to digitize the paper figures. The original paper does not
provide CSV data or supplementary numerical output. Instead, this project
reimplements the published dimensionless map and regenerates the numerical
data and SVG figures from that model.

## What This Project Does

The paper studies shuttle buses that repeatedly travel between an origin and a
destination. Passenger loading creates delay, and a speed-control rule reduces
the travel time when the headway becomes large. The nonlinear feedback between
loading delay and speedup can produce regular, periodic, and chaotic schedules.

This project implements:

- the shuttle-bus nonlinear map from the paper,
- an event-driven simulator for freely passing buses,
- regenerated data for Fig. 2 through Fig. 8,
- SVG plots generated without third-party plotting libraries,
- validation checks for the main transition points reported in the paper.

All code uses only the Python standard library. No `numpy`, `pandas`,
`matplotlib`, or `scipy` dependency is required.

## Model

For bus $i$ at trip $m$, let $T_i(m)$ be the arrival time at the origin. The
headway $H_i(m)$ is the time gap between this arrival and the previous bus
arrival at the origin:

$$
H_i(m) = T_i(m) - T_{i'}(m')
$$

Here $i'$ and $m'$ refer to the bus and trip index of the immediately preceding
arrival event.

The dimensionless map implemented here is:

$$
T_i(m+1) = T_i(m) + \Gamma H_i(m)
           + \frac{1}{1 + S_i H_i(m)}
$$

where:

- $\Gamma$ is the loading parameter.
- $S_i$ is the speedup parameter of bus $i$.
- $\Gamma H_i(m)$ is the loading/unloading delay term.
- $\frac{1}{1 + S_i H_i(m)}$ is the moving-time term under speedup control.
- $\Delta T_i(m) = T_i(m+1) - T_i(m)$ is the tour time.

The simulator is event-driven. At each step, the next bus arrival at the origin
is popped from a priority queue, its headway is computed against the previous
arrival event, and its next arrival time is scheduled. This matches the paper's
assumption that buses may pass each other freely.

## Repository Layout

```text
.
|-- README.md
|-- requirements.txt
|-- reproduce.py
|-- shuttle_bus.py
|-- svg_plot.py
|-- validate.py
`-- outputs/
    |-- data/
    |-- figures/
    `-- summary.md
```

File roles:

- `shuttle_bus.py`: simulator, statistics, and transition helpers.
- `reproduce.py`: regenerates CSV data and SVG figures.
- `svg_plot.py`: lightweight SVG plotting utilities.
- `validate.py`: smoke tests for the numerical implementation.
- `outputs/data/`: regenerated CSV data.
- `outputs/figures/`: regenerated SVG figures.
- `outputs/summary.md`: short generated output summary.

## How To Run

From the repository root:

```powershell
python validate.py
python reproduce.py
```

The first command checks the implementation. The second command regenerates all
CSV and SVG outputs.

The default reproduction uses `1001` $\Gamma$ samples in $[0, 2]$, then filters
the data according to the open intervals used in the paper, for example:

- full bifurcation sweeps: $0 < \Gamma < 2$,
- zoomed figures: $0 < \Gamma < 0.5$.

The plot frames are separate from the simulation constraints. For example, a
figure may show an axis frame slightly beyond the last tick, while the data
still obeys the strict open interval specified in the paper.

To use a different $\Gamma$ resolution:

```powershell
python reproduce.py --gamma-count 1501
```

## Generated Figures

Running `python reproduce.py` creates:

- `outputs/figures/fig2_headway_bifurcation.svg`
  - Reproduction of Fig. 2.
  - Plots $H_1(m)$ versus $\Gamma$ for trips $m=900,\ldots,1000$.
  - Cases:
    - $S_1=S_2=0$
    - $S_1=S_2=0.2$
    - $S_1=0.3,\ S_2=0.2$
    - $S_1=0.5,\ S_2=0.2$

- `outputs/figures/fig3_headway_bifurcation_zoom.svg`
  - Reproduction of Fig. 3.
  - Zoom of Fig. 2 for $0 < \Gamma < 0.5$.

- `outputs/figures/fig4_tour_times.svg`
  - Reproduction of Fig. 4.
  - Plots tour times $\Delta T_1(m)$ and $\Delta T_2(m)$ for
    $S_1=0.5,\ S_2=0.2$.

- `outputs/figures/fig5_tour_times_zoom.svg`
  - Reproduction of Fig. 5.
  - Zoom of Fig. 4 for $0 < \Gamma < 0.5$.

- `outputs/figures/fig6_return_maps.svg`
  - Reproduction of Fig. 6.
  - Return maps $H_1(m+1)$ versus $H_1(m)$.
  - Uses $\Gamma = 0.2,\ 0.3,\ 0.5,\ 0.8$.

- `outputs/figures/fig7_mean_rms.svg`
  - Reproduction of Fig. 7.
  - Mean values and RMS variations for headways and tour times.

- `outputs/figures/fig8_phase_diagram.svg`
  - Reproduction of Fig. 8.
  - Transition curve for equal speedup parameters $S_1=S_2$.

## Generated Data

The CSV files in `outputs/data/` are regenerated simulation data. They are not
original data extracted from the paper.

The relationship between CSV files and figures is:

- `fig2_fig3_headway_case_*.csv`
  - Source data for Fig. 2 and Fig. 3.
  - Fig. 3 is a zoomed view of the same headway sweep.

- `fig4_fig5_tour_times_s1_0p5_s2_0p2.csv`
  - Source data for Fig. 4 and Fig. 5.
  - Fig. 5 is a zoomed view of the same tour-time sweep.

- `fig6_return_map_gamma_*.csv`
  - Source data for Fig. 6 return maps.

- `fig7_mean_rms_s1_0p5_s2_0p2.csv`
  - Source data for Fig. 7 mean and RMS plots.

- `fig8_phase_transition_equal_speedup.csv`
  - Source data for Fig. 8 phase diagram.

Each time `python reproduce.py` is run, these CSV and SVG files are overwritten
with newly regenerated deterministic outputs.

## Determinism

The simulation is deterministic. It does not use random numbers or random
seeds. If the code and parameters are unchanged, rerunning `reproduce.py`
regenerates the same data up to normal floating-point formatting.

The default two-bus initial condition is:

$$
T_1(0) = 0,\qquad T_2(0) = 0.5
$$

The paper does not fully specify initial conditions. Long transients are
discarded by sampling later trip ranges such as $m=900,\ldots,1000$ and
$m=1000,\ldots,2000$, following the figure captions.

## Validation

Run:

```powershell
python validate.py
```

The validation script checks several key properties:

- the equal-speedup transition formula gives
  $\Gamma = \frac{1}{6} \approx 0.167$ for $S=0.2$,
- $\Gamma=0.1$ remains regular for $S_1=0.5,\ S_2=0.2$,
- $\Gamma=0.2$ shows fluctuation after the first transition,
- $\Gamma > 2$ diverges in the no-speedup case.

If the checks pass, the script prints:

```text
All validation checks passed.
```

## Limitations

This is a model reproduction, not a digitization of the original plots.

Important limitations:

- The original paper does not provide raw data.
- Initial conditions are not fully specified in the paper.
- Chaotic trajectories are sensitive to initial conditions and numerical
  details.
- The SVG renderer is custom and will not look pixel-identical to the original
  paper's plotting tool.

Therefore, the expected agreement is qualitative and numerical at the level of
the published model behavior: regular regimes, bifurcation structure, return
map patterns, transition points, and divergence behavior.

## References Used For Reproduction

- User-provided PDF of the paper.
- ScienceDirect metadata page:
  <https://www.sciencedirect.com/science/article/abs/pii/S0378437106004754>
- Public OCR/preview used only to cross-check equations and captions:
  <https://www.scribd.com/document/882586440/Chaos-Control-and-Schedule-of-Shuttle-Buses>
- Independent class-poster reproduction using the same dimensionless map:
  <https://math.arizona.edu/~gabitov/teaching/101/math_485_585/Posters/ChaosBusShuttle_485.pdf>
