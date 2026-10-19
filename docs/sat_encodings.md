# Các encoding AMO cho N-Queens

## 1. Phần mô hình không thay đổi

Biến gốc `x[r,c]` có ID `r*N+c+1`, đúng khi ô `(r,c)` có hậu. Vì vậy N²
biến bàn cờ chiếm đúng miền `1..N²`. Mỗi hàng và cột dùng EO (exactly-one),
còn mỗi đường chéo `r-c` và `r+c` chỉ dùng AMO (at-most-one). Không có ALO
cho đường chéo và không có symmetry breaking.

Với nhóm `S`, ALO luôn là **một clause trực tiếp** chứa toàn bộ `S`. EO luôn
là ALO cộng AMO. Chỉ thành phần AMO thay đổi theo tùy chọn encoding.

## 2. Ba cách mã hóa AMO

Xét nhóm ba biến gốc `a,b,c`.

### Pairwise

Thêm một clause cho từng cặp:

```text
(¬a ∨ ¬b) ∧ (¬a ∨ ¬c) ∧ (¬b ∨ ¬c)
```

Nhóm k biến dùng `k(k-1)/2` clause và không có biến phụ. Cách này trực quan,
nhưng số clause tăng bậc hai.

### Sequential counter

Sequential counter đưa các biến trạng thái phụ vào một chuỗi. Về ý tưởng,
trạng thái thứ i ghi rằng đã thấy một biến đúng trong tiền tố đến vị trí i;
các clause truyền trạng thái về phía trước và cấm một biến gốc mới đúng khi
trạng thái trước đã đúng. Dự án gọi đúng API đã kiểm tra:

```python
CardEnc.atmost(lits=S, bound=1, vpool=vpool, encoding=EncType.seqcounter)
```

Ví dụ `a,b,c` vì thế có thêm biến phụ (tên minh họa `s1,s2`); người dùng
không gán trước chúng. Một phép gán biến gốc hợp lệ chỉ cần **tồn tại** phần
gán `s1,s2` mở rộng làm CNF thỏa mãn.

### Bitwise

Bitwise gán cho mỗi biến gốc một mã nhị phân bằng các bit phụ. Nếu một biến
gốc đúng, các clause buộc bit phụ mang mã của biến đó. Hai biến gốc khác nhau
không thể cùng đúng vì mã của chúng khác nhau ở ít nhất một bit. Nhóm ba biến
cần các bit đủ phân biệt ba mã. Dự án gọi:

```python
CardEnc.atmost(lits=S, bound=1, vpool=vpool, encoding=EncType.bitwise)
```

## 3. Cấp ID và giải mã

Một `IDPool(start_from=N*N+1)` duy nhất được truyền qua mọi nhóm hàng, cột và
đường chéo. Nhờ đó biến phụ của các nhóm không trùng nhau và không đè miền
biến bàn cờ. Decoder vẫn chỉ lấy literal dương trong `1..N²`; mọi literal
biến phụ bị bỏ qua.

Số biến được định nghĩa như sau:

- biến bàn cờ: N²;
- biến phụ: số ID mà pool chung đã cấp ngoài miền bàn cờ;
- tổng biến: tổng hai đại lượng trên.

Không dùng mặc định “max ID = số biến xuất hiện”, vì quy tắc đó không tổng
quát khi một cơ chế cấp ID để lại khoảng trống. IDPool hiện cấp liên tiếp,
nhưng số đếm vẫn dựa trên miền đã cấp một cách tường minh.

AMO của nhóm rỗng hoặc một biến là hằng đúng nên không sinh clause/biến phụ.
ALO (và do đó EO) của nhóm rỗng bị từ chối bằng `ValueError`.

## 4. Tính đúng và cách kiểm thử

Mọi encoding AMO phải thỏa tính chất: một phép gán biến gốc có thể mở rộng
thành phép gán thỏa CNF khi và chỉ khi số biến đúng không quá một. Với EO,
điều kiện là đúng chính xác một biến. Test vét cạn mọi phép gán gốc của nhóm
nhỏ, cố định chúng bằng assumptions rồi để Glucose3 tự tìm biến phụ. Đây là
kiểm tra đúng về mặt tồn tại, không phụ thuộc một cách gán biến phụ cụ thể.

Phần chứng minh mô hình N-Queens vẫn như pairwise: nghiệm bàn cờ hợp lệ thỏa
EO hàng/cột và AMO đường chéo; ngược lại, EO hàng tạo đúng N hậu, EO cột và
hai họ AMO loại mọi tấn công. Validator kiểm tra luật bàn cờ độc lập với CNF.

## 5. Kích thước không phải kết luận hiệu năng

Pairwise thường dùng nhiều clause nhưng không có biến phụ. Sequential và
bitwise có thể giảm clause ở nhóm lớn nhưng làm tăng số biến và thay đổi cấu
trúc/khả năng lan truyền đơn vị của CNF. Thời gian còn phụ thuộc solver, kích
thước N, cấu trúc clause, heuristic, phần cứng và nhiễu đo. Vì chưa chạy
benchmark có kiểm soát, mọi dự đoán encoding nào nhanh hơn ở mốc này chỉ là
**giả thuyết**, không phải kết quả thực nghiệm.
