# Backend IBM CPLEX MIP

## 1. Thành phần cài đặt và giấy phép

Backend dùng Python package thấp tầng `cplex`, không dùng DOcplex hoặc dịch
vụ cloud. IBM mô tả package này là giao diện Python của CPLEX Callable
Library; bản hiện tại có thể cài Community Edition runtime trực tiếp qua
PyPI. Môi trường đã kiểm tra thực tế:

```text
Python 3.14.6
cplex distribution 22.2.0.1
cplex runtime/API version 22.2.0.0
Windows x86-64
```

Tài liệu chính thức:

- [IBM: CPLEX Python API cài bằng pip/conda](https://www.ibm.com/docs/en/icos/22.1.2?topic=rnco2-cplex-python-api-now-installed-using-pip-conda)
- [IBM: lựa chọn license và giới hạn Community Edition](https://www.ibm.com/products/ilog-cplex-optimization-studio/pricing)
- [PyPI: package cplex](https://pypi.org/project/cplex/)

Community Edition miễn phí bị giới hạn 1.000 biến và 1.000 ràng buộc. Bản
không giới hạn cần license/subscription hoặc quyền Academic Initiative của
IBM. Dự án không mua license, đăng nhập tài khoản hoặc cấu hình cloud. Với
mô hình N² biến, giới hạn biến Community Edition đã chặn N ≥ 32; benchmark
lớn phải kiểm tra license trước, không được diễn giải lỗi giới hạn là UNSAT.

Import package chưa đủ chứng minh khả năng chạy. Mốc này đã tạo và solve một
MIP nhị phân tối thiểu, nhận status `101: integer optimal solution`, rồi chạy
thật N=1,2,3,4,8 và smoke benchmark.

## 2. Mô hình toán học

Tạo biến nhị phân `x[r,c]` cho mọi ô. Giá trị 1 nghĩa là có hậu tại hàng r,
cột c:

```text
Σ_c x[r,c] = 1                 với mọi hàng r
Σ_r x[r,c] = 1                 với mọi cột c
Σ_(r-c=d) x[r,c] ≤ 1           với mọi đường chéo d
Σ_(r+c=s) x[r,c] ≤ 1           với mọi đường chéo s
```

Không có symmetry breaking và không có mục tiêu tối ưu thực chất; hệ số mục
tiêu mặc định đều bằng 0. CPLEX được đặt `mip.limits.solutions=1` để yêu cầu
dừng sau nghiệm khả thi đầu tiên. Nếu đã có incumbent khi dừng, backend giữ
nghiệm, chạy validator và trả SAT cùng status CPLEX gốc.

## 3. Giải mã và trạng thái

Giá trị nhị phân CPLEX là số thực. Trước khi đổi thành tọa độ, code kiểm tra
mỗi giá trị cách 0 hoặc 1 không quá `mip.tolerances.integrality`; giá trị nằm
ngoài dung sai gây ERROR, không bị làm tròn mù quáng.

- Có incumbent và validator đạt: SAT.
- `MIP_infeasible`/`infeasible` không có incumbent: UNSAT.
- Trạng thái khác không có incumbent, kể cả infeasible-or-unbounded hoặc chạm
  giới hạn: UNKNOWN.
- Deadline worker ngoài: TIMEOUT.
- Thiếu package hay lỗi runtime/license nhận diện được: UNAVAILABLE.
- Exception lập trình/API khác: ERROR.

`backend_status` giữ cả mã và chuỗi CPLEX. `encoding=null` và
`num_clauses=null` vì đây không phải encoding CNF. Số biến là N².

## 4. Cấu hình và thời gian

Benchmark đặt một thread, seed tường minh và solution limit bằng 1. Không đặt
time limit nội bộ; deadline ngoài worker bao phủ import/runtime, build, solve,
decode và validator. `build_time` gồm tạo đối tượng CPLEX và mô hình;
`solve_time` là lời gọi `solve`; `load_time=null` vì không tách được hợp lý.

Hiện dự án chỉ triển khai CPLEX MIP trong nhóm solver thương mại.
