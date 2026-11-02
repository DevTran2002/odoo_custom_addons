# 02. Yêu cầu nghiệp vụ & yêu cầu chức năng

> **Dự án:** TH Collaborator - Quản lý cộng tác viên & hợp đồng  
> **Module:** th_collaborator (16.0.1.3.0), th_collaborator_sign_vnpt (16.0.1.0.0)  
> **Nền tảng:** Odoo 16 (Community/Enterprise), Python 3.10, PostgreSQL  
> **Cập nhật:** 18/10/2026 · **Tác giả:** Sonbn

## 1. Yêu cầu nghiệp vụ (BR)

| ID | Yêu cầu | Mục tiêu | Ưu tiên |
|---|---|---|---|
| BR-01 | Quản lý thông tin CTV: họ tên, email, SĐT, người phụ trách, tên hợp đồng, loại hợp đồng | Một nơi tra cứu CTV | Cao |
| BR-02 | Lưu 2 loại hợp đồng: do công ty đẩy lên và do CTV tự đẩy lên | Tách bản công ty gửi / bản CTV ký | Cao |
| BR-03 | Gửi mail cho CTV tự map tên + email ("Xin chào <Tên>"), gửi bằng email người phụ trách | Giảm thao tác, đúng người liên hệ | Cao |
| BR-04 | CTV không đăng nhập vẫn tải được hợp đồng qua link trong mail, dùng SĐT để xác thực/map bản ghi | CTV không có tài khoản hệ thống | Cao |
| BR-05 | Đẩy và tải hợp đồng số lượng lớn cùng lúc | Xử lý hàng trăm CTV | Cao |
| BR-06 | Upload file thường chỉ nhận PDF hoặc ảnh | Chuẩn hoá hồ sơ | Trung bình |
| BR-07 | Hỏi xác nhận trước khi gửi lại mail; chỉ gửi khi có email và hợp đồng công ty/template | Tránh gửi trùng/thiếu | Trung bình |
| BR-08 | Có bộ lọc sẵn "CTV của tôi" theo người phụ trách | Nhân viên tập trung CTV mình phụ trách | Trung bình |
| BR-09 | Phân quyền đơn giản: chỉ 1 quyền nhân viên | Dễ vận hành | Trung bình |
| BR-10 | Hợp đồng CTV gửi lên được đặt tên chuẩn SĐT_Tên | Dễ tra cứu, lưu trữ | Trung bình |
| BR-11 | Tải template hợp đồng, đục lỗ thông tin CTV vào hợp đồng, xem trước, cấu hình mẫu email | Tự động hoá soạn hợp đồng | Cao |
| BR-12 | Chọn thông tin cần đục lỗ và gắn với trường mong muốn; vẽ ô trên PDF không có ô form | Dùng được mọi mẫu hợp đồng | Cao |
| BR-13 | Tạo hợp đồng từ template lưu vào Hợp đồng công ty | Kiểm soát bản gửi CTV | Cao |
| BR-14 | Bên A ký số hợp đồng bằng USB Token qua VNPT-CA Plugin, ký lẻ và ký hàng loạt | Hợp đồng có giá trị pháp lý điện tử | Cao |
| BR-15 | Có thể chuyển sang nhà cung cấp chữ ký số khác mà không viết lại hệ thống | Không phụ thuộc 1 nhà cung cấp | Cao |
| BR-16 | Tuân thủ quy tắc lập trình của đội (đặt tên th_, phân quyền role/access, logging, docstring...) | Chất lượng & bảo trì | Bắt buộc |

## 2. Yêu cầu chức năng (FR)

