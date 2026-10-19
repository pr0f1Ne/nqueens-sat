# Câu hỏi bảo vệ và trả lời

## Vì sao hàng/cột dùng EO?

Mỗi hàng và mỗi cột của bàn cờ chuẩn phải có đúng một hậu. ALO bảo đảm có ít nhất một biến đúng; AMO bảo đảm không có hai biến cùng đúng. Kết hợp hai điều kiện là EO.

## Vì sao đường chéo chỉ dùng AMO?

Không phải đường chéo nào cũng phải chứa hậu. Chỉ cần cấm hai hậu cùng một đường chéo, nên thêm ALO sẽ làm sai mô hình và ép các đường chéo ngắn phải có hậu.

## Biến phụ có ý nghĩa gì?

Biến phụ biểu diễn trạng thái trung gian của encoding (ví dụ tiền tố của sequential counter hoặc bit mã hóa). Chúng không phải ô bàn cờ; một phép gán biến gốc đúng được chấp nhận khi tồn tại phần gán biến phụ mở rộng làm CNF thỏa mãn.

## Vì sao ít clause chưa chắc nhanh hơn?

Thời gian còn phụ thuộc số biến phụ, độ dài và cấu trúc clause, unit propagation, heuristic của solver, cache, overhead khởi động và phần cứng. Kết quả thực tế cho thấy sequential/bitwise ít clause hơn pairwise nhưng không luôn nhanh hơn.

## Vì sao timeout không phải UNSAT?

Timeout chỉ nói rằng giới hạn thời gian đã hết trước khi backend kết luận. UNSAT chỉ hợp lệ khi solver chứng minh vô nghiệm; benchmark giữ TIMEOUT/UNKNOWN riêng.

## Vì sao cần validator độc lập?

Validator kiểm tra luật N-Queens trực tiếp, không dùng lại CNF hay trạng thái nội bộ solver. Nó phát hiện lỗi giải mã, lỗi ánh xạ biến và nghiệm backend không hợp lệ.

## Vì sao so sánh SAT, CP và MIP chưa hoàn toàn cô lập?

SAT dùng $N^2$ biến Boolean/CNF, CP-SAT dùng $N$ biến nguyên với AllDifferent, còn CPLEX dùng $N^2$ biến nhị phân và ràng buộc tuyến tính. Do đó biểu diễn, presolve, propagation, heuristic và backend đều thay đổi cùng lúc; kết quả là so sánh hệ thống, không phải cô lập thuật toán lõi.

## Vì sao CPLEX thiếu một số kích thước?

Môi trường chỉ có Community Edition; mô hình có $N^2$ biến nên N=32 vượt giới hạn 1.000 biến. Các bản ghi được ghi UNAVAILABLE, không diễn giải thành UNSAT.

## Năm lần lặp có phải năm instance không?

Không. Mỗi N là cùng một instance N-Queens chuẩn; năm lần chỉ là phép đo lặp để quan sát dao động thời gian.

## Có thể kết luận pairwise luôn tốt nhất không?

Không. Dữ liệu chỉ gồm bốn N, một instance mỗi N, một máy và các backend khả dụng; kết luận hợp lệ chỉ là pairwise ổn định nhất trong phạm vi đã thử.
