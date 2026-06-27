import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import csv
import heapq

import shuttle_bus

# ----- Pre-processing Phase Diagram Data -----
PHASE_S = tuple(i / 20 for i in range(0, 31))  
PHASE_G_FORMULA = tuple(shuttle_bus.equal_speed_transition_formula(s) for s in PHASE_S)
try:
    with open('outputs/data/fig8_phase_transition_equal_speedup.csv', 'r') as f:
        reader = csv.DictReader(f)
        PHASE_G_SIM = [float(row['gamma_transition_sim']) if row['gamma_transition_sim'] != 'nan' else None for row in reader]
except Exception:
    PHASE_G_SIM = tuple(shuttle_bus.estimate_equal_speed_transition(s) for s in PHASE_S)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="Shuttle Bus Chaos Dashboard")


def empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        template='plotly_white',
        title=title,
        margin=dict(l=40, r=40, t=50, b=40),
        annotations=[
            dict(
                text="No bus selected",
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


def active_buses(selected_buses):
    buses = []
    for value in selected_buses or []:
        try:
            bus = int(value)
        except (TypeError, ValueError):
            continue
        if bus in (1, 2) and bus not in buses:
            buses.append(bus)
    return buses

# ==========================================
# 1. SIDEBAR
# ==========================================
sidebar = html.Div(
    [
        html.H4("Configuration", className="display-6", style={'fontSize': '24px', 'fontWeight': 'bold'}),
        html.Hr(),
        html.P("Adjust bus and passenger parameters:", className="text-muted", style={'fontSize': '14px'}),
        
        html.Label(html.B("Bus 1 Speed (S1)"), className="mt-3"),
        dcc.Slider(id='s1-slider', min=0.0, max=1.0, step=0.1, value=0.5, marks={i/10: str(i/10) for i in range(11)}),
        
        html.Label(html.B("Bus 2 Speed (S2)"), className="mt-4"),
        dcc.Slider(id='s2-slider', min=0.0, max=1.0, step=0.1, value=0.2, marks={i/10: str(i/10) for i in range(11)}),
        
        html.Label(html.B("Loading Parameter (Gamma)"), className="mt-4"),
        html.P("Used for Return Map & KPI calculation", style={'fontSize': '12px', 'color': '#7f8c8d', 'margin': '0'}),
        dcc.Slider(id='gamma-slider', min=0.0, max=2.0, step=0.1, value=0.5, marks={i/10: str(i/10) for i in range(0, 21, 2)}),
        
        html.Hr(className="mt-4"),
        dbc.Button("Update & Analyze", id="run-button", color="primary", className="w-100 mt-2", n_clicks=0),
        html.P("Simulation sweep takes ~2-4s.", className="text-center text-muted mt-2", style={'fontSize': '12px'})
    ],
    style={"padding": "20px", "backgroundColor": "#f8f9fa", "minHeight": "100vh", "borderRight": "1px solid #dee2e6"}
)

# ==========================================
# 2. MAIN CONTENT
# ==========================================
content = html.Div(
    [
        html.H2("Bus Bunching Simulation Dashboard", className="mb-4", style={'color': '#2c3e50', 'fontWeight': 'bold'}),
        
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("System State (at Gamma)", className="card-title text-muted"), 
                html.H3("Loading...", id="kpi-status", className="font-weight-bold")
            ]), className="shadow-sm")),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Mean Headway Bus 1 (H1)", className="card-title text-muted"), 
                html.H3("...", id="kpi-h1", className="text-primary font-weight-bold")
            ]), className="shadow-sm")),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Mean Headway Bus 2 (H2)", className="card-title text-muted"), 
                html.H3("...", id="kpi-h2", className="text-warning font-weight-bold")
            ]), className="shadow-sm")),
        ], className="mb-4"),

        html.Div([
            html.Span("Show buses:", className="fw-bold me-2"),
            dbc.Checklist(
                id="bus-selector",
                options=[{"label": "Bus 1", "value": 1}, {"label": "Bus 2", "value": 2}],
                value=[1],
                inline=True,
                className="btn-group flex-wrap",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary btn-sm",
                labelCheckedClassName="active",
            ),
        ], className="mb-3"),

        dcc.Loading(type="default", children=[
            dbc.Tabs([
                dbc.Tab(label="1. Headway & Tour Times", tab_id="tab-1", children=[
                    dbc.Row([
                        dbc.Col([html.Label(html.B("X-Axis (Gamma):")), dcc.RangeSlider(id='p1-x-range', min=0.0, max=2.5, step=0.1, value=[0.0, 2.05])], width=6),
                        dbc.Col([html.Label(html.B("Y-Axis (Value):")), dcc.RangeSlider(id='p1-y-range', min=0.0, max=20.0, step=1.0, value=[0.0, 6.0])], width=6)
                    ], className="mb-3 bg-light p-3 rounded border"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig1-headway', style={'height': '550px'}), width=6), dbc.Col(dcc.Graph(id='fig2-tourtime', style={'height': '550px'}), width=6)])
                ], className="p-3 border border-top-0 bg-white"),

                dbc.Tab(label="2. Return Map", tab_id="tab-2", children=[
                    html.P("The Return Map displays the full trajectory of the system, including 'Chaotic Attractors' during bunching events.", className="mt-3 text-center text-muted"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig3-returnmap', style={'height': '650px'}), width={'size': 8, 'offset': 2})])
                ], className="p-3 border border-top-0 bg-white"),

                dbc.Tab(label="3. Mean & RMS", tab_id="tab-3", children=[
                    dbc.Row([
                        dbc.Col([html.Label(html.B("X-Axis (Gamma):")), dcc.RangeSlider(id='p3-x-range', min=0.0, max=2.5, step=0.1, value=[0.0, 2.05])], width=6),
                        dbc.Col([html.Label(html.B("Y-Axis (Value):")), dcc.RangeSlider(id='p3-y-range', min=0.0, max=6.0, step=0.5, value=[0.0, 5.0])], width=6)
                    ], className="mb-3 bg-light p-3 rounded border"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig4-mean', style={'height': '550px'}), width=6), dbc.Col(dcc.Graph(id='fig4-rms', style={'height': '550px'}), width=6)])
                ], className="p-3 border border-top-0 bg-white"),

                dbc.Tab(label="4. Phase Diagram", tab_id="tab-4", children=[
                    html.P("Phase boundary diagram. Note the Gold Star: If it falls BELOW/RIGHT of the red curve, the system enters the Chaotic state.", className="mt-3 text-center text-danger font-weight-bold"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig5-phase', style={'height': '650px'}), width={'size': 10, 'offset': 1})])
                ], className="p-3 border border-top-0 bg-white"),

                dbc.Tab(label="5. Live Animation", tab_id="tab-5", children=[
                    html.P("Buses shuttling between Origin (Left) and Destination (Right). Wait times depend entirely on the exact mathematical map (Eq.5), causing realistic bus bunching/chaos.", className="mt-3 text-center text-muted"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig6-animation', style={'height': '700px'}), width={'size': 10, 'offset': 1})])
                ], className="p-3 border border-top-0 bg-white")
                
            ], id="tabs", active_tab="tab-2")
        ])
    ],
    style={"padding": "30px", "backgroundColor": "#f4f6f8", "minHeight": "100vh"}
)

app.layout = dbc.Container([dbc.Row([dbc.Col(sidebar, width=3, className="p-0"), dbc.Col(content, width=9, className="p-0")], className="m-0")], fluid=True, className="p-0")



# ==========================================
# 3. ANIMATION FUNCTION (UPDATED)
# ==========================================
def build_animation_figure(diverged, gamma, s1, s2):
    """
    Simulates the exact discrete nonlinear map from the research paper (Eq. 5)
    and interpolates positions to create a continuous Plotly animation.
    """
    # 1. Discrete Event Simulation strictly based on the paper's math
    queue = []
    # Initial staggered arrivals: Bus 1 at t=0.0, Bus 2 at t=0.5
    heapq.heappush(queue, (0.0, 'arrive_origin', 1))
    heapq.heappush(queue, (0.5, 'arrive_origin', 2))
    
    segments_1 = []
    segments_2 = [(0.0, 0.5, np.pi, np.pi)] # Bus 2 waits at origin until t=0.5
    
    last_arrival_time = -0.5 # Set so that H_1 = 0 - (-0.5) = 0.5 initially
    t_max_sim = 15.0 # Total dimensionless time to simulate
    
    while queue:
        t, event, bus_id = heapq.heappop(queue)
        if t > t_max_sim + 2.0:
            break
            
        if event == 'arrive_origin':
            H = t - last_arrival_time # Headway: Time since previous bus arrived
            if H < 0.0001: H = 0.0001 # Prevent division by zero when bunched
            last_arrival_time = t
            
            S = s1 if bus_id == 1 else s2
            
            # Equations from the paper: Delay depends on Gamma, Speedup on S
            delay_total = gamma * H
            travel_total = 1.0 / (1.0 + S * H)
            
            # Split delay and travel symmetrically between Go and Return phases
            delay_half = delay_total / 2.0
            travel_half = travel_total / 2.0
            
            # Calculate absolute timeline points for this specific round trip
            t1 = t
            t2 = t1 + delay_half             # Finish boarding at Origin
            t3 = t2 + travel_half            # Arrive at Destination
            t4 = t3 + delay_half             # Finish alighting at Destination
            t5 = t4 + travel_half            # Return to Origin
            
            # Record trajectory segments: (start_t, end_t, start_theta, end_theta)
            # Origin is at PI, Destination is at 0
            segs = segments_1 if bus_id == 1 else segments_2
            segs.append((t1, t2, np.pi, np.pi))     # Boarding delay (Stationary)
            segs.append((t2, t3, np.pi, 0.0))       # Top curve (Go phase)
            segs.append((t3, t4, 0.0, 0.0))         # Alighting delay (Stationary)
            segs.append((t4, t5, 0.0, -np.pi))      # Bottom curve (Return phase)
            
            heapq.heappush(queue, (t5, 'arrive_origin', bus_id))

    # 2. Frame Generation (Interpolating continuous positions)
    fps = 32
    dt = 1.0 / fps
    times = np.arange(0, t_max_sim, dt)
    
    def get_theta(t, segments):
        for (st, et, s_th, e_th) in segments:
            if st <= t <= et:
                if et == st: return s_th
                return s_th + (e_th - s_th) * (t - st) / (et - st)
        if not segments: return np.pi
        if t < segments[0][0]: return segments[0][2]
        if t > segments[-1][1]: return segments[-1][3]
        return np.pi

    arrival_times = sorted([seg[0] for seg in segments_1 if seg[2] == np.pi and seg[3] == np.pi] + 
                           [seg[0] for seg in segments_2 if seg[2] == np.pi and seg[3] == np.pi])
                           
    def get_pax(t):
        valid = [a for a in arrival_times if a <= t]
        last_arr = valid[-1] if valid else -0.5
        # Assuming 20 pax arrive per dimensionless time unit for visual scaling
        return int((t - last_arr) * 20) 

    # Track definition
    theta_track = np.linspace(-np.pi, np.pi, 100)
    
    fig = go.Figure(
        data=[
            # The Route Oval
            go.Scatter(x=np.cos(theta_track), y=np.sin(theta_track), mode='lines', line=dict(color='#bdc3c7', width=3), showlegend=False, hoverinfo='skip'),
            # Origin and Destination Stops
            go.Scatter(x=[-1, 1], y=[0, 0], mode='markers', marker=dict(color='#7f8c8d', size=16, symbol='square'), name='Terminals (Origin & Dest)'),
            # Bus 1
            go.Scatter(x=[-1], y=[0], mode='markers', marker=dict(color='#1f77b4', size=22, line=dict(width=2, color='white')), name='Bus 1 (Blue)'),
            # Bus 2 (slightly offset radius to see overlapping/passing)
            go.Scatter(x=[-1], y=[0], mode='markers', marker=dict(color='#ff7f0e', size=22, line=dict(width=2, color='white')), name='Bus 2 (Orange)'),
            # Text for Passengers
            go.Scatter(x=[-1.35, 1.35], y=[0.25, 0.25], mode='text', text=["Origin: 0 pax", "Dest: 0 pax"], textfont=dict(size=14, color='red', weight='bold'), showlegend=False)
        ]
    )

    frames = []
    # R1 and R2 allow visual passing (Buses won't completely cover each other)
    R1, R2 = 1.0, 1.08 
    
    for i, t in enumerate(times):
        th1 = get_theta(t, segments_1)
        th2 = get_theta(t, segments_2)
        pax = get_pax(t)
        
        x1, y1 = R1 * np.cos(th1), R1 * np.sin(th1)
        x2, y2 = R2 * np.cos(th2), R2 * np.sin(th2)
        
        # Ensure 'diverged' status is clear
        if diverged and t > t_max_sim * 0.5:
            p_text = f"Origin: {pax} pax (CHAOS!)"
        else:
            p_text = f"Origin: {pax} pax waiting"
            
        frames.append(go.Frame(
            data=[
                go.Scatter(x=[x1], y=[y1]), 
                go.Scatter(x=[x2], y=[y2]), 
                go.Scatter(text=[p_text, "Destination: Drop-off"])
            ], 
            traces=[2, 3, 4], 
            name=f'frame{i}'
        ))

    fig.frames = frames
    fig.update_layout(
        template='plotly_white', 
        xaxis=dict(range=[-2.0, 2.0], showgrid=False, zeroline=False, visible=False), 
        yaxis=dict(range=[-1.5, 1.5], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1), 
        margin=dict(l=20, r=20, t=20, b=20),
        updatemenus=[dict(type="buttons", showactive=False, x=0.5, y=-0.1, xanchor="center", yanchor="top", direction="left",
            buttons=[
                dict(label="Play Simulation", method="animate", args=[None, dict(frame=dict(duration=50, redraw=False), fromcurrent=True, transition=dict(duration=0))]),
                dict(label="Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
            ])]
    )
    return fig


# ==========================================
# 4. MAIN CALLBACK
# ==========================================
@app.callback(
    [Output('kpi-status', 'children'), Output('kpi-status', 'className'), Output('kpi-h1', 'children'), Output('kpi-h2', 'children'), Output('fig1-headway', 'figure'), Output('fig2-tourtime', 'figure'), Output('fig3-returnmap', 'figure'), Output('fig4-mean', 'figure'), Output('fig4-rms', 'figure'), Output('fig5-phase', 'figure'), Output('fig6-animation', 'figure')],
    [Input('run-button', 'n_clicks'), Input('bus-selector', 'value')],
    [State('s1-slider', 'value'), State('s2-slider', 'value'), State('gamma-slider', 'value'), State('p1-x-range', 'value'), State('p1-y-range', 'value'), State('p3-x-range', 'value'), State('p3-y-range', 'value')]
)
def update_dashboard(n_clicks, selected_buses, s1, s2, target_gamma, p1_x, p1_y, p3_x, p3_y):
    gamma_values = shuttle_bus.gamma_values(0.0, 2.0, 1000)
    selected = active_buses(selected_buses)
    
    bif_g, bif_h1, bif_g2, bif_h2, tour_g, tour_t1, tour_t2 = [], [], [], [], [], [], []
    mean_h1, rms_h1, mean_h2, rms_h2, mean_t1, rms_t1, mean_t2, rms_t2 = [], [], [], [], [], [], [], []
    
    for g in gamma_values:
        if g <= 0.0 or g >= 2.0: continue
        res = shuttle_bus.simulate(g, (s1, s2), trips=1050)
        
        if res.diverged:
            mean_h1.append(None); rms_h1.append(None); mean_h2.append(None); rms_h2.append(None); mean_t1.append(None); rms_t1.append(None); mean_t2.append(None); rms_t2.append(None)
            continue
            
        h1_window = shuttle_bus.inclusive_window(res.headways[0], 900, 1000)
        h2_window = shuttle_bus.inclusive_window(res.headways[1], 900, 1000)
        t1_window = shuttle_bus.inclusive_window(res.tour_times[0], 900, 1000)
        t2_window = shuttle_bus.inclusive_window(res.tour_times[1], 900, 1000)
        
        stride = 2
        bif_g.extend([g] * len(h1_window[::stride]))
        bif_h1.extend(h1_window[::stride])
        bif_g2.extend([g] * len(h2_window[::stride]))
        bif_h2.extend(h2_window[::stride])
        tour_g.extend([g] * len(t1_window[::stride]))
        tour_t1.extend(t1_window[::stride])
        tour_t2.extend(t2_window[::stride])
        
        mean_h1.append(shuttle_bus.mean(h1_window)); rms_h1.append(shuttle_bus.rms_variation(h1_window))
        mean_h2.append(shuttle_bus.mean(h2_window)); rms_h2.append(shuttle_bus.rms_variation(h2_window))
        mean_t1.append(shuttle_bus.mean(t1_window)); rms_t1.append(shuttle_bus.rms_variation(t1_window))
        mean_t2.append(shuttle_bus.mean(t2_window)); rms_t2.append(shuttle_bus.rms_variation(t2_window))

    if target_gamma <= 0.0:
        diverged_status = False
        kpi_h1_text, kpi_h2_text = "0.50 m", "0.50 m"
        x_ret, y_ret, x_ret2, y_ret2 = [], [], [], []
    else:
        res_ret = shuttle_bus.simulate(target_gamma, (s1, s2), trips=2050)
        
        avg_s = (s1 + s2) / 2.0
        theoretical_gamma_limit = avg_s / (1.0 + avg_s)
        diverged_status = res_ret.diverged or (target_gamma > theoretical_gamma_limit)
        
        try:
            h1_full = shuttle_bus.inclusive_window(res_ret.headways[0], 1000, 2000)
            h2_full = shuttle_bus.inclusive_window(res_ret.headways[1], 1000, 2000)
            x_ret = h1_full[:-1][::2]
            y_ret = h1_full[1:][::2]
            x_ret2 = h2_full[:-1][::2]
            y_ret2 = h2_full[1:][::2]
        except Exception:
            x_ret, y_ret, x_ret2, y_ret2 = [], [], [], []
            
        if diverged_status:
            kpi_h1_text, kpi_h2_text = "N/A (Chaos)", "N/A (Chaos)"
        else:
            kpi_h1_text = f"{shuttle_bus.mean(h1_full):.2f} m"
            kpi_h2_text = f"{shuttle_bus.mean(h2_full):.2f} m"
            
    if diverged_status:
        kpi_status = "Warning (Bus Bunching)"
        kpi_class = "text-danger font-weight-bold"
    else:
        kpi_status = "Stable (Periodic)"
        kpi_class = "text-success font-weight-bold"

    layout_temp = 'plotly_white'
    fig1 = go.Figure()
    if 1 in selected:
        fig1.add_trace(go.Scattergl(x=bif_g, y=bif_h1, mode='markers', marker=dict(symbol='square', size=2, color='#2c3e50'), name="Bus 1"))
    if 2 in selected:
        fig1.add_trace(go.Scattergl(x=bif_g2, y=bif_h2, mode='markers', marker=dict(symbol='square', size=2, color='#ff7f0e'), name="Bus 2"))
    if not selected:
        fig1 = empty_figure("Headway Bifurcation")
    fig1.update_layout(template=layout_temp, title="Headway Bifurcation", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=p1_x), yaxis=dict(range=p1_y))

    fig2 = go.Figure()
    if 1 in selected:
        fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t1, mode='markers', marker=dict(size=2, color='#1f77b4'), name="Bus 1"))
    if 2 in selected:
        fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t2, mode='markers', marker=dict(size=2, color='#ff7f0e'), name="Bus 2"))
    if not selected:
        fig2 = empty_figure("Tour Times")
    fig2.update_layout(template=layout_temp, title="Tour Times", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=p1_x), yaxis=dict(range=p1_y))

    fig3 = go.Figure()
    if 1 in selected:
        fig3.add_trace(go.Scatter(x=x_ret, y=y_ret, mode='markers', marker=dict(symbol='circle-open', size=4, color='#2c3e50', line=dict(width=1)), name=f"Bus 1, Gamma={target_gamma}"))
    if 2 in selected:
        fig3.add_trace(go.Scatter(x=x_ret2, y=y_ret2, mode='markers', marker=dict(symbol='circle-open', size=4, color='#ff7f0e', line=dict(width=1)), name=f"Bus 2, Gamma={target_gamma}"))
    if selected:
        fig3.add_trace(go.Scatter(x=[0.0, 1.5], y=[0.0, 1.5], mode='lines', line=dict(color='#7f8c8d', width=1, dash='dash'), showlegend=False))
    else:
        fig3 = empty_figure("Return Map")
    fig3.update_layout(template=layout_temp, title=f"Return Map (Gamma={target_gamma})", xaxis_title="Headway at trip m", yaxis_title="Headway at trip m+1", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=[-0.1, 1.6]), yaxis=dict(range=[-0.1, 1.6], scaleanchor="x", scaleratio=1))

    fig4_mean = go.Figure()
    fig4_mean.add_traces([
        go.Scatter(x=gamma_values, y=mean_h1, line=dict(color='#1f77b4'), name="Mean H1"), go.Scatter(x=gamma_values, y=mean_h2, line=dict(color='#ff7f0e'), name="Mean H2"),
        go.Scatter(x=gamma_values, y=mean_t1, line=dict(color='#2ca02c'), name="Mean ΔT1"), go.Scatter(x=gamma_values, y=mean_t2, line=dict(color='#d62728'), name="Mean ΔT2")
    ])
    fig4_mean.update_layout(template=layout_temp, title="Mean Values", xaxis=dict(range=p3_x), yaxis=dict(range=p3_y))

    fig4_rms = go.Figure()
    fig4_rms.add_traces([
        go.Scatter(x=gamma_values, y=rms_h1, line=dict(color='#1f77b4'), name="RMS H1"), go.Scatter(x=gamma_values, y=rms_h2, line=dict(color='#ff7f0e'), name="RMS H2"),
        go.Scatter(x=gamma_values, y=rms_t1, line=dict(color='#2ca02c'), name="RMS ΔT1"), go.Scatter(x=gamma_values, y=rms_t2, line=dict(color='#d62728'), name="RMS ΔT2")
    ])
    fig4_rms.update_layout(template=layout_temp, title="RMS Variation", xaxis=dict(range=p3_x), yaxis=dict(range=p3_y))

    sweep_gamma_values = [g for g in gamma_values if 0.0 < g < 2.0]
    fig4_mean = go.Figure()
    if 1 in selected:
        fig4_mean.add_trace(go.Scatter(x=sweep_gamma_values, y=mean_h1, line=dict(color='#1f77b4'), name="Mean H1"))
        fig4_mean.add_trace(go.Scatter(x=sweep_gamma_values, y=mean_t1, line=dict(color='#2ca02c'), name="Mean DT1"))
    if 2 in selected:
        fig4_mean.add_trace(go.Scatter(x=sweep_gamma_values, y=mean_h2, line=dict(color='#ff7f0e'), name="Mean H2"))
        fig4_mean.add_trace(go.Scatter(x=sweep_gamma_values, y=mean_t2, line=dict(color='#d62728'), name="Mean DT2"))
    if not selected:
        fig4_mean = empty_figure("Mean Values")
    fig4_mean.update_layout(template=layout_temp, title="Mean Values", xaxis=dict(range=p3_x), yaxis=dict(range=p3_y))

    fig4_rms = go.Figure()
    if 1 in selected:
        fig4_rms.add_trace(go.Scatter(x=sweep_gamma_values, y=rms_h1, line=dict(color='#1f77b4'), name="RMS H1"))
        fig4_rms.add_trace(go.Scatter(x=sweep_gamma_values, y=rms_t1, line=dict(color='#2ca02c'), name="RMS DT1"))
    if 2 in selected:
        fig4_rms.add_trace(go.Scatter(x=sweep_gamma_values, y=rms_h2, line=dict(color='#ff7f0e'), name="RMS H2"))
        fig4_rms.add_trace(go.Scatter(x=sweep_gamma_values, y=rms_t2, line=dict(color='#d62728'), name="RMS DT2"))
    if not selected:
        fig4_rms = empty_figure("RMS Variation")
    fig4_rms.update_layout(template=layout_temp, title="RMS Variation", xaxis=dict(range=p3_x), yaxis=dict(range=p3_y))

    fig5 = go.Figure()
    sim_points_x = [g for g in PHASE_G_SIM if g is not None]
    sim_points_y = [s for g, s in zip(PHASE_G_SIM, PHASE_S) if g is not None]
    fig5.add_trace(go.Scatter(x=sim_points_x, y=sim_points_y, mode='markers', marker=dict(color='#2c3e50', size=6), name="Simulation"))
    
    s_smooth = [i/100 for i in range(151)]
    g_smooth = [shuttle_bus.equal_speed_transition_formula(s) for s in s_smooth]
    fig5.add_trace(go.Scatter(x=g_smooth, y=s_smooth, mode='lines', name="Theory: Gamma=S/(1+S)", line=dict(color='#e74c3c', width=2)))
    
    fig5.add_trace(go.Scatter(x=[target_gamma], y=[s1], mode='markers', marker=dict(size=16, symbol='star', color='#f1c40f', line=dict(width=2, color='black')), name="Current Configuration"))
        
    fig5.update_layout(template=layout_temp, title="Phase Diagram", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=[0.0, 2.0]), yaxis=dict(range=[0.0, 1.5]), legend=dict(x=0.01, y=0.99))

    fig6_anim = build_animation_figure(diverged_status, target_gamma, s1, s2)

    return kpi_status, kpi_class, kpi_h1_text, kpi_h2_text, fig1, fig2, fig3, fig4_mean, fig4_rms, fig5, fig6_anim

if __name__ == '__main__':
    app.run(debug=True)