| ID | Chức năng | Mô tả / tiêu chí chấp nhận | BR | Trạng thái |
|---|---|---|---|---|
| FR-01 | Quản lý hồ sơ CTV | Form/list/search CTV; bắt buộc tên, SĐT, email, người phụ trách, tên hợp đồng trên view; email đúng định dạng; SĐT ≥9 số và không trùng (chuẩn hoá +84/0) | BR-01 | Hoàn thành |
| FR-02 | Loại hợp đồng dạng tag | Menu Cấu hình > Loại hợp đồng; tag có màu, sắp xếp, lưu trữ; ô chọn trên CTV không cho tạo nhanh | BR-01 | Hoàn thành |
| FR-03 | 2 kho hợp đồng | Tab Hợp đồng công ty / Hợp đồng CTV tải lên (many2many_binary, chỉ PDF/ảnh); file gắn res_model/res_id = CTV | BR-02 | Hoàn thành |
| FR-04 | Gửi mail hợp đồng | Nút trên form (ẩn khi thiếu email hoặc thiếu HĐ công ty/template); nút gửi lại có xác nhận; nút gửi hàng loạt trên list có xác nhận; From/Reply-To = người phụ trách; đính kèm toàn bộ Hợp đồng công ty | BR-03, BR-07 | Hoàn thành |
| FR-05 | Link upload công khai | Token ngẫu nhiên/CTV; CTV nhập SĐT đã đăng ký; ≤10 file, ≤20MB/file; PDF/ảnh kiểm tra nội dung thật; nút tạo lại link vô hiệu link cũ | BR-04, BR-06 | Hoàn thành |
| FR-06 | Đặt tên hợp đồng CTV | File CTV gửi lên đổi tên SĐT_Tên.<đuôi>, các file sau SĐT_Tên_2, _3 (đếm tiếp theo số file đã có) | BR-10 | Hoàn thành |
| FR-07 | Upload hàng loạt (wizard) | Chọn loại HĐ + hình thức (Nhiều file PDF/ảnh \| ZIP); map theo SĐT ở đầu tên file hoặc tên thư mục; báo file không map được; giới hạn ZIP 2.000 file/1GB | BR-05 | Hoàn thành |
| FR-08 | Tải ZIP hàng loạt | 2 nút: Tải HĐ công ty (ZIP), Tải HĐ CTV (ZIP); 1 cấp thư mục SĐT_Tên/; trùng tên thêm id | BR-05 | Hoàn thành |
| FR-09 | Bộ lọc CTV của tôi | Action mặc định search_default_th_filter_my; nhóm theo trạng thái/người phụ trách/loại HĐ | BR-08 | Hoàn thành |
| FR-10 | Phân quyền 1 role | Role "Nhân viên quản lý CTV" -> access group giữ ACL; menu theo group | BR-09, BR-16 | Hoàn thành |
| FR-11 | Template hợp đồng PDF | Upload PDF (có/không ô form); nhận diện ô form; gắn mẫu email, loại HĐ, cấu hình ký số | BR-11 | Hoàn thành |
| FR-12 | Cấu hình đục lỗ | Bảng ô form -> trường CTV (Selection động, gợi ý ten/email/sdt...); "Đọc lại ô form" giữ cấu hình cũ | BR-12 | Hoàn thành |
| FR-13 | Màn hình thiết kế ô đục lỗ | Render PDF (pdf.js), kéo vẽ ô, di chuyển, đổi kích thước, Delete xoá, chọn trường + cỡ chữ, chuyển trang, lưu, xem thử | BR-12 | Hoàn thành |
| FR-14 | Đục lỗ PDF tiếng Việt | Vẽ chữ bằng font Unicode tại toạ độ ô, tự thu nhỏ chữ cho vừa, flatten ô đã điền; định dạng ngày dd/mm/yyyy, selection, tag | BR-11 | Hoàn thành |
| FR-15 | Xem trước hợp đồng | Trên CTV (dữ liệu thật) và template (nhãn trường); PDF inline, không lưu file | BR-11 | Hoàn thành |
| FR-16 | Cấu hình mẫu email | Menu Cấu hình > Mẫu email hợp đồng (mail.template của CTV); mỗi template HĐ chọn 1 mẫu | BR-11 | Hoàn thành |
| FR-17 | Tạo hợp đồng | Nút Tạo hợp đồng / Tạo lại hợp đồng (xác nhận) lưu vào Hợp đồng công ty; thay bản cũ, xoá bản cũ nếu chưa gửi mail; reset trạng thái ký | BR-13 | Hoàn thành |
| FR-18 | Cấu hình ký số | Nhà cung cấp, kiểu hiển thị (5 kiểu), ảnh, bật/tắt thông tin, mô tả {thoi_gian}, cỡ/màu chữ, ký nháy, TSA | BR-14 | Hoàn thành |
| FR-19 | Ô chữ ký bên A | Vẽ trên màn hình thiết kế, loại ô "Chữ ký số bên A", tối đa 1 ô/template | BR-14 | Hoàn thành |
| FR-20 | Ký số lẻ & hàng loạt | Nút Ký số bên A (form) / Ký số hàng loạt (list); chọn chứng thư 1 lần, nhập PIN 1 lần/lô; lưu file _da_ky.pdf; vết người ký, thời gian, chứng thư | BR-14 | Hoàn thành (chưa test token thật) |
| FR-21 | Ràng buộc sau ký | Chặn gửi mail khi template yêu cầu ký mà chưa ký; chặn ký lại; tạo lại hợp đồng thì bỏ chữ ký | BR-14 | Hoàn thành |
| FR-22 | Khung đa nhà cung cấp ký số | Hook Python + registry JS; nhà cung cấp kiểu client/server; module VNPT là provider đầu tiên | BR-15 | Hoàn thành |

