"""Interactive dashboard for the N-bus two-station shuttle extension."""

from __future__ import annotations

import math
from pathlib import Path
import sys

import dash
from dash import Input, Output, State, dash_table, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


EXTENSION_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EXTENSION_ROOT.parent
for path in (PROJECT_ROOT, EXTENSION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_multibus import default_initial_times, parse_speeds, sample_window, summarize_bus  # noqa: E402
from shuttle_bus import gamma_values, simulate  # noqa: E402


COLORS = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        title=title,
        margin=dict(l=50, r=25, t=55, b=45),
        annotations=[
            dict(
                text="No data",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#7f8c8d"),
            )
        ],
    )
    return fig


def format_float(value: float) -> str:
    if not math.isfinite(value):
        return "nan"
    return f"{value:.4f}"


def bus_color(bus: int) -> str:
    return COLORS[bus % len(COLORS)]


def build_summary(result, speeds: tuple[float, ...], sample_start: int, sample_stop: int) -> list[dict[str, str]]:
    rows = []
    starts = default_initial_times(result.bus_count)
    for bus in range(result.bus_count):
        h = sample_window(result.headways[bus], sample_start, sample_stop)
        dt = sample_window(result.tour_times[bus], sample_start, sample_stop)
        h_mean, h_rms, h_min, h_max, motion = summarize_bus(h)
        dt_mean, dt_rms, dt_min, dt_max, _ = summarize_bus(dt)
        rows.append(
            {
                "bus": f"Bus {bus + 1}",
                "speedup": format_float(speeds[bus]),
                "initial": format_float(starts[bus]),
                "mean_h": format_float(h_mean),
                "rms_h": format_float(h_rms),
                "min_h": format_float(h_min),
                "max_h": format_float(h_max),
                "mean_dt": format_float(dt_mean),
                "rms_dt": format_float(dt_rms),
                "motion": motion,
            }
        )
    return rows


def system_state(rows: list[dict[str, str]], diverged: bool) -> tuple[str, str]:
    if diverged:
        return "Diverged", "danger"
    motions = {row["motion"] for row in rows}
    if "chaotic" in motions:
        return "Chaotic-like", "danger"
    if "periodic" in motions:
        return "Periodic", "warning"
    if motions == {"regular"}:
        return "Regular", "success"
    return "Mixed", "secondary"


def time_series_figure(result, sample_start: int, sample_stop: int, kind: str) -> go.Figure:
    title = "Headway samples" if kind == "headway" else "Tour-time samples"
    ylabel = "H_i(m)" if kind == "headway" else "Delta T_i(m)"
    values_by_bus = result.headways if kind == "headway" else result.tour_times
    fig = go.Figure()

    for bus, values in enumerate(values_by_bus):
        sample = sample_window(values, sample_start, sample_stop)
        x_values = list(range(sample_start, sample_start + len(sample)))
        fig.add_trace(
            go.Scattergl(
                x=x_values,
                y=sample,
                mode="lines",
                name=f"Bus {bus + 1}",
                line=dict(color=bus_color(bus), width=1.6),
            )
        )

    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Trip index m",
        yaxis_title=ylabel,
        margin=dict(l=55, r=25, t=55, b=45),
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


def return_map_figure(result, selected_bus: int, sample_start: int, sample_stop: int) -> go.Figure:
    bus = max(0, min(result.bus_count - 1, selected_bus - 1))
    values = sample_window(result.headways[bus], sample_start, sample_stop)
    x_values = values[:-1]
    y_values = values[1:]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0.0, 1.5],
            y=[0.0, 1.5],
            mode="lines",
            line=dict(color="#95a5a6", width=1, dash="dash"),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scattergl(
            x=x_values,
            y=y_values,
            mode="markers",
            marker=dict(color=bus_color(bus), size=4),
            name=f"Bus {bus + 1}",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=f"Return map for Bus {bus + 1}",
        xaxis_title="H_i(m)",
        yaxis_title="H_i(m+1)",
        margin=dict(l=55, r=25, t=55, b=45),
    )
    return fig


