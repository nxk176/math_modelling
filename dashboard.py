import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from dash.dependencies import State

# Import core simulation logic from your existing file
import shuttle_bus

# ----- Tiền xử lý dữ liệu biểu đồ Phase Diagram tĩnh -----
# Biểu đồ pha (Phase Diagram) mất khá nhiều thời gian để tính toán (30 điểm x mô phỏng vòng lặp dài).
# Vì biểu đồ này không bị ảnh hưởng bởi tham số s1, s2 thay đổi liên tục, ta tính toán 1 lần lúc bật web.
PHASE_S = tuple(i / 20 for i in range(0, 31))  # S chạy từ 0.00 đến 1.50
PHASE_G_FORMULA = tuple(shuttle_bus.equal_speed_transition_formula(s) for s in PHASE_S)
try:
    # Ưu tiên tái sử dụng dữ liệu đã chạy sẵn trong file CSV nếu có
    import csv
    with open('outputs/data/fig8_phase_transition_equal_speedup.csv', 'r') as f:
        reader = csv.DictReader(f)
        PHASE_G_SIM = [float(row['gamma_transition_sim']) if row['gamma_transition_sim'] != 'nan' else None for row in reader]
except Exception:
    # Nếu file csv không tồn tại, tự động tính lại toán học
    PHASE_G_SIM = tuple(shuttle_bus.estimate_equal_speed_transition(s) for s in PHASE_S)

app = dash.Dash(__name__, title="Shuttle Bus Chaos Dashboard")

# Inline CSS for a clean Layout
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'margin': '20px', 'maxWidth': '1400px', 'marginLeft': 'auto', 'marginRight': 'auto'}, children=[
    html.H1("Shuttle Bus Chaos Simulation Dashboard", style={'textAlign': 'center', 'color': '#2c3e50'}),
    
    # Global Controls that affect multiple panels
    html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'border': '1px solid #dee2e6', 'borderRadius': '5px', 'marginBottom': '20px'}, children=[
        html.Div(style={'width': '30%', 'minWidth': '250px', 'margin': '0 15px'}, children=[
            html.H5("Tốc độ Xe 1 (S1)", style={'margin': '5px 0'}),
            dcc.Slider(id='s1-slider', min=0.0, max=1.0, step=0.1, value=0.5, marks={i/10: str(i/10) for i in range(11)}),
        ]),
        html.Div(style={'width': '30%', 'minWidth': '250px', 'margin': '0 15px'}, children=[
            html.H5("Tốc độ Xe 2 (S2)", style={'margin': '5px 0'}),
            dcc.Slider(id='s2-slider', min=0.0, max=1.0, step=0.1, value=0.2, marks={i/10: str(i/10) for i in range(11)}),
        ]),
    ]),
    
    html.P("Lưu ý: Quá trình quét Gamma (1000 mẫu) để vẽ biểu đồ có thể mất khoảng 2-4 giây sau khi đổi tham số. Vui lòng chờ.", style={'textAlign': 'center', 'color': '#666', 'fontStyle': 'italic', 'fontSize': '14px'}),
    
    dcc.Loading(type="circle", children=[
        dcc.Tabs(id="tabs-styled", style={'height': '44px'}, children=[
            # Panel 1: Headway & Tour Times
            dcc.Tab(label='Panel 1: Headway & Tour Times', style={'padding': '6px'}, selected_style={'padding': '6px', 'fontWeight': 'bold'}, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '20px'}, children=[
                    html.Div(style={'width': '45%', 'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px'}, children=[
                        html.Label(html.B("Trục X (Gamma) - Range:")),
                        dcc.RangeSlider(id='p1-x-range', min=0.0, max=2.5, step=0.1, value=[0.0, 2.05], marks={i/10: str(i/10) for i in range(0, 26, 5)}),
                    ]),
                    html.Div(style={'width': '45%', 'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px'}, children=[
                        html.Label(html.B("Trục Y (Values) - Range:")),
                        dcc.RangeSlider(id='p1-y-range', min=0.0, max=20.0, step=1.0, value=[0.0, 6.0], marks={i: str(i) for i in range(0, 21, 5)}),
                    ])
                ]),
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'paddingTop': '20px'}, children=[
                    dcc.Graph(id='fig1-headway', style={'width': '49%', 'height': '600px'}),
                    dcc.Graph(id='fig2-tourtime', style={'width': '49%', 'height': '600px'}),
                ])
            ]),
            
            # Panel 2: Return Map
            dcc.Tab(label='Panel 2: Return Map', style={'padding': '6px'}, selected_style={'padding': '6px', 'fontWeight': 'bold'}, children=[
                html.Div(style={'padding': '20px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px', 'marginTop': '20px', 'width': '50%', 'margin': '20px auto 0 auto'}, children=[
                    html.H5("Tham số độ trễ (Gamma)", style={'margin': '0 0 10px 0', 'textAlign': 'center'}),
                    dcc.Slider(id='gamma-slider', min=0.0, max=2.0, step=0.1, value=0.5, marks={i/10: str(i/10) for i in range(21)}),
                ]),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'paddingTop': '20px'}, children=[
                    dcc.Graph(id='fig3-returnmap', style={'width': '600px', 'height': '600px'}),
                ])
            ]),
            
            # Panel 3: Mean & RMS
            dcc.Tab(label='Panel 3: Mean & RMS', style={'padding': '6px'}, selected_style={'padding': '6px', 'fontWeight': 'bold'}, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '20px'}, children=[
                    html.Div(style={'width': '45%', 'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px'}, children=[
                        html.Label(html.B("Trục X (Gamma) - Range:")),
                        dcc.RangeSlider(id='p3-x-range', min=0.0, max=2.5, step=0.1, value=[0.0, 2.05], marks={i/10: str(i/10) for i in range(0, 26, 5)}),
                    ]),
                    html.Div(style={'width': '45%', 'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px'}, children=[
                        html.Label(html.B("Trục Y (Value) - Range:")),
                        dcc.RangeSlider(id='p3-y-range', min=0.0, max=6.0, step=0.5, value=[0.0, 5.0], marks={i: str(i) for i in range(0, 7, 1)}),
                    ])
                ]),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'paddingTop': '20px'}, children=[
                    dcc.Graph(id='fig4-mean', style={'width': '49%', 'height': '600px'}),
                    dcc.Graph(id='fig4-rms', style={'width': '49%', 'height': '600px'}),
                ])
            ]),
            
            # Panel 4: Phase Diagram
            dcc.Tab(label='Panel 4: Phase Diagram', style={'padding': '6px'}, selected_style={'padding': '6px', 'fontWeight': 'bold'}, children=[
                html.P("Biểu đồ ranh giới chuyển pha (Phase diagram). Trục X là Gamma, Trục Y là S.", style={'textAlign': 'center', 'marginTop': '20px', 'fontStyle': 'italic'}),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'paddingTop': '10px'}, children=[
                    dcc.Graph(id='fig5-phase', style={'width': '800px', 'height': '600px'}),
                ])
            ])
        ])
    ])
])

