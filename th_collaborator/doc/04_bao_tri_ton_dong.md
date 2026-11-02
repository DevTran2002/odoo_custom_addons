# 04. Bảo trì & vấn đề tồn đọng

> **Dự án:** TH Collaborator - Quản lý cộng tác viên & hợp đồng  
> **Module:** th_collaborator (16.0.1.3.0), th_collaborator_sign_vnpt (16.0.1.0.0)  
> **Nền tảng:** Odoo 16 (Community/Enterprise), Python 3.10, PostgreSQL  
> **Cập nhật:** 18/10/2026 · **Tác giả:** Sonbn

## 1. Hướng dẫn bảo trì

| Hạng mục | Nội dung |
|---|---|
| Cài đặt / nâng cấp | odoo-bin -c odoo.conf -d <db> -u th_collaborator,th_collaborator_sign_vnpt. Sửa Python cần restart; sửa view/field/data cần -u. |
| addons_path | Phải chứa D:\work\odoo-16.0\Owl-odoo (hiện odoo.conf chưa có). |
| Font đục lỗ | Linux: apt install fonts-dejavu-core, hoặc tham số hệ thống th_collaborator.pdf_font_path = đường dẫn .ttf. Đổi font cần restart. |
| Mail | Kiểm tra Settings > Technical > Emails (Outgoing/Exception). Cron "Mail: Email Queue Manager" phải chạy (max_cron_threads > 0). Email người phụ trách nên cùng domain SMTP (SPF/DMARC). |
| Giới hạn upload | Trang CTV: TH_UPLOAD_MAX_FILES=10, TH_UPLOAD_MAX_FILE_SIZE=20MB (controllers/th_main.py). Wizard ZIP: 2.000 file/1GB. Nginx client_max_body_size, Odoo limit_request, limit_time_real. |
| License VNPT | Cấu hình > Cấu hình ký số > License key. Gia hạn trước ngày hết hạn; key gắn domain. |
| Mẫu email | Data noupdate=1: sửa trên giao diện, upgrade không ghi đè. Người gửi luôn bị ép = người phụ trách trong code. |
| Thêm trường đục lỗ | Trường mới của CTV (char/text/date/selection/m2o/m2m...) tự xuất hiện trong danh sách chọn; loại trừ ở TH_EXCLUDED_FIELD_NAMES. |
| Thêm nhà cung cấp ký số | Xem mục Mở rộng trong tài liệu thiết kế (module th_collaborator_sign_<tên>). |
| Log | _logger ghi: gửi mail, CTV upload, sai SĐT, import hàng loạt, tải ZIP, ký số, lưu ô thiết kế. |
| Xử lý lỗi quyền | Kiểm tra user có role "Nhân viên quản lý CTV" -> group th_access_collaborator_user -> ACL ir.model.access.csv. |
| Sao lưu | Sao lưu DB + filestore (hợp đồng là ir.attachment trong filestore). |
| Dọn dẹp | Các bản hợp đồng cũ đã gửi mail được giữ (chatter tham chiếu) – theo dõi dung lượng filestore. |

### Lệnh thường dùng

```bash
# Nâng cấp module
odoo-bin -c odoo.conf -d <db> -u th_collaborator,th_collaborator_sign_vnpt
# Cài font tiếng Việt (Linux)
sudo apt install fonts-dejavu-core
```

### Quy trình tiếp nhận lỗi quyền (theo quy tắc đội)

1. Kiểm tra role được cấp cho user.
2. Tìm group bị báo lỗi (`th_access_collaborator_user`) và ACL tương ứng.
3. Xác định view/field/menu dùng group đó.

## 2. Vấn đề tồn đọng

Tổng 20 vấn đề · Cao: 2 · Trung bình: 7 · Thấp: 11