## 3. Yêu cầu phi chức năng (NFR)

| ID | Nhóm | Yêu cầu |
|---|---|---|
| NFR-01 | Hiệu năng | Gửi nhiều mail không treo màn hình (khuyến nghị force_send=False); ZIP stream qua file tạm, đọc trực tiếp filestore; ký 1 lô 1 lần PIN |
| NFR-02 | Bảo mật | Token + SĐT, CSRF, kiểm tra nội dung file, chặn zip bomb, sudo có lý do, quyền file theo bản ghi |
| NFR-03 | Tiếng Việt | Font Unicode khi đục lỗ; giao diện & thông báo tiếng Việt |
| NFR-04 | Mở rộng | Thêm nhà cung cấp ký số bằng module riêng, không sửa lõi |
| NFR-05 | Tuân thủ quy tắc đội | Prefix th_, đặt tên XML ID th_<module>_<object>_<type>, _logger, docstring, không required/readonly trên field |

## 4. Ma trận truy vết BR → FR

| BR | Yêu cầu | Chức năng đáp ứng |
|---|---|---|
| BR-01 | Quản lý thông tin CTV: họ tên, email, SĐT, người phụ trách, tên hợp đồ… | FR-01, FR-02 |
| BR-02 | Lưu 2 loại hợp đồng: do công ty đẩy lên và do CTV tự đẩy lên | FR-03 |
| BR-03 | Gửi mail cho CTV tự map tên + email ("Xin chào <Tên>"), gửi bằng email… | FR-04 |
| BR-04 | CTV không đăng nhập vẫn tải được hợp đồng qua link trong mail, dùng SĐ… | FR-05 |
| BR-05 | Đẩy và tải hợp đồng số lượng lớn cùng lúc | FR-07, FR-08 |
| BR-06 | Upload file thường chỉ nhận PDF hoặc ảnh | FR-05 |
| BR-07 | Hỏi xác nhận trước khi gửi lại mail; chỉ gửi khi có email và hợp đồng … | FR-04 |
| BR-08 | Có bộ lọc sẵn "CTV của tôi" theo người phụ trách | FR-09 |
| BR-09 | Phân quyền đơn giản: chỉ 1 quyền nhân viên | FR-10 |
| BR-10 | Hợp đồng CTV gửi lên được đặt tên chuẩn SĐT_Tên | FR-06 |
| BR-11 | Tải template hợp đồng, đục lỗ thông tin CTV vào hợp đồng, xem trước, c… | FR-11, FR-14, FR-15, FR-16 |
| BR-12 | Chọn thông tin cần đục lỗ và gắn với trường mong muốn; vẽ ô trên PDF k… | FR-12, FR-13 |
| BR-13 | Tạo hợp đồng từ template lưu vào Hợp đồng công ty | FR-17 |
| BR-14 | Bên A ký số hợp đồng bằng USB Token qua VNPT-CA Plugin, ký lẻ và ký hà… | FR-18, FR-19, FR-20, FR-21 |
| BR-15 | Có thể chuyển sang nhà cung cấp chữ ký số khác mà không viết lại hệ th… | FR-22 |
| BR-16 | Tuân thủ quy tắc lập trình của đội (đặt tên th_, phân quyền role/acces… | FR-10 |
