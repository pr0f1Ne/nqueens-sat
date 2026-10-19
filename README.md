# N-Queens bằng SAT — ba encoding AMO

Dự án tìm **một nghiệm** N-Queens bằng SAT/Glucose3, OR-Tools CP-SAT,
IBM CP Optimizer, IBM CPLEX MIP hoặc Gurobi MIP. SAT hỗ trợ AMO `pairwise`,
`sequential`, `bitwise`.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Môi trường đã kiểm tra: Python 3.14.6, `python-sat==1.9.dev16` và
`ortools==9.15.6755`. Với phiên bản
này, dự án đã xác nhận `CardEnc.atmost` nhận `bound`, `vpool`, `encoding`;
`EncType.seqcounter` và `EncType.bitwise` lần lượt có giá trị 1 và 4.
CPLEX dùng `cplex==22.2.0.1`; đây là package/runtime proprietary Community
Edition với giới hạn 1.000 biến và 1.000 ràng buộc.
Gurobi dùng `gurobipy==13.0.3` với restricted non-production license trong
môi trường kiểm tra. CP Optimizer dùng `docplex==2.32.264` và runtime
`cpoptimizer.exe`. License/runtime thương mại cần được kiểm tra lại trên máy
khác; import thành công không đủ chứng minh backend chạy được.

## Chạy

`pairwise` là mặc định để giữ tương thích:

```powershell
.\.venv\Scripts\python.exe main.py 8
.\.venv\Scripts\python.exe main.py 8 --encoding pairwise
.\.venv\Scripts\python.exe main.py 8 --encoding sequential
.\.venv\Scripts\python.exe main.py 8 --encoding bitwise
.\.venv\Scripts\python.exe main.py 8 --method cpsat --timeout 10 --solver-seed 0
.\.venv\Scripts\python.exe main.py 8 --method cplex_mip --timeout 10 --solver-seed 0
.\.venv\Scripts\python.exe main.py 8 --method gurobi_mip --timeout 10 --solver-seed 0
.\.venv\Scripts\python.exe main.py 8 --method cp_optimizer --timeout 10 --solver-seed 0
```

Có thể giới hạn toàn tác vụ, gồm spawn worker, dựng CNF, nạp solver, giải,
giải mã và validator:

```powershell
.\.venv\Scripts\python.exe main.py 8 --encoding sequential --timeout 5
```

`--encoding` chỉ áp dụng cho SAT; CLI từ chối kết hợp nó với phương pháp khác.
CP-SAT chạy một worker, ghi seed, không đặt objective hoặc symmetry breaking.

Kết quả JSON phân biệt `SAT`, `UNSAT`, `TIMEOUT`, `UNKNOWN`, `ERROR` và
`UNAVAILABLE`. Exit code là 0 cho SAT/UNSAT, 1 cho các trạng thái chưa giải
được/lỗi backend và 2 cho lỗi đối số.

Các trường kích thước:

- `num_board_variables`: luôn là N², miền ID `1..N²`.
- `num_auxiliary_variables`: số ID biến phụ do `IDPool` chung đã cấp.
- `num_variables`: tổng hai số trên; không suy ra bằng max literal.
- `num_clauses`: số clause CNF thực tế.

Các trường thời gian là `build_time`, `load_time`, `solve_time`, `total_time`;
`parent_observed_time` có khi dùng timeout và bao gồm overhead worker. Giai
đoạn không quan sát được là `null`, không giả làm 0.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Test bao phủ N=1,2,3,4,8 cho cả ba encoding; mọi nghiệm SAT qua validator.
Các nhóm AMO/EO nhỏ được vét cạn bằng assumptions, nhờ đó solver được phép
tìm phần gán biến phụ tồn tại thay vì ép một mẫu biến phụ cụ thể. Test cũng
kiểm tra dùng chung IDPool, nhóm rỗng/một biến, decoder và timeout worker.

## Benchmark SAT

Smoke benchmark ba kích thước, ba encoding SAT và CP-SAT, hai phép đo lặp:

```powershell
.\.venv\Scripts\python.exe benchmark.py --n 4 8 16 --methods sat cpsat --encodings pairwise sequential bitwise --repeats 2 --timeout 10 --output results --seed 20261017 --shuffle --cpsat-seed 0
```

Mỗi phiên tạo thư mục `results/<run_id>/` riêng với cấu hình, môi trường,
JSONL thô, CSV và nghiệm. Dữ liệu được ghi ngay sau từng case; các case chạy
tuần tự và mỗi case tạo solver mới. Seed trên chỉ điều khiển thứ tự case khi
shuffle, không phải solver seed. Một lần lặp cùng N là phép đo lặp của cùng
instance, không phải một instance độc lập.

Giao thức, ranh giới thời gian và cách tái lập được mô tả tại
[`docs/benchmark_protocol.md`](docs/benchmark_protocol.md).
Mô hình CP-SAT được giải thích tại [`docs/cpsat_model.md`](docs/cpsat_model.md).
Mô hình, runtime và license CPLEX được giải thích tại
[`docs/cplex_mip_model.md`](docs/cplex_mip_model.md).
Gurobi và CP Optimizer được mô tả tại
[`docs/gurobi_mip_model.md`](docs/gurobi_mip_model.md) và
[`docs/cp_optimizer_model.md`](docs/cp_optimizer_model.md).

Xem mô hình và nội dung phương pháp tại
[`docs/sat_encodings.md`](docs/sat_encodings.md). Tài liệu pairwise ban đầu
được giữ tại [`docs/sat_pairwise.md`](docs/sat_pairwise.md).

## Giới hạn hiện tại

- Lượt chính thức SAT/CP-SAT/CPLEX và lượt bổ sung Gurobi/CP Optimizer dùng
  N=8,16,32,64, năm phép đo lặp.
- CPLEX không chạy được N=32/64; Gurobi không chạy được N=64 do license giới hạn.
- N=128/256 chưa chạy; mỗi N vẫn chỉ là một instance chuẩn.
- Mã nguồn và dữ liệu tái lập được công bố tại
  <https://github.com/pr0f1Ne/nqueens-sat>.
