# Hướng dẫn làm việc cho Codex

## 1. Mục tiêu dự án

Xây dựng chương trình giải bài toán N-Queens bằng SAT phục vụ
bài tập lớn môn Các vấn đề hiện đại của Khoa học máy tính.

Dự án cần:
- Mã hóa N-Queens thành CNF.
- Gọi SAT solver thông qua PySAT.
- So sánh các encoding AMO.
- So sánh với CP-SAT, IBM CP Optimizer, CPLEX MIP và Gurobi
  theo yêu cầu bài tập.
- Lưu kết quả thực nghiệm có thể tái lập.
- Cung cấp tài liệu để sinh viên hiểu và viết báo cáo khoa học.

Nhiệm vụ mặc định là tìm một nghiệm hợp lệ.
Không chuyển sang đếm hoặc liệt kê tất cả nghiệm nếu chưa được yêu cầu.

## 2. Cách làm việc

- Đọc README, mã nguồn và các kiểm thử hiện có trước khi sửa.
- Giữ lại những thay đổi của người dùng không liên quan đến nhiệm vụ.
- Thực hiện theo từng mốc nhỏ có thể chạy và kiểm tra.
- Ưu tiên mã nguồn rõ ràng, dễ giải thích trong báo cáo.
- Không thêm GUI, web app, database hoặc framework không cần thiết.
- Không tự mở rộng sang Sudoku hay biến thể N-Queens.
- Nếu yêu cầu chưa rõ, nêu giả định và tác động.
- Chỉ hỏi khi quyết định đó ảnh hưởng đáng kể đến phạm vi hoặc
  không thể tiếp tục đúng với thông tin hiện có.

Sau mỗi mốc, giải thích bằng tiếng Việt:
1. Đã thay đổi những gì.
2. Thuật toán và ý nghĩa các hàm chính.
3. Cách chạy.
4. Những kiểm tra đã thực hiện và kết quả thực tế.
5. Nội dung có thể sử dụng trong báo cáo.
6. Những hạn chế hoặc phần chưa hoàn thành.

## 3. Công nghệ và môi trường

- Ngôn ngữ: Python.
- Môi trường ảo: .venv.
- SAT toolkit: gói python-sat, import qua namespace pysat.
- SAT solver khởi đầu: Glucose3.
- Mã hóa khởi đầu: pairwise.
- Triển khai sequential counter và bitwise ở mốc tiếp theo.
- Các solver so sánh là thành phần tùy chọn về cài đặt;
  thiếu chúng không được làm hỏng chức năng SAT cơ bản.

Trước khi thêm dependency:
- Kiểm tra dependency hiện có.
- Chỉ thêm thư viện cần thiết.
- Cập nhật tệp khai báo dependency tương ứng.
- Ghi lại phiên bản đã dùng cho thực nghiệm.

Không tự giả định giấy phép thương mại đã có.
Không tự mua giấy phép hoặc sử dụng dịch vụ trả phí.

## 4. Cấu trúc mã nguồn

Ở giai đoạn đầu, giữ cấu trúc đơn giản:

- main.py: giao diện dòng lệnh.
- sat_encoding.py: tạo CNF và các encoding.
- sat_solver.py: gọi SAT solver và giải mã.
- validator.py: kiểm tra nghiệm độc lập.
- benchmark.py: chạy thực nghiệm và lưu dữ liệu.
- tests/: kiểm thử.
- results/: kết quả thực nghiệm.
- docs/: giải thích mô hình và hướng dẫn báo cáo.
- README.md: cài đặt và cách chạy.

Khi thêm phương pháp so sánh, có thể tạo:
- cpsat_solver.py
- cp_solver.py
- mip_solver.py

Không đặt tên tệp trùng thư viện chuẩn hoặc dependency,
ví dụ encodings.py, time.py, csv.py, pysat.py.

Không tái cấu trúc toàn bộ dự án nếu nhiệm vụ hiện tại không cần.

