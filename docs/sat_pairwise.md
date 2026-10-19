# Mô hình SAT pairwise cho N-Queens

## 1. Biến và ràng buộc

Đánh số hàng, cột từ 0 đến N−1. Biến Boolean `x[r,c]` đúng khi có hậu ở
ô `(r,c)`; ID DIMACS là `r*N+c+1`, nên các biến bàn cờ là `1..N²`.

Với tập biến `S`:

- ALO (ít nhất một): một clause `∨(x với x thuộc S)`.
- AMO pairwise (nhiều nhất một): với mọi cặp `a,b` khác nhau, thêm
  `(¬a ∨ ¬b)`. Nhóm k biến sinh `k(k−1)/2` clause.
- EO (chính xác một): ALO kết hợp AMO.

Mỗi hàng và mỗi cột dùng EO. Mỗi đường chéo có chung `r-c` hoặc `r+c`
chỉ dùng AMO; đường chéo không cần có hậu nên không có ALO. Pairwise không
dùng biến phụ, vì vậy mô hình có đúng N² biến.

Ví dụ N=2, EO của hàng 0 sinh `(x00 ∨ x01)` và
`(¬x00 ∨ ¬x01)`. Clause đường chéo chính là `(¬x00 ∨ ¬x11)`.

## 2. Vì sao mô hình đúng

Chiều thuận: mọi cách đặt N hậu hợp lệ có đúng một hậu mỗi hàng/cột nên
thỏa EO; không có hai hậu chung đường chéo nên thỏa mọi clause AMO.

Chiều ngược: EO hàng buộc đúng N hậu (mỗi hàng một hậu). EO cột loại khả
năng trùng cột. Hai họ AMO đường chéo loại mọi cặp có cùng `r-c` hoặc
`r+c`. Do đó phép gán thỏa CNF tương ứng một nghiệm N-Queens hợp lệ.

## 3. Ý nghĩa từng hàm

- `validate_n`: chặn N không phải số nguyên dương ngay tại biên API.
- `board_var`: ánh xạ hai chiều về mặt ý tưởng giữa ô và ID SAT.
- `add_at_least_one`: sinh clause ALO duy nhất của một nhóm.
- `add_pairwise_at_most_one`: duyệt mọi cặp bằng `combinations` và sinh AMO.
- `add_exactly_one`: ghép ALO và AMO, dùng cho hàng/cột.
- `encode_n_queens_pairwise`: gom nhóm hàng, cột và hai họ đường chéo để
  tạo toàn bộ CNF.
- `decode_model`: bỏ literal âm và mọi ID ngoài `1..N²`, rồi trả tọa độ hậu.
- `solve_n_queens`: đo từng giai đoạn, nạp CNF vào Glucose3, tìm một nghiệm,
  giải mã và gọi validator độc lập; khi có timeout thì điều phối worker.
- `run_in_worker`: chạy toàn tác vụ bằng chế độ `spawn`, áp deadline ở tiến
  trình cha và thu hồi worker bằng `terminate`/`kill` cùng các lần `join` hữu
  hạn. Thiết kế này hoạt động trên Windows và có thể dùng lại cho backend sau.
- `validate_solution`: kiểm tra luật bàn cờ trực tiếp bằng số lượng phần tử
  khác nhau của hàng, cột, `r-c`, `r+c`; không đọc lại CNF.
- `parse_args`/`main`: nhận N, in cấu trúc kết quả JSON và đặt exit code.

## 4. Kích thước để trình bày trong báo cáo

Mỗi nhóm EO kích thước N có `1 + N(N−1)/2` clause. Có N hàng và N cột.
Phần đường chéo cộng số cặp ô trên từng đường chéo ở cả hai hướng. Có thể
báo trực tiếp `num_variables` và `num_clauses` từ kết quả chương trình;
không được so số clause này như thể là số constraint của CP/MIP.

Các luận điểm quan trọng cần hiểu: ý nghĩa biến; khác biệt ALO/AMO/EO;
lý do đường chéo chỉ cần AMO; chứng minh đúng hai chiều; quy tắc giải mã chỉ
lấy biến bàn cờ dương; và vai trò của validator độc lập trong việc phát hiện
lỗi mã hóa hoặc giải mã.

## 5. Timeout và các ranh giới thời gian

Khi không truyền `--timeout`, lời giải chạy trực tiếp như trước. Khi có
timeout, tiến trình cha dùng đồng hồ đơn điệu từ ngay trước thao tác spawn.
Deadline vì thế bao phủ cả khởi động worker và toàn tác vụ dựng/nạp/giải.
Đây là giới hạn thực thi: worker quá hạn bị dừng và thu hồi, khác với việc chỉ
phát hiện rằng solver đã chạy quá lâu sau khi nó kết thúc.

`build_time`, `load_time`, `solve_time` và `total_time` do tác vụ bên trong
worker đo. `parent_observed_time` do tiến trình cha đo và còn gồm chi phí
spawn, truyền kết quả và thu hồi. Nếu timeout xảy ra giữa chừng, tiến trình
cha không có số đo giai đoạn đáng tin cậy nên các trường đó là `null`.