@app.callback(
    [
        Output('fig1-headway', 'figure'),
        Output('fig2-tourtime', 'figure'),
        Output('fig3-returnmap', 'figure'),
        Output('fig4-mean', 'figure'),
        Output('fig4-rms', 'figure'),
        Output('fig5-phase', 'figure')
    ],
    [
        Input('s1-slider', 'value'),
        Input('s2-slider', 'value'),
        Input('gamma-slider', 'value'),
        Input('p1-x-range', 'value'),
        Input('p1-y-range', 'value'),
        Input('p3-x-range', 'value'),
        Input('p3-y-range', 'value'),
    ]
)
def update_graphs(s1, s2, target_gamma, p1_x, p1_y, p3_x, p3_y):
    # Param sweep configs (Tăng resolution lên 1000 để khớp với mật độ của hình ảnh gốc)
    gamma_count = 1000
    gamma_values = shuttle_bus.gamma_values(0.0, 2.0, gamma_count)
    
    # 1 & 2 & 4. Sweep qua chuỗi Gamma để vẽ Bifurcation, Tour times và Mean/RMS
    bif_g = []
    bif_h1 = []
    
    tour_g = []
    tour_t1 = []
    tour_t2 = []
    
    mean_h1, rms_h1 = [], []
    mean_h2, rms_h2 = [], []
    mean_t1, rms_t1 = [], []
    mean_t2, rms_t2 = [], []
    
    for g in gamma_values:
        # Bỏ qua biên 0.0 và 2.0 theo "open domain"
        if g <= 0.0 or g >= 2.0:
            continue
        
        res = shuttle_bus.simulate(g, (s1, s2), trips=1050)
        
        if res.diverged:
            mean_h1.append(None); rms_h1.append(None)
            mean_h2.append(None); rms_h2.append(None)
            mean_t1.append(None); rms_t1.append(None)
            mean_t2.append(None); rms_t2.append(None)
            continue
            
        h1_window = shuttle_bus.inclusive_window(res.headways[0], 900, 1000)
        h2_window = shuttle_bus.inclusive_window(res.headways[1], 900, 1000)
        t1_window = shuttle_bus.inclusive_window(res.tour_times[0], 900, 1000)
        t2_window = shuttle_bus.inclusive_window(res.tour_times[1], 900, 1000)
        
        # Cho scatter plot - áp dụng stride=2 (lấy xen kẽ) giống mã nguồn gốc
        stride = 2
        bif_g.extend([g] * len(h1_window[::stride]))
        bif_h1.extend(h1_window[::stride])
        
        tour_g.extend([g] * len(t1_window[::stride]))
        tour_t1.extend(t1_window[::stride])
        tour_t2.extend(t2_window[::stride])
        
        # Cho Mean/RMS plot (luôn dùng toàn bộ chuỗi theo công thức)
        mean_h1.append(shuttle_bus.mean(h1_window))
        rms_h1.append(shuttle_bus.rms_variation(h1_window))
        mean_h2.append(shuttle_bus.mean(h2_window))
        rms_h2.append(shuttle_bus.rms_variation(h2_window))
        mean_t1.append(shuttle_bus.mean(t1_window))
        rms_t1.append(shuttle_bus.rms_variation(t1_window))
        mean_t2.append(shuttle_bus.mean(t2_window))
        rms_t2.append(shuttle_bus.rms_variation(t2_window))

    # --- Hình 1: Headway Bifurcation ---
    fig1 = go.Figure()
    fig1.add_trace(go.Scattergl(x=bif_g, y=bif_h1, mode='markers', marker=dict(symbol='square', size=2, color='#000000'), name="H1"))
    fig1.update_layout(
        title="1. Phân nhánh Headway (H1)", xaxis_title="Gamma", yaxis_title="H1(m)", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=p1_x),
        yaxis=dict(range=p1_y)
    )

    # --- Hình 2: Tour Times ---
    fig2 = go.Figure()
    fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t1, mode='markers', marker=dict(symbol='square', size=2, color='#000000'), name="Bus 1 (ΔT1)"))
    fig2.add_trace(go.Scattergl(x=tour_g, y=tour_t2, mode='markers', marker=dict(symbol='square', size=2, color='#000000'), name="Bus 2 (ΔT2)"))
    fig2.update_layout(
        title="2. Tour Times", xaxis_title="Gamma", yaxis_title="ΔT(m)", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=p1_x),
        yaxis=dict(range=p1_y)
    )

    # --- Hình 3: Return Map ---
    # Bỏ qua biên 2.0 nếu target_gamma >= 2.0
    if target_gamma >= 2.0 or target_gamma <= 0.0:
        res_ret = type('Obj', (object,), {'diverged': True})()
    else:
        res_ret = shuttle_bus.simulate(target_gamma, (s1, s2), trips=2050)
        
    if not res_ret.diverged:
        h1_full = shuttle_bus.inclusive_window(res_ret.headways[0], 1000, 2000)
        # Ap dụng stride=2 giống Hình 6 của tác giả
        x_ret = h1_full[:-1][::2]
        y_ret = h1_full[1:][::2]
    else:
        x_ret, y_ret = [], []
        
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=x_ret, y=y_ret, mode='markers', marker=dict(symbol='square', size=3, color='#000000'), name=f"Gamma={target_gamma}"))
    # Vẽ đường thẳng y = x (đường biểu diễn đồ thị map)
    fig3.add_trace(go.Scatter(x=[0.0, 1.5], y=[0.0, 1.5], mode='lines', line=dict(color='#777777', width=1.1), name="y=x"))
    
    fig3.update_layout(
        title=f"3. Return Map (Gamma={target_gamma})", xaxis_title="H1(m)", yaxis_title="H1(m+1)", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=[0.0, 1.5], constrain='domain', tickmode='array', tickvals=[0.0, 0.5, 1.0, 1.5]),
        yaxis=dict(range=[0.0, 1.5], scaleanchor="x", scaleratio=1, constrain='domain', tickmode='array', tickvals=[0.5, 1.0, 1.5]) # Hide 0 on Y-axis to prevent overlap
    )

    # --- Hình 4: Mean & RMS ---
    fig4_mean = go.Figure()
    fig4_mean.add_trace(go.Scatter(x=gamma_values, y=mean_h1, mode='lines', line=dict(color='#1f77b4', width=2), name="H1a"))
    fig4_mean.add_trace(go.Scatter(x=gamma_values, y=mean_h2, mode='lines', line=dict(color='#ff7f0e', width=2), name="H2a"))
    fig4_mean.add_trace(go.Scatter(x=gamma_values, y=mean_t1, mode='lines', line=dict(color='#2ca02c', width=2), name="DT1a"))
    fig4_mean.add_trace(go.Scatter(x=gamma_values, y=mean_t2, mode='lines', line=dict(color='#d62728', width=2), name="DT2a"))
    fig4_mean.update_layout(
        title="4a. Mean Values", xaxis_title="Loading parameter Gamma", yaxis_title="Mean value", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=p3_x),
        yaxis=dict(range=p3_y)
    )

    fig4_rms = go.Figure()
    fig4_rms.add_trace(go.Scatter(x=gamma_values, y=rms_h1, mode='lines', line=dict(color='#1f77b4', width=2), name="H1v"))
    fig4_rms.add_trace(go.Scatter(x=gamma_values, y=rms_h2, mode='lines', line=dict(color='#ff7f0e', width=2), name="H2v"))
    fig4_rms.add_trace(go.Scatter(x=gamma_values, y=rms_t1, mode='lines', line=dict(color='#2ca02c', width=2), name="DT1v"))
    fig4_rms.add_trace(go.Scatter(x=gamma_values, y=rms_t2, mode='lines', line=dict(color='#d62728', width=2), name="DT2v"))
    fig4_rms.update_layout(
        title="4b. RMS Variations", xaxis_title="Loading parameter Gamma", yaxis_title="RMS variation", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=p3_x),
        yaxis=dict(range=p3_y)
    )

    # --- Hình 5: Phase Diagram ---
    fig5 = go.Figure()
    
    # 1. Vẽ các điểm giả lập (simulation points - Chấm đen dày, bán kính to như svg_plot)
    sim_points_x = [g for g in PHASE_G_SIM if g is not None]
    sim_points_y = [s for g, s in zip(PHASE_G_SIM, PHASE_S) if g is not None]
    fig5.add_trace(go.Scatter(x=sim_points_x, y=sim_points_y, mode='markers', marker=dict(color='#000000', size=6), name="simulation"))
    
    # 2. Vẽ đường công thức giải tích phân rã (Analytic formulat - Đường đỏ, độ dày 2.0)
    # Lấy smooth rendering với độ chia siêu mịn (151 điểm) để đường cong đẹp mượt
    s_smooth = [i/100 for i in range(151)]
    g_smooth = [shuttle_bus.equal_speed_transition_formula(s) for s in s_smooth]
    fig5.add_trace(go.Scatter(x=g_smooth, y=s_smooth, mode='lines', name="Gamma=S/(1+S)", line=dict(color='#d62728', width=2)))
    
    # Optional: Highlight current state if S1==S2
    if s1 == s2:
        curr_g = shuttle_bus.equal_speed_transition_formula(s1)
        fig5.add_trace(go.Scatter(x=[curr_g], y=[s1], mode='markers', marker=dict(size=12, symbol='star', color='#1f77b4'), name="Current S1=S2"))
        
    fig5.update_layout(
        title="5. Phase diagram: regular / periodic-chaotic transition", xaxis_title="Loading parameter Gamma", yaxis_title="Speedup parameter S", 
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(range=[0.0, 0.8], tickmode='array', tickvals=[0.0, 0.2, 0.4, 0.6, 0.8]),
        yaxis=dict(range=[0.0, 1.5], tickmode='array', tickvals=[0.5, 1.0, 1.5]) # Hide 0 on Y-axis to prevent overlap
    )

    return fig1, fig2, fig3, fig4_mean, fig4_rms, fig5


if __name__ == '__main__':
    app.run(debug=True)