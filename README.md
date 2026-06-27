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
- `extension_multibus/run_multibus.py`: optional extension for testing more
  than two buses while keeping the same two-station shuttle structure.
- `outputs/`: generated data, figures, and summary files created by
  `python reproduce.py`; this directory is intentionally ignored by Git.

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
outputs/summary.md
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

The extension is placed in:

```text
extension_multibus/run_multibus.py
```

This extension keeps the same two-station shuttle setting:

```text
origin -> destination -> origin
```

It is an exploratory test, not a replacement for the main reproduction.

Run one four-bus case:

```powershell
python extension_multibus/run_multibus.py --bus-count 4 --gamma 0.2 --speeds 0.5,0.2,0.3,0.4
```

Run a four-bus Gamma sweep:

```powershell
python extension_multibus/run_multibus.py --bus-count 4 --speeds 0.5,0.2,0.3,0.4 --sweep --gamma-count 101
```

Run five buses with equal speedup:

```powershell
python extension_multibus/run_multibus.py --bus-count 5 --equal-speed 0.3 --gamma 0.2 --sweep
```

Extension outputs are written to:

```text
extension_multibus/outputs/
```

The extension summary CSV reports, for each bus:

- speedup parameter;
- initial arrival time;
- mean headway;
- RMS headway variation;
- mean tour time;
- RMS tour-time variation;
- qualitative motion label.

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
python extension_multibus/run_multibus.py --bus-count 4 --gamma 0.2 --speeds 0.5,0.2,0.3,0.4
```

If `validate.py` prints `All validation checks passed` and `reproduce.py`
finishes with `Done.`, the source code is running correctly.
