"""Interactive dashboard for the N-bus two-station shuttle extension."""

from __future__ import annotations

import math
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Sequence

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

TOUR_COLORS = (
    "#2ca02c",
    "#d62728",
    "#17becf",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#bcbd22",
    "#7f7f7f",
    "#1f77b4",
    "#ff7f0e",
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


def tour_color(bus: int) -> str:
    return TOUR_COLORS[bus % len(TOUR_COLORS)]


def bus_options(bus_count: int) -> list[dict[str, int | str]]:
    return [{"label": f"Bus {bus + 1}", "value": bus + 1} for bus in range(bus_count)]


def active_bus_indices(selected_buses: Sequence[int] | None, bus_count: int) -> list[int]:
    selected = []
    for value in selected_buses or []:
        try:
            bus = int(value) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= bus < bus_count and bus not in selected:
            selected.append(bus)
    return selected


def pack_result(result) -> dict[str, Any]:
    return {
        "gamma": result.gamma,
        "speeds": list(result.speeds),
        "arrivals": [list(values) for values in result.arrivals],
        "headways": [list(values) for values in result.headways],
        "tour_times": [list(values) for values in result.tour_times],
        "events": [list(event) for event in result.events],
        "diverged": result.diverged,
    }


def unpack_result(data: dict[str, Any]) -> SimpleNamespace:
    arrivals = tuple(tuple(values) for values in data["arrivals"])
    return SimpleNamespace(
        gamma=float(data["gamma"]),
        speeds=tuple(float(value) for value in data["speeds"]),
        arrivals=arrivals,
        headways=tuple(tuple(values) for values in data["headways"]),
        tour_times=tuple(tuple(values) for values in data["tour_times"]),
        events=tuple(tuple(event) for event in data["events"]),
        diverged=bool(data["diverged"]),
        bus_count=len(arrivals),
        completed_trips=min(len(values) for values in arrivals) if arrivals else 0,
    )


def build_sweep_data(
    *,
    speeds: tuple[float, ...],
    trips: int,
    sample_start: int,
    sample_stop: int,
    gamma_stop: float,
    gamma_count: int,
) -> dict[str, Any]:
    starts = default_initial_times(len(speeds))
    data: dict[str, Any] = {
        "gammas": [],
        "mean_h": [[] for _ in speeds],
        "rms_h": [[] for _ in speeds],
        "mean_tour": [[] for _ in speeds],
        "rms_tour": [[] for _ in speeds],
        "headway": [[] for _ in speeds],
        "tour": [[] for _ in speeds],
    }

    for gamma in gamma_values(0.0, gamma_stop, gamma_count):
        data["gammas"].append(gamma)
        result = simulate(gamma, speeds, trips=trips, initial_times=starts)
        for bus in range(result.bus_count):
            headway_sample = sample_window(result.headways[bus], sample_start, sample_stop)
            tour_sample = sample_window(result.tour_times[bus], sample_start, sample_stop)
            h_mean, h_rms, *_ = summarize_bus(headway_sample)
            tour_mean, tour_rms, *_ = summarize_bus(tour_sample)
            data["mean_h"][bus].append((gamma, h_mean))
            data["rms_h"][bus].append((gamma, h_rms))
            data["mean_tour"][bus].append((gamma, tour_mean))
            data["rms_tour"][bus].append((gamma, tour_rms))
            if gamma > 0.0:
                data["headway"][bus].extend((gamma, value) for value in headway_sample)
                data["tour"][bus].extend((gamma, value) for value in tour_sample)
    return data


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


def return_map_figure(
    result,
    selected_buses: Sequence[int] | None,
    sample_start: int,
    sample_stop: int,
) -> go.Figure:
    active_buses = active_bus_indices(selected_buses, result.bus_count)
    if not active_buses:
        return empty_figure("Return map")

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
    for bus in active_buses:
        values = sample_window(result.headways[bus], sample_start, sample_stop)
        fig.add_trace(
            go.Scattergl(
                x=values[:-1],
                y=values[1:],
                mode="markers",
                marker=dict(color=bus_color(bus), size=4, opacity=0.85),
                name=f"Bus {bus + 1}",
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="Return map",
        xaxis_title="H_i(m)",
        yaxis_title="H_i(m+1)",
        margin=dict(l=55, r=25, t=55, b=45),
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


def route_animation_figure(result) -> go.Figure:
    """Build a smooth route animation similar to the two-bus dashboard."""

    t_max_sim = 15.0
    fps = 32
    frame_times = [i / fps for i in range(int(t_max_sim * fps))]
    segments_by_bus: list[list[tuple[float, float, float, float]]] = [[] for _ in range(result.bus_count)]

    for bus, arrivals in enumerate(result.arrivals):
        if arrivals and arrivals[0] > 0:
            segments_by_bus[bus].append((0.0, arrivals[0], math.pi, math.pi))

    for time, bus, _trip, headway, tour in result.events:
        if time > t_max_sim + 2.0:
            break
        delay_total = max(0.0, result.gamma * headway)
        travel_total = max(0.0, tour - delay_total)
        delay_half = delay_total / 2.0
        travel_half = travel_total / 2.0

        t1 = time
        t2 = t1 + delay_half
        t3 = t2 + travel_half
        t4 = t3 + delay_half
        t5 = t4 + travel_half

        segments = segments_by_bus[bus]
        segments.append((t1, t2, math.pi, math.pi))
        segments.append((t2, t3, math.pi, 0.0))
        segments.append((t3, t4, 0.0, 0.0))
        segments.append((t4, t5, 0.0, -math.pi))

    def theta_at(t: float, segments: list[tuple[float, float, float, float]]) -> float:
        if not segments:
            return math.pi
        for start, stop, theta_start, theta_stop in segments:
            if start <= t <= stop:
                if stop <= start:
                    return theta_start
                ratio = (t - start) / (stop - start)
                return theta_start + (theta_stop - theta_start) * ratio
        if t < segments[0][0]:
            return segments[0][2]
        return segments[-1][3]

    def positions_at(t: float) -> tuple[list[float], list[float]]:
        x_values = []
        y_values = []
        for bus, segments in enumerate(segments_by_bus):
            theta = theta_at(t, segments)
            x_values.append(math.cos(theta))
            y_values.append(math.sin(theta))
        return x_values, y_values

    arrival_times = [event[0] for event in result.events if event[0] <= t_max_sim]

    def passenger_text(t: float) -> str:
        previous = [arrival for arrival in arrival_times if arrival <= t]
        last_arrival = previous[-1] if previous else 0.0
        return f"Origin: {int(max(0.0, t - last_arrival) * 20)} waiting"

    fig = go.Figure()
    theta = [-math.pi + 2.0 * math.pi * i / 180 for i in range(181)]
    x0, y0 = positions_at(0.0)
    fig.add_trace(
        go.Scatter(
            x=[math.cos(t) for t in theta],
            y=[math.sin(t) for t in theta],
            mode="lines",
            line=dict(color="#bdc3c7", width=3),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[-1.0, 1.0],
            y=[0.0, 0.0],
            mode="markers+text",
            marker=dict(color="#7f8c8d", size=16, symbol="square"),
            text=["Origin", "Destination"],
            textposition=["bottom center", "top center"],
            name="Stations",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x0,
            y=y0,
            mode="markers+text",
            marker=dict(
                color=[bus_color(bus) for bus in range(result.bus_count)],
                size=22,
                line=dict(color="white", width=2),
            ),
            text=[f"B{bus + 1}" for bus in range(result.bus_count)],
            textposition="top center",
            name="Buses",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[-1.35, 1.35],
            y=[0.25, 0.25],
            mode="text",
            text=[passenger_text(0.0), "Destination"],
            textfont=dict(size=14, color="#c0392b"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    frames = []
    for idx, t in enumerate(frame_times):
        x_bus, y_bus = positions_at(t)
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(x=x_bus, y=y_bus),
                    go.Scatter(text=[passenger_text(t), "Destination"]),
                ],
                traces=[2, 3],
                name=f"frame{idx}",
            )
        )
    fig.frames = frames
    fig.update_layout(
        template="plotly_white",
        xaxis=dict(visible=False, range=[-2.0, 2.0], showgrid=False, zeroline=False),
        yaxis=dict(visible=False, range=[-1.5, 1.5], showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1),
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", y=-0.06),
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.5,
                "y": -0.08,
                "xanchor": "center",
                "yanchor": "top",
                "direction": "left",
                "buttons": [
                    {
                        "label": "Play Simulation",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 50, "redraw": False},
                                "fromcurrent": True,
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
    )
    return fig


def sweep_figures(sweep_data: dict[str, Any], selected_buses: Sequence[int] | None) -> tuple[go.Figure, go.Figure]:
    bus_count = len(sweep_data["mean_h"])
    active_buses = active_bus_indices(selected_buses, bus_count)

    def make_fig(headway_key: str, tour_key: str, title: str, ylabel: str) -> go.Figure:
        if not active_buses:
            return empty_figure(title)

        fig = go.Figure()
        for bus in active_buses:
            headway_points = sweep_data[headway_key][bus]
            tour_points = sweep_data[tour_key][bus]
            fig.add_trace(
                go.Scatter(
                    x=[x for x, _ in headway_points],
                    y=[y for _, y in headway_points],
                    mode="lines",
                    name=f"H{bus + 1}",
                    line=dict(color=bus_color(bus), width=1.7),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[x for x, _ in tour_points],
                    y=[y for _, y in tour_points],
                    mode="lines",
                    name=f"DT{bus + 1}",
                    line=dict(color=tour_color(bus), width=1.9),
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
        make_fig("mean_h", "mean_tour", "Gamma sweep: mean values", "Mean value"),
        make_fig("rms_h", "rms_tour", "Gamma sweep: RMS variations", "RMS value"),
    )


def bifurcation_figures(
    sweep_data: dict[str, Any],
    selected_buses: Sequence[int] | None,
) -> tuple[go.Figure, go.Figure]:
    """Build paper-style bifurcation scatter plots from stored sweep data."""

    bus_count = len(sweep_data["headway"])
    active_buses = active_bus_indices(selected_buses, bus_count)

    def make_scatter(key: str, title: str, ylabel: str) -> go.Figure:
        if not active_buses:
            return empty_figure(title)

        fig = go.Figure()
        for bus in active_buses:
            points = sweep_data[key][bus]
            fig.add_trace(
                go.Scattergl(
                    x=[x for x, _ in points],
                    y=[y for _, y in points],
                    mode="markers",
                    marker=dict(color=bus_color(bus), size=2.5, symbol="square", opacity=0.55),
                    name=f"Bus {bus + 1}",
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
        make_scatter("headway", "Bifurcation scatter: headway samples", "H_i(m)"),
        make_scatter("tour", "Bifurcation scatter: tour-time samples", "Delta T_i(m)"),
    )


sidebar = html.Div(
    [
        html.H4("Multi-Bus Setup", className="mb-3"),
        html.Label("Number of buses N", className="fw-bold"),
        dbc.Input(id="bus-count", type="number", min=2, max=10, step=1, value=4),
        html.Label("Speedups S1,...,SN", className="fw-bold mt-3"),
        dbc.Input(id="speeds", type="text", value="0.5,0.2,0.3,0.4"),
        html.P("Comma-separated; one value per bus.", style={"fontSize": "12px", "color": "#7f8c8d", "margin": "2px 0 0"}),
        html.Label("Equal speed fallback", className="fw-bold mt-3"),
        dbc.Input(id="equal-speed", type="number", min=0, max=2, step=0.05, value=0.2),
        html.P("Used only if the speedup list is empty.", style={"fontSize": "12px", "color": "#7f8c8d", "margin": "2px 0 0"}),
        html.Label("Gamma", className="fw-bold mt-3"),
        dcc.Slider(id="gamma", min=0.0, max=2.0, step=0.05, value=0.5, marks={0: "0", 0.5: "0.5", 1: "1", 1.5: "1.5", 2: "2"}),
        html.P("Used for Return Map, KPI, and animation.", style={"fontSize": "12px", "color": "#7f8c8d", "margin": "2px 0 0"}),
        html.Label("Trips per bus", className="fw-bold mt-3"),
        dbc.Input(id="trips", type="number", min=200, max=4000, step=100, value=1500),
        dbc.Row(
            [
                dbc.Col([html.Label("Sample start", className="fw-bold mt-3"), dbc.Input(id="sample-start", type="number", min=0, value=1000)]),
                dbc.Col([html.Label("Sample stop", className="fw-bold mt-3"), dbc.Input(id="sample-stop", type="number", min=1, value=1499)]),
            ]
        ),
        html.P("Long-run trip window used after the transient.", style={"fontSize": "12px", "color": "#7f8c8d", "margin": "2px 0 0"}),
        html.Hr(),
        html.Label("Sweep gamma max", className="fw-bold"),
        dbc.Input(id="gamma-stop", type="number", min=0.1, max=2.0, step=0.1, value=2.0),
        html.Label("Sweep samples", className="fw-bold mt-3"),
        dbc.Input(id="gamma-count", type="number", min=5, max=501, step=1, value=301),
        html.P("Number of Gamma points in the sweep plots.", style={"fontSize": "12px", "color": "#7f8c8d", "margin": "2px 0 0"}),
        dbc.Button("Run Multi-Bus Simulation", id="run-button", color="primary", className="w-100 mt-4"),
    ],
    className="p-3 bg-light border-end",
    style={"minHeight": "100vh"},
)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="Multi-Bus Shuttle Dashboard")

app.layout = dbc.Container(
    [
        dcc.Store(id="analysis-store"),
        dbc.Row(
            [
                dbc.Col(sidebar, width=3, className="p-0"),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H2("N-Bus Two-Station Shuttle Dashboard", className="mb-1"),
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
                        html.Div(
                            [
                                html.Span("Show buses:", className="fw-bold me-2"),
                                dbc.Checklist(
                                    id="bus-selector",
                                    options=[],
                                    value=[],
                                    inline=True,
                                    className="btn-group flex-wrap",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-outline-primary btn-sm",
                                    labelCheckedClassName="active",
                                ),
                            ],
                            className="px-4 pt-3",
                        ),
                        dcc.Loading(
                            type="default",
                            children=dbc.Tabs(
                                [
                                    dbc.Tab(
                                        label="Headway & Tour Times",
                                        children=[
                                            dbc.Row(
                                                [
                                                    dbc.Col(dcc.Graph(id="fig-bif-headway"), width=6),
                                                    dbc.Col(dcc.Graph(id="fig-bif-tour"), width=6),
                                                ],
                                            ),
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Return Map",
                                        children=[
                                            dbc.Row(
                                                [
                                                    dbc.Col(dcc.Graph(id="fig-return", style={"height": "650px"}), width={"size": 8, "offset": 2}),
                                                ]
                                            )
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Mean & RMS",
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
                                        label="Route Animation",
                                        children=[
                                            dcc.Graph(id="fig-route", style={"height": "680px"}),
                                        ],
                                        className="p-4",
                                    ),
                                    dbc.Tab(
                                        label="Bus Summary",
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
                                        ],
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
        Output("analysis-store", "data"),
        Output("status-alert", "children"),
        Output("status-alert", "color"),
        Output("kpi-state", "children"),
        Output("kpi-buses", "children"),
        Output("kpi-gamma", "children"),
        Output("kpi-rms", "children"),
        Output("summary-table", "data"),
        Output("bus-selector", "options"),
        Output("bus-selector", "value"),
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
        State("gamma-stop", "value"),
        State("gamma-count", "value"),
    ],
)
def run_analysis(
    _n_clicks,
    bus_count,
    raw_speeds,
    equal_speed,
    gamma,
    trips,
    sample_start,
    sample_stop,
    gamma_stop,
    gamma_count,
):
    try:
        bus_count = int(bus_count)
        trips = int(trips)
        sample_start = int(sample_start)
        sample_stop = int(sample_stop)
        gamma_count = int(gamma_count)
        gamma = float(gamma)
        gamma_stop = float(gamma_stop)
        speeds = parse_speeds(raw_speeds, bus_count, equal_speed)
        if sample_start > sample_stop:
            raise ValueError("sample start must be <= sample stop")
        if sample_stop >= trips:
            trips = sample_stop + 1
        starts = default_initial_times(bus_count)

        result = simulate(gamma, speeds, trips=trips, initial_times=starts)
        rows = build_summary(result, speeds, sample_start, sample_stop)
        state, color = system_state(rows, result.diverged)
        max_rms = max(float(row["rms_h"]) for row in rows if row["rms_h"] != "nan")
        fig_route = route_animation_figure(result)

        sweep_data = build_sweep_data(
            speeds=speeds,
            trips=trips,
            sample_start=sample_start,
            sample_stop=sample_stop,
            gamma_stop=gamma_stop,
            gamma_count=gamma_count,
        )
        payload = {
            "result": pack_result(result),
            "sweep": sweep_data,
            "sample_start": sample_start,
            "sample_stop": sample_stop,
        }

        options = bus_options(bus_count)
        selected = [1] if options else []
        status = f"Ran N={bus_count}, Gamma={gamma:.3f}, sweep Gamma=[0, {gamma_stop:.3f}] with {gamma_count} samples."
        return (
            payload,
            status,
            color,
            state,
            str(bus_count),
            f"{gamma:.3f}",
            f"{max_rms:.4f}",
            rows,
            options,
            selected,
            fig_route,
        )
    except Exception as exc:  # Dash should show validation errors in the UI.
        message = f"Input error: {exc}"
        return (
            None,
            message,
            "danger",
            "Invalid",
            "-",
            "-",
            "-",
            [],
            [],
            [],
            empty_figure("Route animation"),
        )


@app.callback(
    [
        Output("fig-return", "figure"),
        Output("fig-sweep-mean", "figure"),
        Output("fig-sweep-rms", "figure"),
        Output("fig-bif-headway", "figure"),
        Output("fig-bif-tour", "figure"),
    ],
    [
        Input("analysis-store", "data"),
        Input("bus-selector", "value"),
    ],
)
def render_selected_bus_graphs(payload, selected_buses):
    if not payload:
        return (
            empty_figure("Return map"),
            empty_figure("Gamma sweep: mean values"),
            empty_figure("Gamma sweep: RMS variations"),
            empty_figure("Bifurcation scatter: headway samples"),
            empty_figure("Bifurcation scatter: tour-time samples"),
        )

    result = unpack_result(payload["result"])
    sample_start = int(payload["sample_start"])
    sample_stop = int(payload["sample_stop"])

    fig_return = return_map_figure(result, selected_buses, sample_start, sample_stop)
    fig_sweep_mean, fig_sweep_rms = sweep_figures(payload["sweep"], selected_buses)
    fig_bif_headway, fig_bif_tour = bifurcation_figures(payload["sweep"], selected_buses)
    return (
        fig_return,
        fig_sweep_mean,
        fig_sweep_rms,
        fig_bif_headway,
        fig_bif_tour,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
