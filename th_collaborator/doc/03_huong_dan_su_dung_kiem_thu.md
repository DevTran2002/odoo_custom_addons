# 03. Hướng dẫn sử dụng & kịch bản kiểm thử

> **Dự án:** TH Collaborator - Quản lý cộng tác viên & hợp đồng  
> **Module:** th_collaborator (16.0.1.3.0), th_collaborator_sign_vnpt (16.0.1.0.0)  
> **Nền tảng:** Odoo 16 (Community/Enterprise), Python 3.10, PostgreSQL  
> **Cập nhật:** 18/10/2026 · **Tác giả:** Sonbn

## Phần A – Hướng dẫn sử dụng

![Quy trình](images/so_do_quy_trinh.png)

### A1. Cài đặt & phân quyền

1. Thêm thư mục D:\work\odoo-16.0\Owl-odoo vào addons_path.
2. Cài module "TH Collaborator"; nếu ký số VNPT cài thêm "TH Collaborator - Ký số VNPT-CA Plugin".
3. Settings > Users: gán quyền "Nhân viên quản lý CTV" (nhóm Cộng tác viên) cho nhân viên.
4. Đảm bảo user có email (dùng làm người gửi mail).

### A2. Tạo CTV

1. Menu Cộng tác viên > Cộng tác viên > Mới.
2. Nhập Tên hợp đồng, Họ tên, SĐT, Email, Người phụ trách, Loại hợp đồng, Template hợp đồng.
3. Lưu. Link upload riêng của CTV hiện ở ô "Link upload hợp đồng" (có nút copy).
4. Tạo hàng loạt: Favorites > Import records từ Excel (cột Họ tên, Email, SĐT...).

### A3. Cấu hình loại hợp đồng & mẫu email

1. Cấu hình > Loại hợp đồng: thêm dòng, chọn màu.
2. Cấu hình > Mẫu email hợp đồng: sửa tiêu đề/nội dung; dùng object.name, object.th_upload_url.

### A4. Template hợp đồng & đục lỗ

1. Cấu hình > Template hợp đồng > Mới: nhập tên, upload PDF, chọn mẫu email, lưu.
2. PDF có ô form: tab Cấu hình đục lỗ tự sinh dòng; chọn trường CTV cho từng ô.
3. PDF không có ô form: bấm "Thiết kế ô đục lỗ", kéo chuột vẽ ô, chọn trường, chỉnh cỡ chữ, Lưu.
4. Bấm "Xem thử với dữ liệu mẫu" để kiểm tra vị trí.

### A5. Tạo hợp đồng & gửi mail

1. Trên CTV chọn Template hợp đồng > "Xem trước hợp đồng" (không lưu).
2. Bấm "Tạo hợp đồng": file SĐT_Tên_<template>.pdf vào tab Hợp đồng công ty.
3. Bấm "Gửi mail hợp đồng" (lần sau là "Gửi lại", có xác nhận). Mail gửi từ email người phụ trách, kèm Hợp đồng công ty.
4. Gửi nhiều: chọn CTV trên danh sách > "Gửi mail hợp đồng".

### A6. CTV tải hợp đồng lên

1. CTV mở link trong mail, nhập SĐT đã đăng ký, chọn tối đa 10 file PDF/ảnh (≤20MB/file), bấm Gửi.
2. Hệ thống đổi tên SĐT_Tên.pdf, lưu vào tab Hợp đồng CTV tải lên, trạng thái "CTV đã tải hợp đồng", báo người phụ trách trên chatter.

### A7. Tải lên / tải về hàng loạt

1. Menu Tải hợp đồng hàng loạt: chọn Loại hợp đồng + Hình thức (Nhiều file | ZIP).
2. Đặt tên file 0912345678_hopdong.pdf hoặc ZIP có thư mục 0912345678/. SĐT không có dấu cách/gạch.
3. Bấm Tải lên, xem kết quả và danh sách file không map được.
4. Tải về: chọn CTV trên danh sách > "Tải HĐ công ty (ZIP)" hoặc "Tải HĐ CTV (ZIP)".

### A8. Ký số bên A (VNPT USB Token)

1. Máy người ký: cài VNPT-CA Plugin, cắm USB Token.
2. Cấu hình > Cấu hình ký số > Mới: Nhà cung cấp VNPT-CA Plugin, License key, kiểu hiển thị, ảnh con dấu, mô tả.
3. Template hợp đồng: chọn Cấu hình ký số bên A; vào Thiết kế ô đục lỗ vẽ 1 ô, Loại ô = "Chữ ký số bên A", Lưu.
4. CTV: Tạo hợp đồng > "Ký số bên A" > chọn chứng thư > nhập PIN. Hàng loạt: chọn nhiều CTV > "Ký số hàng loạt" (PIN 1 lần).
5. File _da_ky.pdf thay bản chưa ký; sau đó mới gửi mail được.

## Phần B – Kịch bản kiểm thử

Tổng 25 kịch bản · **Đạt: 14** · **Chưa test: 11**. Môi trường đã test: DB riêng `th_collaborator_test`, Odoo 16 local cổng 8099; ký số dùng plugin giả lập (chưa có USB Token).

