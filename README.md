# Tái lập bài báo "Chaos control and schedule of shuttle buses"

Project này implement lại mô hình và các hình kết quả chính của bài:

Takashi Nagatani, "Chaos control and schedule of shuttle buses", *Physica A: Statistical Mechanics and its Applications*, 371(2), 683-691, 2006, DOI `10.1016/j.physa.2006.04.056`.

Nguồn đối chiếu:

- PDF gốc người dùng cung cấp: `c:\Users\ADMIN\Desktop\2025.2\Math_modelling\Traffic Flow\references\Chaos control and schedule of shuttle buses.pdf`
- Metadata/abstract ScienceDirect: <https://www.sciencedirect.com/science/article/abs/pii/S0378437106004754>
- Bản preview OCR công khai dùng để kiểm tra phương trình và caption hình: <https://www.scribd.com/document/882586440/Chaos-Control-and-Schedule-of-Shuttle-Buses>
- Poster tái lập độc lập có cùng map dimensionless: <https://math.arizona.edu/~gabitov/teaching/101/math_485_585/Posters/ChaosBusShuttle_485.pdf>

## Mô hình đã implement

Hệ gồm `M` shuttle bus đi qua lại giữa origin và destination. Mỗi lần bus `i` vừa về origin ở trip `m`, bus nhìn lại lượt bus đến origin ngay trước nó. Headway dimensionless là:

```text
H_i(m) = T_i(m) - T_i'(m')
```

Trong đó `i'` và `m'` là bus và trip của lượt đến ngay trước đó. Map dimensionless của bài báo là:

```text
T_i(m+1) = T_i(m) + Gamma * H_i(m) + 1 / (1 + S_i * H_i(m))
```

Ý nghĩa:

- `Gamma`: loading parameter, gom tốc độ hành khách đến, thời gian boarding và alighting.
- `S_i`: speedup parameter của bus `i`.
- `Gamma * H_i(m)`: delay do loading/unloading.
- `1 / (1 + S_i * H_i(m))`: moving time giảm khi bus tăng tốc để bù delay.
- `Delta T_i(m) = T_i(m+1)-T_i(m)`: tour time.

Mô phỏng dùng hàng đợi sự kiện theo thời gian đến origin, vì bài báo cho phép bus vượt nhau tự do. Cách này quan trọng hơn việc cập nhật bus 1 rồi bus 2 theo thứ tự cố định.

## File chính

- `shuttle_bus.py`: model, simulator, thống kê mean/RMS, phân loại regular/periodic/chaotic.
- `reproduce.py`: tạo toàn bộ CSV và SVG cho các hình Fig. 2 đến Fig. 8.
- `svg_plot.py`: plot SVG thuần Python, không cần `matplotlib`.
- `validate.py`: kiểm tra nhanh các mốc định lượng của bài.
- `outputs/`: sinh ra sau khi chạy reproduction.

## Cách chạy

Từ thư mục này:

```powershell
python validate.py
python reproduce.py
```

Không cần cài thêm thư viện ngoài. Code chỉ dùng Python standard library.

Sau khi chạy, mở các file trong:

```text
outputs/figures/
outputs/data/
```

## Các hình được tái lập

`reproduce.py` tạo:

- `fig2_headway_bifurcation.svg`: `H1(m)` theo `Gamma`, trips `m=900...1000`, bốn case speedup:
  - `(a) S1=S2=0`
  - `(b) S1=S2=0.2`
  - `(c) S1=0.3, S2=0.2`
  - `(d) S1=0.5, S2=0.2`
- `fig3_headway_bifurcation_zoom.svg`: enlargement `0 < Gamma < 0.5`.
- `fig4_tour_times.svg`: `Delta T1(m)` và `Delta T2(m)` cho `S1=0.5, S2=0.2`.
- `fig5_tour_times_zoom.svg`: enlargement `0 < Gamma < 0.5`.
- `fig6_return_maps.svg`: return maps `H1(m+1)` theo `H1(m)` với `Gamma=0.2, 0.3, 0.5, 0.8`.
- `fig7_mean_rms.svg`: mean và RMS variation của headway/tour time.
- `fig8_phase_diagram.svg`: transition regular sang periodic/chaotic khi `S1=S2`.

Mọi hình đều có CSV tương ứng trong `outputs/data/`.

## Mốc kiểm chứng

Các mốc bài báo nêu và code dùng để kiểm chứng:

- Với speedup bằng nhau `S1=S2=0.2`, fluctuation bị suppress đến `Gamma ~= 0.167`.
- Với `S1=0.5, S2=0.2`, transition đầu tiên cũng ở `Gamma ~= 0.167`.
- Case `S1=0.5, S2=0.2` có các transition tiếp theo quanh `Gamma ~= 0.248` và `Gamma ~= 0.407`.
- Return map dùng `Gamma=0.2, 0.3, 0.5, 0.8`, đúng caption Fig. 6.
- Với no speedup, khi `Gamma > 2`, delay/headway phân kỳ.

`validate.py` kiểm tra các điểm này ở mức cần thiết để phát hiện sai implementation.

## Lưu ý về điều kiện đầu

Bài báo không chỉ rõ điều kiện đầu. Project dùng `T1(0)=0`, `T2(0)=0.5` cho case hai bus, rồi bỏ transient dài và chỉ lấy trips `900...1000` hoặc `1000...2000` như bài báo. Với hệ hỗn loạn, hình chi tiết có thể đổi nhẹ theo điều kiện đầu, nhưng các transition và cấu trúc bifurcation chính được giữ.