| ID | Vấn đề | Mức độ | Ảnh hưởng | Đề xuất | Phụ trách |
|---|---|---|---|---|---|
| ISS-01 | License VNPT-CA Plugin trong file mẫu là license TEST, hết hạn 30/10/2026 | Cao | Hết hạn sẽ không ký được | Xin license chính thức theo domain Odoo, nhập vào Cấu hình ký số | Nghiệp vụ / VNPT |
| ISS-02 | Chưa ký thử với USB Token thật (mới test với plugin giả lập) | Cao | Rủi ro khác biệt định dạng kết quả plugin | Chạy TC-20, TC-21 trên máy có token | Kỹ thuật |
| ISS-03 | Chưa xác nhận: SigType=3 cho "Chỉ ảnh", định dạng SigColorRGB, PagesArray khi ký lô | Trung bình | Hiển thị chữ ký có thể sai | Ký thử từng kiểu, đối chiếu tài liệu VNPT | Kỹ thuật |
| ISS-04 | Server chỉ kiểm tra PDF có /ByteRange, không xác thực chuỗi chứng thư/CRL/OCSP | Trung bình | Không phát hiện chữ ký giả mạo nếu RPC bị can thiệp | Bổ sung xác thực (pyHanko/endesive) hoặc API kiểm tra của VNPT | Kỹ thuật |
| ISS-05 | force_send=True nhưng comment ghi False và thông báo list ghi "đưa vào hàng đợi" | Thấp | Gửi nhiều mail có thể treo request; thông báo sai | Form gửi ngay, list dùng hàng đợi (force_send theo tham số); sửa comment/thông báo | Kỹ thuật |
| ISS-06 | Gửi mail bằng email người phụ trách qua SMTP công ty | Trung bình | Mail có thể bị chặn/spam (SPF/DMARC) | Dùng email cùng domain hoặc cấu hình alias/mail.default.from | Hạ tầng |
| ISS-07 | File trong ZIP chưa giới hạn PDF/ảnh (rule 3 chỉ áp dụng upload thường) | Thấp | Có thể có file sai định dạng | Xác nhận nghiệp vụ; nếu cần lọc & báo file sai định dạng | Nghiệp vụ |
| ISS-08 | Trang upload công khai: không giới hạn tần suất, token không hết hạn | Trung bình | Lộ link + biết SĐT có thể upload thay | Thêm hạn link, rate limit, captcha; dùng "Tạo lại link upload" khi lộ | Kỹ thuật |
| ISS-09 | Nhân viên có quyền xoá CTV; chưa chặn 1 user nhiều role | Thấp | Xoá nhầm dữ liệu | Xác nhận với quản lý; có thể bỏ perm_unlink | Quản lý |
| ISS-10 | Tải ZIP truyền ids qua URL GET | Thấp | Chọn quá nhiều CTV có thể vượt độ dài URL | Chuyển sang POST/wizard khi cần | Kỹ thuật |
| ISS-11 | Ký hàng loạt gửi toàn bộ PDF base64 trong 1 RPC | Trung bình | Lô lớn (hàng trăm) có thể chậm/timeout | Chia lô (ví dụ 20 hợp đồng/lần) trong JS | Kỹ thuật |
| ISS-12 | Đục lỗ trên trang PDF bị xoay (/Rotate) chưa test | Thấp | Chữ có thể sai hướng | Test với PDF xoay; xử lý xoay trong overlay | Kỹ thuật |
| ISS-13 | Tên file tiếng Việt trong ZIP tạo trên Windows có thể lỗi font | Thấp | Tên hiển thị khó đọc (map vẫn đúng) | Đặt tên không dấu hoặc nén bằng 7-Zip | Người dùng |
| ISS-14 | File CTV upload trước khi có quy tắc SĐT_Tên vẫn giữ tên cũ | Thấp | Tên không đồng nhất | Viết script đổi tên hàng loạt nếu cần | Kỹ thuật |
| ISS-15 | Màn hình thiết kế mới test bằng mô phỏng sự kiện; màn hình hẹp chật | Thấp | Trải nghiệm kéo thả thật chưa xác nhận | Test bằng chuột thật; dùng màn hình ≥1280px | Kỹ thuật |
| ISS-16 | Bên B (CTV) chưa ký số, vẫn upload bản ký tay/scan | Trung bình | Hợp đồng chưa có chữ ký số 2 bên | Thêm provider kiểu server (VNPT SmartCA...) theo khung mở rộng | Nghiệp vụ |
| ISS-17 | Chưa có test tự động (odoo tests) | Trung bình | Khó phát hiện lỗi hồi quy | Viết TransactionCase cho đục lỗ, map ZIP, ký số (mock), controller | Kỹ thuật |
| ISS-18 | Bản hợp đồng cũ đã gửi mail không bao giờ bị xoá | Thấp | Filestore tăng dần | Theo dõi; có thể thêm cron lưu trữ | Kỹ thuật |
| ISS-19 | Trường chọn đục lỗ lưu tên field; đổi/xoá field CTV sau này sẽ làm dòng cấu hình mất tác dụng | Thấp | Ô đục lỗ để trống | Kiểm tra cấu hình template sau khi đổi field | Kỹ thuật |
| ISS-20 | DB thử nghiệm th_collaborator_test vẫn tồn tại trên PostgreSQL local | Thấp | Chiếm dung lượng | Xoá khi không còn dùng | Kỹ thuật |
