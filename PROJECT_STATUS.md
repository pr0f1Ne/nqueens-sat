# TRẠNG THÁI DỰ ÁN N-QUEENS SAT

Tài liệu phản ánh trạng thái sau mốc thực nghiệm chính thức và phân tích kết quả.

## 1. Phạm vi đã hoàn thành

- Tìm một nghiệm N-Queens bằng SAT và Glucose3.
- Ba encoding AMO: `pairwise` (mặc định), `sequential`, `bitwise`.
- Cùng một mô hình: EO hàng/cột, AMO hai họ đường chéo.
- ALO là clause trực tiếp; sequential/bitwise chỉ mã hóa AMO bằng
  `CardEnc.atmost(..., bound=1)`.
- Một `IDPool` chung bảo vệ miền `1..N²` cho biến bàn cờ.
- Decoder chỉ đọc biến bàn cờ; validator độc lập kiểm tra nghiệm.
- CLI chọn encoding và timeout worker thực sự.
- Kiểm thử truth table AMO/EO bằng assumptions và các ca N bắt buộc.
- Benchmark SAT tuần tự, lưu tăng dần theo run ID và tái sử dụng SolveResult.
- Backend OR-Tools CP-SAT với mô hình N biến nguyên và ba AllDifferent.
- CLI/benchmark chọn rõ SAT hoặc CP-SAT; encoding chỉ có hiệu lực với SAT.
- Backend IBM CPLEX MIP Community Edition và tích hợp benchmark.
- Script tổng hợp CSV và ba biểu đồ matplotlib từ dữ liệu JSONL thật.

Chưa triển khai Gurobi hoặc CP Optimizer.

## 2. Môi trường/API đã xác nhận

- Windows, Python 3.14.6.
- `python-sat==1.9.dev16`.
- `CardEnc.atmost(lits, bound=1, top_id=None, vpool=None, encoding=1)`.
- `EncType.seqcounter == 1`, `EncType.bitwise == 4`.
- `IDPool(start_from=1, occupied=[], with_neg=False)`.
- `ortools==9.15.6755`, wheel CPython 3.14 Windows amd64 đã cài và chạy thật.
- `cplex==22.2.0.1` Community Edition đã chạy thật; giới hạn 1.000 biến/ràng buộc.
- `matplotlib==3.11.2` dùng để tái tạo biểu đồ.

Python giữ nguyên 3.14.6; `python-sat==1.9.dev16` vẫn hoạt động sau khi cài.

## 3. API và cấu trúc chính

- `encode_n_queens(n, encoding="pairwise")`: điểm dựng mô hình chung.
- `add_at_most_one(...)`: điểm chọn encoding duy nhất.
- `add_exactly_one(...)`: ALO trực tiếp cộng AMO đã chọn.
- `encode_n_queens_pairwise(n)`: wrapper tương thích API cũ.
- `solve_n_queens(n, timeout=None, encoding="pairwise")`: giải trực tiếp
  hoặc trong worker có deadline.
- `decode_model`: bỏ literal âm và ID ngoài `1..N²`.
- `solve_n_queens_cpsat`: mô hình q[r], timeout worker ngoài, seed và 1 worker.
- `solve_n_queens_cplex_mip`: MIP N² biến nhị phân, một thread, solution limit 1.

`CNFFormula` và `SolveResult` ghi riêng `num_board_variables`,
`num_auxiliary_variables`, `num_variables` và `num_clauses`. Tổng biến là số
biến bàn cờ cộng số ID phụ đã cấp, không được định nghĩa bằng max literal.

## 4. Kích thước mô hình đã quan sát

Các số dưới đây được sinh trực tiếp bằng mã hiện tại; đây là kích thước CNF,
không phải benchmark thời gian.

| N | Encoding | Biến bàn cờ | Biến phụ | Tổng biến | Clause |
|---:|---|---:|---:|---:|---:|
| 1 | pairwise/sequential/bitwise | 1 | 0 | 1 | 2 |
| 2 | pairwise/sequential/bitwise | 4 | 0 | 4 | 10 |
| 3 | pairwise | 9 | 0 | 9 | 34 |
| 3 | sequential | 9 | 16 | 25 | 50 |
| 3 | bitwise | 9 | 16 | 25 | 58 |
| 4 | pairwise | 16 | 0 | 16 | 84 |
| 4 | sequential | 16 | 38 | 54 | 112 |
| 4 | bitwise | 16 | 28 | 44 | 116 |
| 8 | pairwise | 64 | 0 | 64 | 744 |
| 8 | sequential | 64 | 206 | 270 | 600 |
| 8 | bitwise | 64 | 106 | 170 | 724 |