## 5. Quy tắc mô hình SAT

- N phải là số nguyên dương.
- Hàng và cột đánh số từ 0 đến N - 1.
- Biến x[r,c] đúng khi ô (r,c) có hậu.
- ID biến bàn cờ: r * N + c + 1.
- Biến bàn cờ nằm trong khoảng 1 đến N*N.

Ràng buộc của mô hình cơ sở:
- Mỗi hàng có chính xác một hậu.
- Mỗi cột có chính xác một hậu.
- Mỗi đường chéo có cùng r-c chứa nhiều nhất một hậu.
- Mỗi đường chéo có cùng r+c chứa nhiều nhất một hậu.
- Không thêm ALO cho đường chéo.

Pairwise:
- ALO là một clause chứa toàn bộ biến của nhóm.
- AMO thêm clause [-a, -b] cho mỗi cặp biến khác nhau.
- EO là ALO kết hợp AMO.

Encoding có biến phụ:
- Dùng một cơ chế cấp ID thống nhất cho toàn bộ CNF.
- Không để biến phụ trùng biến bàn cờ hoặc biến phụ của nhóm khác.
- Khi giải mã, chỉ lấy biến bàn cờ dương từ 1 đến N*N.

Không thêm symmetry breaking hoặc bỏ ràng buộc dư thừa
mà không ghi rõ cấu hình và tác động lên thực nghiệm.

## 6. Kết quả và trạng thái

Các phương pháp phải trả kết quả theo một cấu trúc thống nhất:
- N.
- Phương pháp.
- Solver.
- Encoding nếu có.
- Trạng thái.
- Nghiệm nếu có.
- Các số đo thời gian.
- Thông tin kích thước mô hình nếu phù hợp.

Phân biệt:
- SAT: đã tìm được nghiệm.
- UNSAT: solver đã chứng minh không có nghiệm.
- TIMEOUT: hết thời gian mà chưa có kết luận.
- UNKNOWN: chưa có kết luận vì lý do khác.
- ERROR: lỗi thực thi.
- UNAVAILABLE: thiếu solver, dependency hoặc giấy phép.

Không chuyển lỗi, UNKNOWN hoặc TIMEOUT thành UNSAT.

Nếu solver tìm được nghiệm trước khi hết thời gian,
ghi nhận nghiệm và kiểm tra tính hợp lệ.

Lưu trạng thái gốc của backend nếu cần để đối chiếu.

## 7. Kiểm tra tính đúng đắn

Validator phải kiểm tra trực tiếp luật N-Queens,
không dùng lại CNF hoặc kết quả tự xác nhận của solver.

Một nghiệm hợp lệ phải:
- Có đúng N quân hậu.
- Tất cả tọa độ nằm trong bàn cờ.
- Có N hàng khác nhau.
- Có N cột khác nhau.
- Có N giá trị r-c khác nhau.
- Có N giá trị r+c khác nhau.

Các trường hợp bắt buộc:
- N=1: SAT.
- N=2: UNSAT.
- N=3: UNSAT.
- N=4: SAT.
- N=8: SAT.

Không so sánh nghiệm với một cách đặt hậu duy nhất.
Kiểm tra nghiệm theo các ràng buộc.

Với encoding có biến phụ, kiểm tra ở quy mô nhỏ rằng
phép gán biến gốc hợp lệ có thể mở rộng thành phép gán
thỏa mãn và phép gán biến gốc không hợp lệ bị loại.

Mỗi thay đổi logic phải được kiểm tra bằng các trường hợp
có khả năng phát hiện lỗi của thay đổi đó.

## 8. Quy tắc thực nghiệm

Tách hai nhóm:
1. So sánh encoding với cùng SAT solver.
2. So sánh phương pháp trên cùng bài toán và nhiệm vụ.

Mọi phương pháp mặc định tìm một nghiệm.
Không so sánh tìm một nghiệm với liệt kê toàn bộ nghiệm.

