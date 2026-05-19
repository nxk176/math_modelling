# Reproduction summary

Generated artifacts:

- `figures/fig2_headway_bifurcation.svg`
- `figures/fig3_headway_bifurcation_zoom.svg`
- `figures/fig4_tour_times.svg`
- `figures/fig5_tour_times_zoom.svg`
- `figures/fig6_return_maps.svg`
- `figures/fig7_mean_rms.svg`
- `figures/fig8_phase_diagram.svg`
- `data/*.csv`

Key checkpoints from the paper:

- Equal speedup `S1=S2=0.2` suppresses fluctuation until `Gamma ~= 0.167`.
- For `S1=0.5, S2=0.2`, the first transition is also near `Gamma ~= 0.167`.
- The reported later transitions are near `Gamma ~= 0.248` and `Gamma ~= 0.407`.
- For `Gamma > 2`, delays/headways diverge in this dimensionless model.

The SVG plots are dependency-free browser-viewable reproductions generated from
the CSV files.
