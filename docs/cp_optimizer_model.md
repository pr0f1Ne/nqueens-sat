# Backend IBM CP Optimizer

Backend dùng `docplex.cp` với N biến nguyên `q[r]` trong `0..N-1` và ba ràng
buộc `all_diff(q)`, `all_diff(q[r]+r)`, `all_diff(q[r]-r)`. Không có objective
hoặc symmetry breaking. Nghiệm được chuyển thành `(r,q[r])` và kiểm tra bằng
validator chung.

DOcplex cần runtime `cpoptimizer.exe`; dự án trỏ tường minh tới executable
trong `.venv/Scripts`. Môi trường đã giải thật N=1,2,3,4,8 và lượt chính thức
N=8,16,32,64. Benchmark dùng một worker, seed 0 và deadline ngoài worker;
`load_time=null` vì API không tách giai đoạn load phù hợp.

Tài liệu chính thức: [IBM - cài CPLEX/CP Optimizer API bằng pip hoặc conda](https://www.ibm.com/docs/en/icos/22.1.2?topic=rnco2-cplex-python-api-now-installed-using-pip-conda).