Baseline pairwise N=1,2,3,4,8 vẫn lần lượt có 2, 10, 34, 84, 744 clause.

## 5. Kiểm thử

Lệnh:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Bộ test gồm:

- N=1,2,3,4,8 cho cả ba encoding; SAT phải qua validator.
- Vét cạn assignments biến gốc của AMO/EO nhỏ bằng assumptions.
- Nhiều nhóm dùng chung pool có các dải ID phụ rời nhau.
- AMO rỗng/một biến và chính sách từ chối ALO/EO rỗng.
- Baseline pairwise N=4 vẫn 16 biến, 84 clause.
- Decoder, validator, backend thiếu, worker thành công/lỗi/timeout.

Lần chạy trước thực nghiệm: 41 test, tất cả đạt. Ngoài test SAT cũ,
test bao phủ N=1,2,3,4,8 CP-SAT, validator, thiếu dependency, ánh xạ status,
timeout ngoài và schema benchmark có `encoding=null` cho CP-SAT.

## 6. Cách chạy

```powershell
.\.venv\Scripts\python.exe main.py 8 --encoding pairwise
.\.venv\Scripts\python.exe main.py 8 --encoding sequential
.\.venv\Scripts\python.exe main.py 8 --encoding bitwise
.\.venv\Scripts\python.exe main.py 8 --method cpsat --timeout 10 --solver-seed 0
```

Thêm `--timeout 5` nếu cần giới hạn toàn tác vụ.

## 7. Nội dung cho báo cáo và giới hạn

Phương pháp giữ nguyên biến/mô hình toán học, chỉ thay encoding AMO. Pairwise
cấm trực tiếp từng cặp; sequential truyền trạng thái đã-gặp-biến-đúng qua
chuỗi phụ; bitwise buộc biến đúng chọn một mã nhị phân duy nhất. IDPool chung
ngăn biến phụ trùng biến bàn cờ hoặc nhóm khác. Kiểm thử assumptions chứng
minh theo ngữ nghĩa tồn tại phần gán phụ.

Ít clause hơn chưa đảm bảo nhanh hơn vì còn số biến phụ, cấu trúc clause,
unit propagation, heuristic và môi trường chạy. Mốc này không có dữ liệu để
kết luận encoding nào nhanh nhất.

Benchmark tạo `config.json`, `environment.json`, `raw_results.jsonl`,
`results.csv` và `solutions.jsonl`. Mỗi case gọi đúng `solve_n_queens` với
timeout worker hiện có, chạy tuần tự và khởi tạo solver mới. Repeat cùng N là
phép đo lặp của cùng instance, không phải instance độc lập. Seed benchmark
chỉ điều khiển thứ tự shuffle; API hiện tại không điều khiển solver seed hoặc
số worker.

Chưa có: CP Optimizer, Gurobi,
repository/commit ID và báo cáo Elsevier cas-sc hoàn chỉnh. Smoke benchmark
không đủ để kết luận encoding nào tốt hơn.

So sánh SAT và CP-SAT thay đổi đồng thời biểu diễn mô hình lẫn backend: SAT
dùng N² biến Boolean/CNF, CP-SAT dùng N biến nguyên và AllDifferent. Vì vậy
không được mô tả đây là phép cô lập riêng thuật toán lõi.

## 8. Smoke benchmark đã chạy

Cấu hình thực tế: N = 4, 8, 16; ba encoding; 2 repeat; timeout 10 giây mỗi
case; chạy tuần tự; shuffle bằng benchmark seed 20261017. Tổng 18/18 case
được ghi, tất cả là SAT và `validated=true`; 18 nghiệm được kiểm tra lại bằng
validator độc lập. Không có TIMEOUT, ERROR, UNKNOWN hoặc UNAVAILABLE.

Dữ liệu nằm tại:

```text
results/sat-20261017T060035.667862Z-f9fa9109/
```

Môi trường ghi nhận Windows 11, Python 3.14.6, python-sat 1.9.dev16,
Glucose3, 12 logical CPU và 17109934080 byte RAM. Thư mục không có Git nên
commit/dirty là null; environment lưu SHA-256 của nguồn đã chạy.

## 9. Smoke SAT + CP-SAT đã chạy

Cấu hình: N=4,8,16; SAT pairwise/sequential/bitwise và CP-SAT; 2 repeat;
timeout ngoài 10 giây; tuần tự; shuffle seed 20261017; CP-SAT seed 0 và một
worker. Có 24/24 record SAT, tất cả `validated=true`, không có timeout/lỗi.
Trong đó 18 case SAT và 6 case CP-SAT. CP-SAT có `encoding`, `num_clauses`
và `load_time` bằng null đúng schema.

