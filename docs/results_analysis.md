# Phân tích thực nghiệm N-Queens

## 1. Thiết kế và dữ liệu

Thực nghiệm ngày 17-10-2026 gồm hai nhóm độc lập:

- Nhóm A: pairwise, sequential và bitwise trên cùng Glucose3.
- Nhóm B: ba cấu hình SAT trên cùng, OR-Tools CP-SAT và IBM CPLEX MIP.

Pilot dùng N=8,16,32,64, một phép đo mỗi cấu hình, timeout 10 giây. Lượt
chính thức giữ dãy N này, dùng 5 phép đo lặp và timeout ngoài 60 giây, chạy
tuần tự. Không thử N=128/256 vì pilot đã có TIMEOUT tại N=32/64 và pairwise
tăng đến 428.864 clause ở N=64; mở rộng tiếp tạo rủi ro thời gian/bộ nhớ.

Dữ liệu chính thức:

- Nhóm A: `results/official_group_a/nqueens-20261017T111907.520045Z-6b77c4fa/`
- Nhóm B: `results/official_group_b/nqueens-20261017T112229.797169Z-5155e565/`
- Tổng hợp/biểu đồ: `results/analysis_20261017/`

Mỗi N là một instance chuẩn duy nhất; 5 lần là phép đo lặp cùng instance,
không phải 5 instance độc lập. Trung vị và IQR chỉ tính trên lần SAT hợp lệ.
TIMEOUT/ERROR/UNAVAILABLE không được thay bằng timeout hay đưa vào thống kê
thời gian thành công.

## 2. Tính đúng và trạng thái

Nhóm A hoàn thành 60/60 case, tất cả SAT và `validated=true`. Nhóm B hoàn
thành 100/100 case: 90 SAT hợp lệ và 10 UNAVAILABLE. Mười UNAVAILABLE là
CPLEX tại N=32,64 do Community Edition giới hạn 1.000 biến; mô hình có N²
biến nên vượt giới hạn từ N=32. Không có UNSAT, TIMEOUT, UNKNOWN hoặc ERROR
trong lượt chính thức. Do đó không có lần timeout nào bị loại khỏi trung vị
chính thức.

Pilot A có 10 SAT và 2 TIMEOUT; pilot B hoàn chỉnh có 16 SAT, 2 TIMEOUT và
2 UNAVAILABLE. Một pilot B trước đó bị tiến trình điều phối bên ngoài dừng ở
8/20 case; run dở dang được giữ lại và được thay bằng một run pilot mới đủ
20/20, không được dùng trong phân tích chính thức.

Gurobi và CP Optimizer không tham gia: môi trường không có `gurobipy` hoặc
DOcplex/CP Optimizer runtime và dự án chưa có backend tương ứng. Không dùng
mock làm số liệu thực nghiệm.

## 3. Câu hỏi A — encoding nào phù hợp hơn với Glucose3 trong dữ liệu này?

Trung vị thời gian cha quan sát (giây), IQR trong ngoặc:

| N | Pairwise | Sequential | Bitwise |
|---:|---:|---:|---:|
| 8 | 0,294 (0,023) | 0,282 (0,015) | 0,293 (0,010) |
| 16 | 0,305 (0,002) | 0,312 (0,018) | 0,394 (0,005) |
| 32 | 0,320 (0,006) | 0,804 (0,009) | 17,730 (0,046) |
| 64 | 0,582 (0,006) | 11,219 (0,018) | 7,264 (0,016) |

Trong đúng dãy N và máy này, pairwise ổn định nhất từ N=16 đến 64 dù có
nhiều clause nhất. Sequential có ít clause nhất nhưng solve tăng mạnh ở N=64.
Bitwise tăng đột biến tại N=32 rồi giảm ở N=64; đây là kết quả đã quan sát,
không được nội suy thành quan hệ đơn điệu. Ít clause không bảo đảm nhanh hơn
vì cấu trúc clause, propagation và heuristic quan trọng hơn số lượng đơn thuần.

Kích thước tại N=64:

| Encoding | Biến bàn cờ | Biến phụ | Tổng biến | Clause |
|---|---:|---:|---:|---:|
| pairwise | 4.096 | 0 | 4.096 | 428.864 |
| sequential | 4.096 | 15.998 | 20.094 | 47.752 |
| bitwise | 4.096 | 2.036 | 6.132 | 95.572 |

Kết quả cho thấy giảm kích thước CNF là một đánh đổi chứ không phải tiêu chí
đủ để dự đoán thời gian tìm nghiệm.

## 4. Câu hỏi B — các mô hình/backend khác nhau thể hiện thế nào?

Trung vị thời gian cha quan sát của nhóm B:

| Cấu hình | N=8 | N=16 | N=32 | N=64 |
|---|---:|---:|---:|---:|
| SAT pairwise | 0,286 | 0,308 | 0,317 | 0,630 |
| SAT sequential | 0,284 | 0,285 | 0,791 | 11,339 |
| SAT bitwise | 0,285 | 0,408 | 17,777 | 7,355 |
| CP-SAT | 1,077 | 1,116 | 1,190 | 1,436 |
| CPLEX MIP | 0,478 | 0,466 | UNAVAILABLE | UNAVAILABLE |