| ID | FR | Điều kiện | Các bước | Kết quả mong đợi | Kết quả thực tế | Trạng thái |
|---|---|---|---|---|---|---|
| TC-01 | FR-01 | Đăng nhập nhân viên | Tạo CTV SĐT +84912345678; tạo CTV khác SĐT 0912345678 | CTV 2 bị chặn: "Số điện thoại đã tồn tại" |  | Chưa test |
| TC-02 | FR-01 |  | Nhập email "abc@" | Báo email không hợp lệ |  | Chưa test UI |
| TC-03 | FR-04 | CTV chưa có email / chưa HĐ & template | Mở form CTV | Ẩn nút Gửi mail; gửi từ list báo lỗi kèm tên CTV |  | Chưa test |
| TC-04 | FR-04 | CTV đã gửi mail | Bấm "Gửi lại mail hợp đồng" | Hiện hộp xác nhận | Nút có confirm | Đạt (view) |
| TC-05 | FR-04 | Template có ký số, đã ký | Gửi mail | Mail From = người phụ trách, đính kèm bản _da_ky.pdf | Đính kèm đúng; mail exception do DB test không có SMTP | Đạt |
| TC-06 | FR-05 | Có link upload | Mở link, nhập sai SĐT, gửi file | Báo SĐT không khớp, không lưu |  | Chưa test |
| TC-07 | FR-05/06 | Có link upload | Nhập đúng SĐT, gửi 2 file PDF | Lưu SĐT_Tên.pdf, SĐT_Tên_2.pdf; trạng thái CTV đã tải |  | Chưa test |
| TC-08 | FR-05 |  | Gửi file .docx đổi đuôi .pdf | Báo chỉ chấp nhận PDF/ảnh |  | Chưa test |
| TC-09 | FR-07 | CTV có SĐT | Wizard ZIP chứa 0912345678/hd.pdf và abc.pdf | hd.pdf gắn đúng CTV; abc.pdf trong danh sách không map |  | Chưa test |
| TC-10 | FR-08 | 2 CTV có HĐ | Tải HĐ công ty (ZIP) | ZIP có thư mục SĐT_Tên/ chứa file |  | Chưa test |
| TC-11 | FR-11 |  | Upload PDF không có ô form | Lưu được, không lỗi | Lưu thành công | Đạt |
| TC-12 | FR-12 | PDF có ô ten/email/sdt/chu_ky | Upload template | Sinh 4 dòng, gợi ý name/th_email/th_phone; chu_ky để trống | Nhận diện 4 ô | Đạt |
| TC-13 | FR-13 | Template PDF | Vẽ 4 ô, di chuyển, đổi kích thước, Delete, vẽ lại, Lưu | Toạ độ PDF lưu đúng | Đúng (mô phỏng sự kiện chuột) | Đạt |
| TC-14 | FR-14/15 | CTV tên "Nguyễn Thị Hồng Nhung" | Xem trước hợp đồng | Chữ đủ dấu, đúng dòng; ngày dd/mm/yyyy HH:MM | Hiển thị đúng | Đạt |
| TC-15 | FR-14 | Ô nhỏ, tên dài | Xem trước | Chữ tự thu nhỏ vừa ô | Đúng | Đạt |
| TC-16 | FR-17 | CTV có template | Tạo hợp đồng 2 lần | Bản lần 1 (chưa gửi mail) bị xoá; bản đã gửi mail được giữ | Đúng | Đạt |
| TC-17 | FR-17 | Chưa chọn template | Tạo hợp đồng | Báo "chưa chọn template" | Đúng | Đạt |
| TC-18 | FR-19 | Template | Vẽ ô, Loại ô = Chữ ký số bên A; đặt ô thứ 2 làm chữ ký | Ô viền xanh; ô cũ tự về ô thông tin; server chặn >1 ô | Hiển thị đúng | Đạt |
| TC-19 | FR-20 | 2 CTV đã tạo HĐ, plugin giả lập | Chọn 2 CTV > Ký số hàng loạt | 1 lần signArrDataAdvanced (2 file); PdfSigner đúng trang/toạ độ/SigType/ảnh/mô tả; lưu _da_ky.pdf + chứng thư | Đúng; cert "CÔNG TY TNHH ABC (TEST) \| Serial 54010101abcdef" | Đạt (plugin giả) |
| TC-20 | FR-20 | USB Token thật + license chính thức | Ký 1 hợp đồng, mở bằng Adobe/Foxit | Chữ ký hợp lệ, hiển thị đúng kiểu cấu hình |  | Chưa test – cần token |
| TC-21 | FR-18 | Token thật | Thử lần lượt 5 kiểu hiển thị, màu chữ, ký nháy | Hiển thị đúng từng kiểu |  | Chưa test – cần token |
| TC-22 | FR-21 | Template có ký số, chưa ký | Gửi mail | Báo "chưa được bên A ký số" | Đúng | Đạt |
| TC-23 | FR-21 | Đã ký | Ký lại / Tạo lại hợp đồng | Ký lại bị chặn; tạo lại thì is_signed = False | Đúng | Đạt |
| TC-24 | FR-22 | Cài module VNPT | Mở Cấu hình ký số | Có lựa chọn VNPT-CA Plugin + ô license; registry JS có "vnpt_plugin" | Đúng | Đạt |
| TC-25 | FR-10 | User không có role | Đăng nhập | Không thấy menu Cộng tác viên |  | Chưa test |
