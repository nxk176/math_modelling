import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import csv

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
                    html.P("Buses moving on a circular route. The bus with the higher Speed (S) acts as the pursuer during bunching events.", className="mt-3 text-center text-muted"),
                    dbc.Row([dbc.Col(dcc.Graph(id='fig6-animation', style={'height': '700px'}), width={'size': 10, 'offset': 1})])
                ], className="p-3 border border-top-0 bg-white"),
                
            ], id="tabs", active_tab="tab-2")
        ])
    ],
    style={"padding": "30px", "backgroundColor": "#f4f6f8", "minHeight": "100vh"}
)

app.layout = dbc.Container([dbc.Row([dbc.Col(sidebar, width=3, className="p-0"), dbc.Col(content, width=9, className="p-0")], className="m-0")], fluid=True, className="p-0")

# ==========================================
# 3. ANIMATION FUNCTION
# ==========================================
def build_animation_figure(diverged, gamma, s1, s2):
    num_frames = 250
    theta_track = np.linspace(0, 2*np.pi, 100)
    x_track, y_track = np.cos(theta_track), np.sin(theta_track)

    num_stops = 8
    theta_stops = np.linspace(0, 2*np.pi, num_stops, endpoint=False)
    x_stops, y_stops = np.cos(theta_stops), np.sin(theta_stops)

    fig = go.Figure(
        data=[
            go.Scatter(x=x_track, y=y_track, mode='lines', line=dict(color='#bdc3c7', width=4), showlegend=False, hoverinfo='skip'),
            go.Scatter(x=x_stops, y=y_stops, mode='markers', marker=dict(color='#7f8c8d', size=14, symbol='square-open', line=dict(width=2)), name='Bus Stop'),
            go.Scatter(x=[1], y=[0], mode='markers', marker=dict(color='#1f77b4', size=20, line=dict(width=2, color='white')), name='Bus 1 (Blue)'),
            go.Scatter(x=[-1], y=[0], mode='markers', marker=dict(color='#ff7f0e', size=20, line=dict(width=2, color='white')), name='Bus 2 (Orange)'),
            go.Scatter(x=x_stops * 1.15, y=y_stops * 1.15, mode='text', text=["0"]*num_stops, textfont=dict(size=12, color='red'), name='Passengers')
        ]
    )

    frames = []
    theta1, theta2 = 0.0, np.pi
    passengers = np.zeros(num_stops)
    base_speed = 0.08
    
    hunter = 1 if s1 > s2 else 2 
    
    for i in range(num_frames):
        passengers += (gamma * 0.5)
        
        at_stop_1 = np.argmin(np.abs(np.angle(np.exp(1j * (theta_stops - theta1)))))
        at_stop_2 = np.argmin(np.abs(np.angle(np.exp(1j * (theta_stops - theta2)))))
        
        dist_1 = np.abs(np.angle(np.exp(1j * (theta_stops[at_stop_1] - theta1))))
        dist_2 = np.abs(np.angle(np.exp(1j * (theta_stops[at_stop_2] - theta2))))
        
        speed1, speed2 = base_speed, base_speed
        
        if dist_1 < 0.1:
            delay1 = passengers[at_stop_1] * gamma * 0.05
            speed1 = max(0.01, base_speed - delay1) + (s1 * 0.015)
            passengers[at_stop_1] = 0
            
        if dist_2 < 0.1:
            delay2 = passengers[at_stop_2] * gamma * 0.05
            speed2 = max(0.01, base_speed - delay2) + (s2 * 0.015)
            passengers[at_stop_2] = 0
            
        if diverged:
            gap = np.angle(np.exp(1j * (theta1 - theta2))) 
            
            if hunter == 2:
                if gap > 0.1: speed2 += 0.02
                elif 0 <= gap <= 0.1: speed2 += 0.05 
            elif hunter == 1:
                if gap < -0.1: speed1 += 0.02
                elif -0.1 <= gap <= 0: speed1 += 0.05 

        theta1 += speed1
        theta2 += speed2

        p_texts = [f"{int(p)} pax" for p in passengers]
        frames.append(go.Frame(data=[go.Scatter(x=[np.cos(theta1)], y=[np.sin(theta1)]), go.Scatter(x=[np.cos(theta2)], y=[np.sin(theta2)]), go.Scatter(text=p_texts)], traces=[2, 3, 4], name=f'frame{i}'))

    fig.frames = frames
    fig.update_layout(template='plotly_white', xaxis=dict(range=[-1.5, 1.5], showgrid=False, zeroline=False, visible=False), yaxis=dict(range=[-1.5, 1.5], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1), margin=dict(l=40, r=40, t=20, b=20),
        updatemenus=[dict(type="buttons", showactive=False, x=0.5, y=-0.1, xanchor="center", yanchor="top", direction="left",
            buttons=[dict(label="Play Simulation", method="animate", args=[None, dict(frame=dict(duration=50, redraw=False), fromcurrent=True, transition=dict(duration=0))]),
                     dict(label="Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])])]
    )
    return fig

# ==========================================
# 4. MAIN CALLBACK
# ==========================================
@app.callback(
    [Output('kpi-status', 'children'), Output('kpi-status', 'className'), Output('kpi-h1', 'children'), Output('kpi-h2', 'children'), Output('fig1-headway', 'figure'), Output('fig2-tourtime', 'figure'), Output('fig3-returnmap', 'figure'), Output('fig4-mean', 'figure'), Output('fig4-rms', 'figure'), Output('fig5-phase', 'figure'), Output('fig6-animation', 'figure')],
    [Input('run-button', 'n_clicks')],
    [State('s1-slider', 'value'), State('s2-slider', 'value'), State('gamma-slider', 'value'), State('p1-x-range', 'value'), State('p1-y-range', 'value'), State('p3-x-range', 'value'), State('p3-y-range', 'value')]
)
def update_dashboard(n_clicks, s1, s2, target_gamma, p1_x, p1_y, p3_x, p3_y):
    gamma_values = shuttle_bus.gamma_values(0.0, 2.0, 1000)
    
    bif_g, bif_h1, tour_g, tour_t1, tour_t2 = [], [], [], [], []
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
        x_ret, y_ret = [], []
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
        except Exception:
            x_ret, y_ret = [], []
            
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
    fig1 = go.Figure(go.Scattergl(x=bif_g, y=bif_h1, mode='markers', marker=dict(symbol='square', size=2, color='#2c3e50')))
    fig1.update_layout(template=layout_temp, title="Headway Bifurcation (H1)", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=p1_x), yaxis=dict(range=p1_y))

    fig2 = go.Figure()
    fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t1, mode='markers', marker=dict(size=2, color='#1f77b4'), name="Bus 1"))
    fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t2, mode='markers', marker=dict(size=2, color='#ff7f0e'), name="Bus 2"))
    fig2.update_layout(template=layout_temp, title="Tour Times", margin=dict(l=40, r=40, t=50, b=40), xaxis=dict(range=p1_x), yaxis=dict(range=p1_y))

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=x_ret, y=y_ret, mode='markers', marker=dict(symbol='circle-open', size=4, color='#2c3e50', line=dict(width=1)), name=f"Gamma={target_gamma}"))
    fig3.add_trace(go.Scatter(x=[0.0, 1.5], y=[0.0, 1.5], mode='lines', line=dict(color='#7f8c8d', width=1, dash='dash'), showlegend=False))
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