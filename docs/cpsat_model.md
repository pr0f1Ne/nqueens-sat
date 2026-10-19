# Mô hình N-Queens bằng OR-Tools CP-SAT

## 1. Biến và ràng buộc

Với mỗi hàng `r` từ 0 đến N−1, tạo một biến nguyên:

```text
q[r] ∈ {0, ..., N−1}
```

`q[r]` là cột chứa hậu của hàng `r`. Mỗi hàng mặc nhiên có đúng một hậu vì
mỗi hàng có đúng một biến nhận đúng một giá trị. Mô hình gồm:

```text
AllDifferent(q[r])
AllDifferent(q[r] + r)
AllDifferent(q[r] - r)
```

Ràng buộc thứ nhất cấm hai hậu cùng cột. Hai ràng buộc sau cấm trùng hai họ
đường chéo. Không có hàm mục tiêu, symmetry breaking hoặc callback liệt kê;
backend chỉ tìm một nghiệm.

## 2. So với mô hình Boolean SAT

SAT dùng N² biến Boolean `x[r,c]`, sau đó mã hóa EO hàng/cột và AMO đường
chéo thành CNF. CP-SAT dùng N biến nguyên `q[r]` và ba ràng buộc toàn cục
AllDifferent. Vì vậy đây là so sánh **cả mô hình biểu diễn lẫn backend**, không
phải thí nghiệm cô lập thuật toán lõi hoặc chỉ thay solver trên cùng CNF.

`encoding` AMO chỉ có nghĩa cho phương pháp SAT. Record CP-SAT đặt trường này
là `null`; `num_clauses`, `num_board_variables` và `num_auxiliary_variables`
cũng là `null`. `num_variables=N` là số biến quyết định nguyên CP-SAT.

## 3. Trạng thái và nghiệm

Backend status gốc được giữ bằng `CpSolver.status_name`:

- `OPTIMAL` hoặc `FEASIBLE`: có nghiệm; chuyển sang SAT chỉ khi validator đạt.
- `INFEASIBLE`: UNSAT.
- `MODEL_INVALID`: ERROR.
- `UNKNOWN`: UNKNOWN.
- Deadline worker cha bị vượt: TIMEOUT với backend status `OUTER_TIMEOUT`.
- Không import được OR-Tools: UNAVAILABLE.

Nghiệm được đổi thành `[(r, q[r]), ...]` rồi đưa qua cùng validator độc lập
với SAT.

## 4. Cấu hình và thời gian

Benchmark đặt tường minh `num_workers=1` và mặc định `random_seed=0`; cả hai
được ghi vào từng record. Không đặt giới hạn thời gian nội bộ CP-SAT. Giới hạn
duy nhất là deadline ngoài worker hiện có, bao phủ import, dựng mô hình, tạo
solver, solve, chuyển nghiệm và validator.

`build_time` đo dựng biến/ràng buộc. `solve_time` đo lời gọi `CpSolver.solve`.
`total_time` đo toàn tác vụ trong worker và `parent_observed_time` đo phía cha.
Native API đang dùng không có giai đoạn load tách riêng phù hợp, vì vậy
`load_time=null`; không giả lập bằng 0.

## 5. Giới hạn diễn giải

CP-SAT dùng biến nguyên/ràng buộc toàn cục còn SAT dùng Boolean/CNF. Chênh
lệch thời gian có thể đến từ biểu diễn, presolve, propagation, heuristic,
runtime và overhead import. Smoke benchmark nhỏ chỉ kiểm tra pipeline, không
đủ để kết luận phương pháp nào tốt hơn.
