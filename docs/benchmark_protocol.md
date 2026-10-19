# Giao thức benchmark N-Queens

## 1. Phạm vi và mục tiêu

Benchmark hỗ trợ ba encoding SAT với Glucose3, CP-SAT, IBM CP Optimizer,
CPLEX MIP và Gurobi MIP. Tất cả cùng nhiệm vụ tìm một nghiệm. Các case chạy **tuần tự**
để hạn chế tranh chấp tài nguyên; mỗi case khởi tạo solver mới.

Một lần lặp lại cùng N và encoding là một **phép đo lặp của cùng instance**,
không phải một instance N-Queens độc lập. N-Queens với một N cố định vẫn là
cùng bài toán, dù solver có thể trả một nghiệm hợp lệ khác.

## 2. Cấu hình và thứ tự

Ví dụ smoke benchmark:

```powershell
.\.venv\Scripts\python.exe benchmark.py --n 4 8 16 --methods sat cpsat --encodings pairwise sequential bitwise --repeats 2 --timeout 10 --output results --seed 20261017 --shuffle --cpsat-seed 0
```

`--seed` chỉ đưa vào `random.Random(seed)` để tái tạo thứ tự case khi có
`--shuffle`. Nó không phải seed của solver. API Glucose3 đang dùng không
đặt solver seed và không cấu hình số worker; metadata SAT ghi hai thuộc tính
này là `null`. CP-SAT đặt seed theo `--cpsat-seed` và luôn dùng một worker
trong benchmark so sánh ban đầu. Encoding của CP-SAT là `null`.
CPLEX dùng `--cplex-seed`, một thread và `mip.limits.solutions=1`; encoding
của CPLEX MIP là `null`.

Không dùng `--shuffle` thì thứ tự là N, encoding, repeat theo đúng danh sách
đầu vào và `benchmark_order_seed` trong từng record là `null`.

## 3. Ranh giới thời gian và timeout

Mỗi case dùng cùng cơ chế timeout worker ngoài. Đồng hồ cha bắt
đầu ngay trước khi spawn worker và dừng sau khi nhận kết quả, thu hồi worker.
Do đó timeout bao phủ build CNF, load Glucose3, solve, decode, validator và
overhead worker. Đây là timeout thực thi: worker quá hạn bị dừng. CP-SAT
không đặt giới hạn nội bộ, nên không có hai deadline cạnh tranh.
CPLEX cũng chỉ dùng deadline worker ngoài; giới hạn Community Edition được
ghi UNAVAILABLE, không phải UNSAT.

- `build_time`: tạo CNF trong worker.
- `load_time`: khởi tạo solver và nạp CNF.
- `solve_time`: riêng lời gọi `solver.solve()`.
- `total_time`: toàn tác vụ bên trong worker.
- `parent_observed_time`: thời gian tiến trình cha quan sát, gồm spawn và IPC.

Khi TIMEOUT xảy ra, các thời gian con chưa nhận được là `null`; không thay
bằng 0 hoặc timeout. TIMEOUT không phải UNSAT và không phải lần giải thành
công. Benchmark tiếp tục case sau TIMEOUT hoặc ERROR.

## 4. Cấu trúc dữ liệu

Mỗi lần gọi tạo `results/<run_id>/` mới, không ghi đè run cũ:

- `config.json`: cấu hình, số case dự kiến, phạm vi timeout và seed.
- `environment.json`: OS, CPU, RAM nếu lấy được, Python, python-sat, Glucose3,
  Git và hash SHA-256 nguồn.
- `raw_results.jsonl`: bản ghi đầy đủ, append và flush sau từng case.
- `results.csv`: cùng dữ liệu dạng bảng, append và flush sau từng case.
- `solutions.jsonl`: nghiệm tách riêng và liên kết bằng `solution_id`.

Nếu có Git, metadata ghi commit và trạng thái dirty. Nếu không có Git, hai
trường là `null`; SHA-256 các tệp nguồn liên quan xác định mã đã chạy. Công
cụ không đọc hoặc lưu biến môi trường, credential hay dữ liệu người dùng.

Nếu backend trả UNAVAILABLE, benchmark ghi case đó rồi không thử nạp backend
lặp lại; các case còn lại vẫn có record UNAVAILABLE với lý do. Một exception
riêng lẻ trở thành ERROR và không dừng phiên.

## 5. Tái lập và kiểm tra

Để chạy lại, dùng các giá trị trong `config.json`, cùng môi trường/dependency
trong `environment.json`. Nếu `shuffle=true`, giữ nguyên seed để tái tạo thứ
tự. Đối chiếu `expected_case_count` với số dòng JSONL/CSV. Với SAT, yêu cầu
`validated=true`, tra `solution_id` trong `solutions.jsonl` và có thể gọi lại
validator độc lập.

Smoke benchmark chỉ xác nhận pipeline và tạo dữ liệu nhỏ. Không dùng nó để
kết luận encoding nào tốt hơn: số mẫu ít, instance không độc lập và thời
gian ngắn chịu ảnh hưởng overhead/nhiễu hệ thống.