Pairwise thấp nhất trong các cấu hình khả dụng ở N=32/64 trong lần chạy này;
ở N nhỏ, khác biệt bị chi phối đáng kể bởi overhead tiến trình/import. CP-SAT
tăng tương đối đều và thấp hơn sequential/bitwise tại N=64, nhưng cao hơn
pairwise. CPLEX chỉ có dữ liệu N=8,16 nên không thể suy luận cho N lớn.

Đây không phải so sánh cô lập thuật toán lõi. SAT dùng N² biến Boolean và
CNF; CP-SAT dùng N biến nguyên cùng AllDifferent; CPLEX dùng N² biến nhị phân
và ràng buộc tuyến tính. Backend, presolve, propagation và mô hình đều đổi.

## 5. Chi phí khởi động và các pha thời gian

`parent_observed_time` là thước đo tổng phù hợp nhất vì gồm spawn/import/IPC.
Ví dụ N=8 nhóm B: solve median của CP-SAT chỉ khoảng 0,008 giây nhưng thời
gian cha quan sát là 1,077 giây; CPLEX solve khoảng 0,002 giây nhưng tổng quan
sát là 0,478 giây. Với bài nhỏ, overhead khởi động lớn hơn thời gian giải.

SAT pairwise N=64 có build khoảng 0,104 giây, load 0,166 giây và solve 0,017
giây ở nhóm B: dựng/nạp CNF đáng kể hơn solve. Ngược lại sequential và bitwise
N lớn bị chi phối bởi solve. CP-SAT/CPLEX không có `load_time` tách riêng;
trường null không được diễn giải thành 0.

## 6. Giới hạn và phạm vi kết luận

- Chỉ có bốn N và một instance chuẩn cho mỗi N; lặp lại không tạo đa dạng
  instance.
- Chỉ tìm một nghiệm, nên kết quả không đại diện cho đếm/liệt kê nghiệm hoặc
  chứng minh tối ưu của bài toán khác.
- Kết quả gắn với Windows, Python 3.14.6, phần cứng và phiên bản solver đã ghi
  trong `environment.json`.
- Glucose3 không kiểm soát seed/worker qua API hiện tại; CP-SAT và CPLEX dùng
  một luồng, seed 0.
- CPLEX Community Edition thiếu khả năng chạy N≥32; Gurobi và CP Optimizer
  chưa có dependency/runtime/license/backend.
- N=128/256 chưa chạy, không có số liệu để nội suy.

Vì vậy không có cơ sở kết luận một phương pháp luôn tốt nhất. Kết luận hẹp là:
trên bốn kích thước, nhiệm vụ tìm một nghiệm và môi trường này, pairwise với
Glucose3 cho tổng thời gian thấp và ổn định nhất ở N lớn đã thử; CP-SAT có
đường tăng đều hơn sequential/bitwise; CPLEX chỉ được xác nhận ở N nhỏ.

## 7. Tái tạo

Tạo lại bảng và biểu đồ từ hai run chính thức:

```powershell
.\.venv\Scripts\python.exe analyze_results.py `
  --group-a results\official_group_a\nqueens-20261017T111907.520045Z-6b77c4fa `
  --group-b results\official_group_b\nqueens-20261017T112229.797169Z-5155e565 `
  --output results\analysis_reproduced
```

Script sinh `summary.csv`, `time_by_n.png`, `sat_model_size.png` và
`phase_times.png`. Mỗi biểu đồ ghi đơn vị, chú giải và run ID nguồn.

## 8. Bổ sung Gurobi và CP Optimizer ngày 18-10-2026

Run chính thức bổ sung tại
`results/official_commercial_completion/nqueens-20261017T171516.947782Z-8889a38f/`
dùng N=8,16,32,64, 5 phép đo lặp, timeout 60 giây và một luồng/worker. Có
35 SAT validated và 5 UNAVAILABLE. CP Optimizer hoàn thành 20/20 SAT;
Gurobi hoàn thành 15 SAT ở N=8,16,32 và 5 UNAVAILABLE ở N=64 do
size-limited license. Không có TIMEOUT, ERROR hoặc UNKNOWN.

Trung vị thời gian cha quan sát của Gurobi là 0,387; 0,380 và 0,411 giây
tại N=8,16,32. CP Optimizer lần lượt là 1,461; 1,486; 1,475 và 1,495 giây
tại N=8,16,32,64. Các số này được tổng hợp cùng dữ liệu cũ trong
`results/analysis_20261018_report/summary.csv`; biểu đồ mới cũng được sinh bởi
`analyze_results.py`. Giới hạn license khiến dữ liệu MIP vẫn không đầy đủ ở
N=64, nên không suy luận Gurobi cho kích thước đó.

Lệnh tái tạo mới thêm tùy chọn `--group-c` trỏ tới run bổ sung và dùng thư
mục đầu ra mới, ví dụ `results/analysis_reproduced`.
