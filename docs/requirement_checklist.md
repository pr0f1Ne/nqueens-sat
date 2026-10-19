# Đối chiếu yêu cầu và bằng chứng

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Mô hình N-Queens SAT, ALO/AMO/EO | Hoàn thành | `sat_encoding.py`, `docs/sat_encodings.md`, kiểm thử SAT |
| Pairwise, sequential, bitwise trên Glucose3 | Hoàn thành | `sat_solver.py`, `results/official_group_a/...` |
| CP-SAT | Hoàn thành trong môi trường | `cpsat_solver.py`, `docs/cpsat_model.md`, nhóm B |
| CPLEX MIP | Chạy được có giới hạn | `cplex_mip_solver.py`, `docs/cplex_mip_model.md`; UNAVAILABLE tại N=32,64 |
| Gurobi MIP | Hoàn thành có giới hạn | Backend, CLI, benchmark, test thật; N=64 UNAVAILABLE do size-limited license |
| IBM CP Optimizer | Hoàn thành trong môi trường | DOcplex.CP + runtime thật; N=8,16,32,64 đều SAT trong lượt bổ sung |
| Benchmark có timeout, lặp, metadata | Hoàn thành | `benchmark.py`, `docs/benchmark_protocol.md` |
| Pilot và lượt chính thức | Hoàn thành trong phạm vi | `results/pilot_*`, `results/official_*` |
| N=128,256 | Chưa chạy | Loại khỏi lượt chính thức sau pilot timeout/rủi ro tài nguyên |
| Phân tích và biểu đồ | Hoàn thành | `analyze_results.py`, `results/analysis_20261017/`, `docs/results_analysis.md` |
| Báo cáo theo cas-sc | Đã soạn và compile thành công | `report/main.tex`; dùng Times New Roman 10 pt, giãn dòng gần đơn theo PDF mẫu |
| Thông tin tác giả/đơn vị | Hoàn thành | Tác giả và đơn vị đã được điền ở đầu `report/main.tex` |
| URL repository | Hoàn thành | <https://github.com/pr0f1Ne/nqueens-sat> và phần Data Availability |
| Nguồn LaTeX của mẫu giảng viên | Chưa có | Chỉ có PDF tham khảo, không có `.tex`, `.cls` hoặc hướng dẫn nộp chi tiết |
| PDF nộp cuối | Cần xuất/kiểm tra cuối | Compiler tích hợp xác nhận nguồn hợp lệ; cần xuất PDF sau khi điền thông tin tác giả và xem lại toàn bộ trang |
| Tuyên bố sử dụng công cụ AI | Chờ yêu cầu môn học | PDF mẫu có một tuyên bố ở cuối; chưa biết giảng viên có bắt buộc áp dụng cho BTL này hay không |