def event_order_figure(result, max_events: int = 500) -> go.Figure:
    events = result.events[-max_events:]
    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=[event[0] for event in events],
            y=[event[1] + 1 for event in events],
            mode="markers",
            marker=dict(
                color=[bus_color(event[1]) for event in events],
                size=5,
            ),
            text=[f"Bus {event[1] + 1}, trip {event[2]}" for event in events],
            name="Arrival events",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=f"Last {len(events)} origin-arrival events",
        xaxis_title="Arrival time at origin",
        yaxis_title="Bus id",
        yaxis=dict(dtick=1),
        margin=dict(l=55, r=25, t=55, b=45),
        showlegend=False,
    )
    return fig


def route_snapshot_figure(result, sample_stop: int) -> go.Figure:
    fig = go.Figure()
    theta = [2 * math.pi * i / 240 for i in range(241)]
    fig.add_trace(
        go.Scatter(
            x=[math.cos(t) for t in theta],
            y=[math.sin(t) for t in theta],
            mode="lines",
            line=dict(color="#bdc3c7", width=2),
            name="Route",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[1.0, -1.0],
            y=[0.0, 0.0],
            mode="markers+text",
            marker=dict(color=["#2c3e50", "#7f8c8d"], size=13, symbol="square"),
            text=["Origin", "Destination"],
            textposition=["bottom center", "top center"],
            name="Stations",
        )
    )

    x_bus = []
    y_bus = []
    labels = []
    colors = []
    for bus, arrivals in enumerate(result.arrivals):
        if not arrivals:
            continue
        idx = min(sample_stop, len(arrivals) - 1)
        phase = arrivals[idx] % 1.0
        angle = 2 * math.pi * phase
        x_bus.append(math.cos(angle))
        y_bus.append(math.sin(angle))
        labels.append(f"Bus {bus + 1}")
        colors.append(bus_color(bus))

    fig.add_trace(
        go.Scatter(
            x=x_bus,
            y=y_bus,
            mode="markers+text",
            marker=dict(color=colors, size=18, line=dict(color="white", width=2)),
            text=labels,
            textposition="top center",
            name="Buses",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Route snapshot from normalized arrival phases",
        xaxis=dict(visible=False, range=[-1.35, 1.35]),
        yaxis=dict(visible=False, range=[-1.35, 1.35], scaleanchor="x", scaleratio=1),
        margin=dict(l=25, r=25, t=55, b=25),
        legend=dict(orientation="h", y=-0.08),
    )
    return fig


def sweep_figures(
    *,
    speeds: tuple[float, ...],
    trips: int,
    sample_start: int,
    sample_stop: int,
    gamma_stop: float,
    gamma_count: int,
) -> tuple[go.Figure, go.Figure]:
    mean_points = [[] for _ in speeds]
    rms_points = [[] for _ in speeds]
    starts = default_initial_times(len(speeds))

    for gamma in gamma_values(0.0, gamma_stop, gamma_count):
        result = simulate(gamma, speeds, trips=trips, initial_times=starts)
        for bus in range(result.bus_count):
            sample = sample_window(result.headways[bus], sample_start, sample_stop)
            h_mean, h_rms, *_ = summarize_bus(sample)
            mean_points[bus].append((gamma, h_mean))
            rms_points[bus].append((gamma, h_rms))

    def make_fig(points_by_bus, title, ylabel):
        fig = go.Figure()
        for bus, points in enumerate(points_by_bus):
            fig.add_trace(
                go.Scatter(
                    x=[x for x, _ in points],
                    y=[y for _, y in points],
                    mode="lines",
                    name=f"Bus {bus + 1}",
                    line=dict(color=bus_color(bus), width=1.7),
                )
            )
        fig.update_layout(
            template="plotly_white",
            title=title,
            xaxis_title="Loading parameter Gamma",
            yaxis_title=ylabel,
            margin=dict(l=55, r=25, t=55, b=45),
            legend=dict(orientation="h", y=-0.22),
        )
        return fig

    return (
        make_fig(mean_points, "Gamma sweep: mean headway", "Mean H_i"),
        make_fig(rms_points, "Gamma sweep: RMS headway variation", "RMS H_i"),
    )


sidebar = html.Div(
    [
        html.H4("Multi-Bus Setup", className="mb-3"),
        html.Label("Number of buses N", className="fw-bold"),
        dbc.Input(id="bus-count", type="number", min=2, max=10, step=1, value=4),
        html.Label("Speedups S1,...,SN", className="fw-bold mt-3"),
        dbc.Input(id="speeds", type="text", value="0.5,0.2,0.3,0.4"),
        html.Div("Comma-separated. Length must match N.", className="text-muted small mt-1"),
        html.Label("Equal speed fallback", className="fw-bold mt-3"),
        dbc.Input(id="equal-speed", type="number", min=0, max=2, step=0.05, value=0.2),
        html.Label("Gamma", className="fw-bold mt-3"),
        dcc.Slider(id="gamma", min=0.0, max=2.0, step=0.05, value=0.2, marks={0: "0", 0.5: "0.5", 1: "1", 1.5: "1.5", 2: "2"}),
        html.Label("Trips per bus", className="fw-bold mt-3"),
        dbc.Input(id="trips", type="number", min=200, max=4000, step=100, value=1200),
        dbc.Row(
            [
                dbc.Col([html.Label("Sample start", className="fw-bold mt-3"), dbc.Input(id="sample-start", type="number", min=0, value=900)]),
                dbc.Col([html.Label("Sample stop", className="fw-bold mt-3"), dbc.Input(id="sample-stop", type="number", min=1, value=1100)]),
            ]
        ),
        html.Label("Return-map bus", className="fw-bold mt-3"),
        dbc.Input(id="return-bus", type="number", min=1, max=10, step=1, value=1),
        html.Hr(),
        html.Label("Sweep gamma max", className="fw-bold"),
        dbc.Input(id="gamma-stop", type="number", min=0.1, max=2.0, step=0.1, value=0.8),
        html.Label("Sweep samples", className="fw-bold mt-3"),
        dbc.Input(id="gamma-count", type="number", min=5, max=201, step=1, value=41),
        dbc.Button("Run Multi-Bus Simulation", id="run-button", color="primary", className="w-100 mt-4"),
        html.Div("The sweep can take a few seconds for large N.", className="text-muted small text-center mt-2"),
    ],
    className="p-3 bg-light border-end",
    style={"minHeight": "100vh"},
)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="Multi-Bus Shuttle Dashboard")

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(sidebar, width=3, className="p-0"),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H2("N-Bus Two-Station Shuttle Dashboard", className="mb-1"),
                                html.Div(
                                    "Generalized demo for N buses using the same event-driven shuttle map.",
                                    className="text-muted",
                                ),
                            ],
                            className="p-4 pb-2",
                        ),
                        dbc.Alert(id="status-alert", color="secondary", className="mx-4"),
                        dbc.Row(
                            [
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div("State", className="text-muted"), html.H4(id="kpi-state")]))),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Buses", className="text-muted"), html.H4(id="kpi-buses")]))),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Gamma", className="text-muted"), html.H4(id="kpi-gamma")]))),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Max RMS H", className="text-muted"), html.H4(id="kpi-rms")]))),
                            ],
                            className="px-4 g-3",
                        ),
                        dcc.Loading(
                            type="default",
                            children=dbc.Tabs(
                                [
                                    dbc.Tab(
                                        label="Summary",
                                        children=[
                                            dash_table.DataTable(
                                                id="summary-table",
                                                columns=[
                                                    {"name": "Bus", "id": "bus"},
                                                    {"name": "S", "id": "speedup"},
                                                    {"name": "T_i(0)", "id": "initial"},
                                                    {"name": "Mean H", "id": "mean_h"},
                                                    {"name": "RMS H", "id": "rms_h"},
                                                    {"name": "Min H", "id": "min_h"},
                                                    {"name": "Max H", "id": "max_h"},
                                                    {"name": "Mean DT", "id": "mean_dt"},
                                                    {"name": "RMS DT", "id": "rms_dt"},
                                                    {"name": "Motion", "id": "motion"},
                                                ],
                                                data=[],
                                                style_table={"overflowX": "auto"},
                                                style_cell={"fontFamily": "Arial", "fontSize": 13, "padding": "6px"},
                                                style_header={"fontWeight": "bold", "backgroundColor": "#ecf0f1"},
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(dcc.Graph(id="fig-headway"), width=6),
                                                    dbc.Col(dcc.Graph(id="fig-tour"), width=6),
                                                ],
                                                className="mt-3",
                                            ),
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Return Map & Events",
                                        children=[
                                            dbc.Row(
                                                [
                                                    dbc.Col(dcc.Graph(id="fig-return"), width=6),
                                                    dbc.Col(dcc.Graph(id="fig-events"), width=6),
                                                ]
                                            )
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Gamma Sweep",
                                        children=[
                                            dbc.Row(
                                                [
                                                    dbc.Col(dcc.Graph(id="fig-sweep-mean"), width=6),
                                                    dbc.Col(dcc.Graph(id="fig-sweep-rms"), width=6),
                                                ]
                                            )
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Route Snapshot",
                                        children=[dcc.Graph(id="fig-route", style={"height": "650px"})],
                                        className="p-4",
                                    ),
                                ],
                                className="m-4",
                            ),
                        ),
                    ],
                    width=9,
                    className="p-0",
                ),
            ],
            className="g-0",
        )
    ],
    fluid=True,
    className="p-0",
)