```text
results/nqueens-20261017T063518.106777Z-7f5d3393/
```

Đây chỉ là smoke benchmark để xác nhận pipeline, không phải bằng chứng phương
pháp nào tốt hơn.

## 10. Thực nghiệm chính thức 17-10-2026

Pilot dùng N=8,16,32,64, một lần/cấu hình, timeout 10 giây. Nhóm A pilot có
12/12 record (10 SAT, 2 TIMEOUT). Nhóm B pilot hoàn chỉnh có 20/20 record
(16 SAT, 2 TIMEOUT, 2 UNAVAILABLE). Một run pilot B trước đó bị dừng ở 8/20
do giới hạn phiên điều phối; dữ liệu được giữ, không dùng để tổng hợp.

Lượt chính thức dùng N=8,16,32,64, 5 phép đo lặp/cấu hình, timeout 60 giây,
tuần tự. Không chạy N=128/256 do pilot đã timeout và nguy cơ tăng bộ nhớ CNF.

- Nhóm A: 60/60 case hoàn thành, tất cả SAT và validated.
- Nhóm B: 100/100 case hoàn thành; 90 SAT validated, 10 UNAVAILABLE.
- 10 UNAVAILABLE là CPLEX N=32/64 do giới hạn Community Edition.
- Không có case chính thức chưa chạy; không có TIMEOUT/ERROR/UNKNOWN chính thức.
- Gurobi và CP Optimizer không chạy vì thiếu package/runtime/backend.

Dữ liệu:

```text
results/official_group_a/nqueens-20261017T111907.520045Z-6b77c4fa/
results/official_group_b/nqueens-20261017T112229.797169Z-5155e565/
results/analysis_20261017/
```

Phân tích tại `docs/results_analysis.md`. Tổng hợp tại `summary.csv`; biểu đồ
thời gian, kích thước SAT và các pha build/load/solve đều có script tái tạo
`analyze_results.py`. Kết quả không được dùng để tuyên bố một phương pháp
luôn tốt nhất.

## 11. Báo cáo khoa học và đối chiếu yêu cầu

Đã soạn bản LaTeX theo `cas-sc` tại `report/main.tex`, checklist yêu cầu tại
`docs/requirement_checklist.md` và câu hỏi bảo vệ tại
`docs/defense_questions.md`. Báo cáo lấy bảng/hình từ dữ liệu chính thức và
ghi rõ TODO URL repository, backend còn thiếu (Gurobi/CP Optimizer), N=128/256
chưa chạy và giới hạn Community Edition của CPLEX.

Sau khi đối chiếu PDF mẫu của giảng viên, báo cáo dùng bố cục một cột của
`cas-sc`, Times New Roman 10 pt, giãn dòng gần đơn, đoạn văn thụt đầu dòng,
bảng tối giản và hình có nguồn dữ liệu. Nguồn đã biên dịch thành công bằng
compiler của trình soạn thảo LaTeX tích hợp. Tệp PDF mẫu chỉ là một bài báo
tham khảo, không kèm bộ nguồn/template chi tiết để kiểm tra các macro riêng.

## 12. Hoàn thiện Gurobi và CP Optimizer ngày 18-10-2026

Đã cài `gurobipy==13.0.3` và `docplex==2.32.264` tương thích Python 3.14.
Gurobi runtime dùng restricted non-production license hết hạn 29-11-2027;
CP Optimizer dùng `cpoptimizer.exe` đi kèm runtime IBM và được DOcplex trỏ
tường minh. Cả hai backend giải thật N=1,2,3,4,8 và qua validator.

Đã thêm `gurobi_mip_solver.py`, `cp_optimizer_solver.py`, tích hợp CLI,
benchmark, metadata, timeout worker và kiểm thử. Smoke chung có 42/42 SAT.
Pilot Gurobi/CP Optimizer có 7 SAT và 1 UNAVAILABLE. Lượt chính thức bổ sung:

```text
results/official_commercial_completion/
  nqueens-20261017T171516.947782Z-8889a38f/
```

Run có 40/40 bản ghi: 35 SAT validated và 5 UNAVAILABLE. Gurobi chạy đến
N=32 nhưng N=64 vượt size-limited license; CP Optimizer có 20/20 SAT. Một
run chính thức trước đó bị gián đoạn ở 37/40 được giữ lại và không dùng trong
bảng báo cáo. Toàn bộ 47 kiểm thử đạt, `pip check` không phát hiện lỗi.

Thông tin tác giả/đơn vị và URL repository công khai đã được điền. Phần còn lại là kiểm tra
trực quan bản PDF nộp cuối sau khi điền các thông tin này.
