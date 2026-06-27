# Math Modelling Project - Shuttle Bus Chaos

This README is a quick run guide for the submitted source code. The report and
slides explain the mathematical model and the scientific background in detail.
This file focuses only on how to run the code and what each command produces.

## Requirements

- Python 3.10 or newer.
- No third-party package is required for the static reproduction scripts:
  `validate.py` and `reproduce.py`.
- The interactive dashboard is optional and requires the packages listed in
  `requirements.txt`.

Check Python:

```powershell
python --version
```

If `python` is not recognized on Windows, use:

```powershell
py -3 --version
```

## Project Files

```text
Math_Modelling/
|-- README.md
|-- requirements.txt
|-- shuttle_bus.py
|-- reproduce.py
|-- svg_plot.py
|-- validate.py
|-- dashboard_v2.py
`-- extension_multibus/
```

Main files:

- `shuttle_bus.py`: core event-driven simulator for the shuttle-bus nonlinear
  map.
- `reproduce.py`: regenerates the static CSV data and SVG figures used by the
  project.
- `svg_plot.py`: lightweight SVG plotting helper used by `reproduce.py`.
- `validate.py`: quick numerical checks to confirm that the implementation is
  behaving as expected.
- `dashboard_v2.py`: optional interactive dashboard for exploring parameters.
- `extension_multibus/run_multibus.py`: optional CLI extension for testing more
  than two buses while keeping the same two-station shuttle structure.
- `extension_multibus/dashboard_multibus.py`: optional interactive dashboard
  for the generalized N-bus extension.
- `extension_multibus/validate_multibus.py`: quick checks for the N-bus
  extension.
- `outputs/`: generated data and figures created by `python reproduce.py`;
  this directory is intentionally ignored by Git.

## Quick Run

From the `Math_Modelling` folder:

```powershell
python validate.py
python reproduce.py
```

Expected validation output:

```text
All validation checks passed.
```

Expected reproduction output:

```text
Writing results to ...\Math_Modelling\outputs
Generating Fig. 2 and Fig. 3 data...
Generating Fig. 4 and Fig. 5 data...
Generating Fig. 6 return maps...
Generating Fig. 7 means and RMS...
Generating Fig. 8 phase diagram...
Done.
```

After running `python reproduce.py`, the generated files are saved in:

```text
outputs/data/
outputs/figures/
```

The generated CSV files are simulation outputs produced by the implemented
model. They are not raw data extracted from the original paper.

## What The Main Commands Do

### `python validate.py`

Runs quick checks on the numerical implementation. It verifies that:

- the equal-speed transition formula gives the expected value for `S=0.2`;
- the simulated transition is close to the expected transition value;
- a low-loading case stays regular;
- a higher-loading case shows fluctuation;
- a no-speedup case diverges when `Gamma > 2`.

This command is useful before presenting or grading because it catches obvious
implementation mistakes quickly.

### `python reproduce.py`

Runs the full static experiment pipeline. It regenerates:

- headway bifurcation data and figures;
- tour-time data and figures;
- return-map data and figures;
- mean/RMS data and figures;
- equal-speed phase-transition data and figure.

The script overwrites the generated files in `outputs/`. The simulation is
deterministic, so rerunning the same source code with the same parameters
produces the same numerical results up to normal floating-point formatting.

Optional Gamma resolution:

```powershell
python reproduce.py --gamma-count 1501
```

The default is:

```text
gamma-count = 1001
```

## Optional Dashboard

The dashboard is not required to regenerate the static project results. It is
only an interactive demo for changing parameters and inspecting the behaviour
of the two-bus model.

Install dashboard dependencies:

```powershell
pip install -r requirements.txt
```

Run dashboard:

```powershell
python dashboard_v2.py
```

Then open the local URL printed by Dash, usually:

```text
http://127.0.0.1:8050/
```

Use the dashboard to adjust:

- `S1`: speedup parameter of bus 1;
- `S2`: speedup parameter of bus 2;
- `Gamma`: passenger loading parameter.

The dashboard shows headway, tour time, return map, mean/RMS curves, phase
diagram, and a simple animation view.

## Optional Multi-Bus Extension

The main reproduction follows the two-bus experiments. The simulator itself can
also run more than two buses because the number of buses is determined by the
length of the speedup tuple.

The extension files are placed in:

```text
extension_multibus/run_multibus.py
extension_multibus/dashboard_multibus.py
extension_multibus/validate_multibus.py
```

This extension keeps the same two-station shuttle setting:

```text
origin -> destination -> origin
```

It is an exploratory test, not a replacement for the main reproduction.

For the N-bus extension, the speedup list only sets the control parameters
`S1,...,SN`. The initial arrival times are generated automatically by spreading
the buses evenly over one normalized base tour:

```text
T1(0) = 0
T2(0) = 1/N
T3(0) = 2/N
...
TN(0) = (N-1)/N
```

For example, with four buses the initial arrivals are:

```text
(T1(0), T2(0), T3(0), T4(0)) = (0, 0.25, 0.5, 0.75)
```

This is used to avoid artificial simultaneous first arrivals and to make the
initial schedule evenly distributed for any number of buses.

Validate the extension:

```powershell
python extension_multibus/validate_multibus.py
```

Run one four-bus case:

```powershell
python extension_multibus/run_multibus.py --bus-count 4 --gamma 0.2 --speeds 0.5,0.2,0.3,0.4
```

Run a four-bus Gamma sweep:

```powershell
python extension_multibus/run_multibus.py --bus-count 4 --speeds 0.5,0.2,0.3,0.4 --sweep --gamma-count 101
```

If `--gamma-start`, `--gamma-stop`, and `--gamma-count` are not overridden,
the extension sweep uses:

```text
gamma_start = 0.0
gamma_stop  = 2.0
gamma_count = 101
```

This means the sweep runs 101 evenly spaced loading-parameter values from
`Gamma = 0.00` to `Gamma = 2.00`, with step size `0.02`.

The `--sweep` command generates graph outputs analogous to the main two-bus
figures, but for all buses in the selected N-bus configuration:

```text
extension_multibus/outputs/data/
extension_multibus/outputs/figures/
```

The generated SVG figures include:

- `multibus_fig2_headway_bifurcation_*.svg`: headway bifurcation panels for
  each bus;
- `multibus_fig3_headway_zoom_*.svg`: zoomed headway bifurcation panels;
- `multibus_fig4_tour_times_*.svg`: tour-time bifurcation panels for each bus;
- `multibus_fig5_tour_times_zoom_*.svg`: zoomed tour-time panels;
- `multibus_fig6_return_maps_*.svg`: return maps for selected Gamma values and
  each bus;
- `multibus_fig7_mean_rms_*.svg`: mean and RMS curves for all buses.

There is no direct copy of the paper's Fig. 8 for the multi-bus case because
the original phase boundary is defined for the two-bus equal-speed setting. For
the N-bus extension, the mean/RMS and return-map figures are used as the main
diagnostics.

Run five buses with equal speedup:

```powershell
python extension_multibus/run_multibus.py --bus-count 5 --equal-speed 0.3 --gamma 0.2 --sweep
```

Single-run extension CSV outputs are written to:

```text
extension_multibus/outputs/data/
```

The extension summary CSV reports, for each bus:

- speedup parameter;
- initial arrival time;
- mean headway;
- RMS headway variation;
- mean tour time;
- RMS tour-time variation;
- qualitative motion label.

Run the interactive N-bus dashboard:

```powershell
python extension_multibus/dashboard_multibus.py
```

Then open:

```text
http://127.0.0.1:8051/
```

The multi-bus dashboard lets the user set the main simulation parameters:

- `Number of buses N`: the number of buses running on the same two-station
  loop;
- `Speedups S1,...,SN`: comma-separated control strengths, one value per bus;
- `Equal speed fallback`: used only when the speedup list is left empty; in
  that case every bus receives the same speedup value;
- `Gamma`: the passenger-loading parameter used by the return-map,
  route-animation, and bus-summary views;
- `Trips per bus`: the number of trips simulated for each bus;
- `Sample start` and `Sample stop`: the long-run trip window used for
  statistics and plotting after the transient part has been skipped;
- `Sweep gamma max`: the maximum Gamma value used in the sweep and
  bifurcation-scatter tabs;
- `Sweep samples`: the number of Gamma values sampled in the sweep. Larger
  values give denser scatter plots but take longer to run.

After one run, the bus selector buttons can be used to show or hide Bus 1,
Bus 2, and so on. The dashboard does not re-run the simulation when these
buttons are clicked; it only redraws the graphs from the stored analysis data.
Bus 1 is selected by default after a run. If no bus button is selected, the
graphs remain empty. The selector affects return maps, Gamma sweep mean/RMS
plots, and bifurcation scatter plots. In the Gamma sweep mean/RMS plots, both
headway `H_i` and tour time `Delta T_i` are drawn as solid lines with separate
colors.

The `Headway & Tour Times` tab sweeps evenly spaced Gamma values on the x-axis
and plots sampled long-run values on the y-axis, matching the paper-style
scatter view used by the two-bus figures. The `Mean & RMS` tab shows mean and
RMS curves for both headway and tour time. The `Route Animation` tab adds a
Play/Pause demo of the buses moving around the two-station loop.

## Fresh Clone Checklist

Use this sequence to verify the submitted code from a fresh copy:

```powershell
cd Math_Modelling
python --version
python validate.py
python reproduce.py
```

Optional dashboard check:

```powershell
pip install -r requirements.txt
python dashboard_v2.py
```

Optional multi-bus extension check:

```powershell
python extension_multibus/validate_multibus.py
python extension_multibus/run_multibus.py --bus-count 4 --gamma 0.2 --speeds 0.5,0.2,0.3,0.4
```

Optional multi-bus dashboard check:

```powershell
pip install -r requirements.txt
python extension_multibus/dashboard_multibus.py
```

If `validate.py` prints `All validation checks passed` and `reproduce.py`
finishes with `Done.`, the source code is running correctly.