@app.callback(
    [
        Output("status-alert", "children"),
        Output("status-alert", "color"),
        Output("kpi-state", "children"),
        Output("kpi-buses", "children"),
        Output("kpi-gamma", "children"),
        Output("kpi-rms", "children"),
        Output("summary-table", "data"),
        Output("fig-headway", "figure"),
        Output("fig-tour", "figure"),
        Output("fig-return", "figure"),
        Output("fig-events", "figure"),
        Output("fig-sweep-mean", "figure"),
        Output("fig-sweep-rms", "figure"),
        Output("fig-route", "figure"),
    ],
    [Input("run-button", "n_clicks")],
    [
        State("bus-count", "value"),
        State("speeds", "value"),
        State("equal-speed", "value"),
        State("gamma", "value"),
        State("trips", "value"),
        State("sample-start", "value"),
        State("sample-stop", "value"),
        State("return-bus", "value"),
        State("gamma-stop", "value"),
        State("gamma-count", "value"),
    ],
)
def update_dashboard(
    _n_clicks,
    bus_count,
    raw_speeds,
    equal_speed,
    gamma,
    trips,
    sample_start,
    sample_stop,
    return_bus,
    gamma_stop,
    gamma_count,
):
    try:
        bus_count = int(bus_count)
        trips = int(trips)
        sample_start = int(sample_start)
        sample_stop = int(sample_stop)
        return_bus = int(return_bus)
        gamma_count = int(gamma_count)
        gamma = float(gamma)
        gamma_stop = float(gamma_stop)
        speeds = parse_speeds(raw_speeds, bus_count, equal_speed)
        if sample_stop >= trips:
            raise ValueError("sample stop must be smaller than trips")
        if sample_start > sample_stop:
            raise ValueError("sample start must be <= sample stop")
        starts = default_initial_times(bus_count)

        result = simulate(gamma, speeds, trips=trips, initial_times=starts)
        rows = build_summary(result, speeds, sample_start, sample_stop)
        state, color = system_state(rows, result.diverged)
        max_rms = max(float(row["rms_h"]) for row in rows if row["rms_h"] != "nan")

        fig_headway = time_series_figure(result, sample_start, sample_stop, "headway")
        fig_tour = time_series_figure(result, sample_start, sample_stop, "tour")
        fig_return = return_map_figure(result, return_bus, sample_start, sample_stop)
        fig_events = event_order_figure(result)
        fig_route = route_snapshot_figure(result, sample_stop)
        fig_sweep_mean, fig_sweep_rms = sweep_figures(
            speeds=speeds,
            trips=trips,
            sample_start=sample_start,
            sample_stop=sample_stop,
            gamma_stop=gamma_stop,
            gamma_count=gamma_count,
        )

        status = (
            f"Ran N={bus_count} buses with speeds {speeds}. "
            f"Initial times are evenly staggered over one base tour: {starts}."
        )
        return (
            status,
            color,
            state,
            str(bus_count),
            f"{gamma:.3f}",
            f"{max_rms:.4f}",
            rows,
            fig_headway,
            fig_tour,
            fig_return,
            fig_events,
            fig_sweep_mean,
            fig_sweep_rms,
            fig_route,
        )
    except Exception as exc:  # Dash should show validation errors in the UI.
        message = f"Input error: {exc}"
        return (
            message,
            "danger",
            "Invalid",
            "-",
            "-",
            "-",
            [],
            empty_figure("Headway samples"),
            empty_figure("Tour-time samples"),
            empty_figure("Return map"),
            empty_figure("Arrival events"),
            empty_figure("Gamma sweep: mean headway"),
            empty_figure("Gamma sweep: RMS headway"),
            empty_figure("Route snapshot"),
        )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
