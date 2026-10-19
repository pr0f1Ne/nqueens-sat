# Backend Gurobi MIP

Backend dùng `gurobipy==13.0.3` với biến nhị phân `x[r,c]`, tổng mỗi hàng và
cột bằng 1, tổng mỗi đường chéo không vượt quá 1. Không có objective hoặc
symmetry breaking. `SolutionLimit=1`, `Threads=1` và seed được ghi trong kết
quả. Giá trị nghiệm được kiểm tra theo `IntFeasTol` trước khi giải mã.

Môi trường ngày 18-10-2026 có restricted non-production license, hết hạn
29-11-2027. Runtime đã giải thật N=1,2,3,4,8. Pilot và lượt chính thức chạy
N=8,16,32,64; N=64 trả UNAVAILABLE vì model quá lớn cho size-limited license.
Import package không được dùng thay cho kiểm tra thực thi.

Tài liệu: [Gurobi Python API](https://docs.gurobi.com/projects/optimizer/en/current/reference/python.html)
và [gurobipy trên PyPI](https://pypi.org/project/gurobipy/).
