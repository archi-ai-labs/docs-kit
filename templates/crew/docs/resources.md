# resources — tài nguyên dùng chung là KHOÁ, không phải vai

Máy test thật, môi trường stable local, database dùng chung thường chỉ có một.
Biến chúng thành một vai thì được một hàng người chờ; biến thành **khoá có
tên** thì được một hàng phiếu xếp thứ tự. Tên khoá và các mẫu lệnh hay chạm nó
khai trong `.docs-kit.json` → `crew.resources`.

```
scripts/crew lock acquire e2e-harness 157          # giữ, hoặc báo ai đang giữ
scripts/crew lock acquire e2e-harness 157 --wait   # xếp hàng chờ
scripts/crew lock release e2e-harness 157          # trả, ghi thời gian giữ
```

Khoá **ghi giờ cấp và giờ trả** vào `../<repo>-crew/log.tsv` — không có
timestamp thì không chỉnh lại được các ngưỡng bên dưới.

## Mỗi phiếu tách hai phần

- **phần cục bộ** (typecheck, unit test) — chạy song song không giới hạn;
- **phần máy thật** (e2e, staging) — xếp hàng qua khoá, để **nhỏ và ở cuối**.

Phiếu nào phần máy thật lớn hơn phần cục bộ là phiếu ops và xếp hàng riêng —
nó không được định nhịp cho các executor.

## Nhịp nhận phiếu — ba tín hiệu đèn

`scripts/crew status` dịch log khoá thành ba tín hiệu, không bắt ai tính công
thức:

| Tín hiệu | Đọc là | Việc cần làm |
|---|---|---|
| tổng chờ khoá hôm nay = 0 | máy thật rảnh | nhận thêm phiếu nặng được |
| chờ khoá cộng dồn > 30 phút/ngày | khoá thành cổ chai | bớt một phiên nặng |
| đang mở > 4 phiên | vượt sức người đọc | ngừng nhận, kể cả phiếu nhẹ |

Đếm **suất khoá**, không đếm phiếu: phiếu nặng (cần khoá) = 1 suất, phiếu nhẹ
= 0 suất, và mỗi tài nguyên chỉ có **1 suất** vì máy thật chỉ có một. Trần
4 phiên có lý do khác hẳn: thường chỉ có một người đọc kết quả. Ngưỡng
30 phút là điểm khởi đầu để chỉnh theo repo (`setup.md`), không phải hằng số;
log thô giữ nguyên để tính lại bất cứ lúc nào.

## Lưới phụ

Hook resource-guard nhắc khi một lệnh khớp mẫu của tài nguyên mà chưa ai giữ
khoá. Nó **đo được người hợp tác, không đo được người quên**: khớp chuỗi con
trên một lệnh Bash, nên lệnh chạy qua wrapper script lọt êm không log. Hàng
rào thật là `crew lock` và kỷ luật trong tệp vai; hook chỉ là lưới phụ và
vĩnh viễn chỉ nhắc, không chặn.