Chạy thăm dò trước khi chạy benchmark lớn.
Dãy N ban đầu có thể là 8, 16, 32, 64, 128, 256,
sau đó điều chỉnh theo tài nguyên thực tế.

Ghi lại:
- Mã lần chạy và thời điểm.
- Phiên bản mã nguồn nếu có Git.
- Hệ điều hành, CPU và RAM.
- Phiên bản Python, thư viện và solver.
- N, encoding và toàn bộ cấu hình liên quan.
- Seed nếu backend hỗ trợ.
- Số luồng hoặc worker.
- Giới hạn thời gian và phạm vi áp dụng giới hạn.
- Trạng thái và kết quả validator.

Định nghĩa rõ các số đo:
- build_time: thời gian tạo mô hình.
- load_time: thời gian nạp/khởi tạo backend nếu tách được.
- solve_time: thời gian gọi giải.
- total_time: thời gian tổng theo ranh giới được tài liệu hóa.

Không bỏ qua chi phí nạp CNF khi báo cáo tổng thời gian.
Dùng đồng hồ đo thời gian đơn điệu, ví dụ perf_counter.

Đối với SAT, ghi số biến và số clause.
Không coi số clause SAT tương đương số constraint CP/MIP.

Lưu dữ liệu thô trước khi tổng hợp.
Không ghi đè kết quả cũ một cách âm thầm.
Không coi thời gian timeout là thời gian giải thành công.

Benchmark lớn cần có giới hạn thời gian thực sự được thực thi.
Không chỉ đo thời gian sau khi solver chạy xong rồi gọi là timeout.

## 9. Tính trung thực của kết quả

- Tuyệt đối không tạo số liệu thực nghiệm giả.
- Không ghi đã chạy kiểm thử khi chưa chạy.
- Phân biệt rõ kết quả dự kiến với kết quả đã quan sát.
- Nếu không chạy được backend, ghi UNAVAILABLE cùng lý do.
- Không dùng kết quả của solver khác để thay thế rồi đổi tên.
- Không kết luận phương pháp nào tốt hơn khi chưa có dữ liệu.
- Mọi bảng và biểu đồ kết quả phải truy được về dữ liệu thô.
- Không bịa tài liệu tham khảo, DOI hoặc liên kết repository.

## 10. Tài liệu và báo cáo

README cần có:
- Mục tiêu dự án.
- Cách tạo môi trường và cài dependency.
- Cách chạy một bài toán.
- Cách chọn encoding và solver.
- Cách chạy kiểm thử.
- Cách chạy và tái lập benchmark.
- Giải thích các trạng thái trả về.

Tài liệu mô hình cần có:
- Định nghĩa biến.
- Các ràng buộc toán học.
- Ví dụ CNF nhỏ.
- Giải thích tính đúng đắn theo hai chiều.
- Cách giải mã nghiệm.
- Số biến, số clause và chi phí của encoding.

Báo cáo cuối tuân theo mẫu giảng viên cung cấp.
Đề yêu cầu định dạng bài báo Elsevier cas-sc.
Nếu chưa có mẫu chi tiết, không tự tuyên bố đã đáp ứng mẫu đó.

Phần Data Availability cần liên kết repository thực tế
chứa mã nguồn, kết quả và hướng dẫn tái lập.

## 11. Tiêu chí hoàn thành một mốc

Một mốc chỉ hoàn thành khi:
- Chức năng của mốc chạy được trong môi trường đã nêu.
- Các kiểm tra liên quan đạt.
- Mọi nghiệm tìm được đều qua validator.
- Tài liệu và lệnh chạy được cập nhật.
- Những giới hạn hoặc lỗi còn lại được công khai.
- Có giải thích đủ để sinh viên trình bày trong báo cáo.

Chỉ hoàn thành phạm vi của mốc đang được giao.
Không triển khai toàn bộ các mốc tương lai khi người dùng
đang yêu cầu học hoặc thực hiện từng bước.