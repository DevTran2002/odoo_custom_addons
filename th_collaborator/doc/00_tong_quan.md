# 00. Tổng quan dự án TH Collaborator

> **Dự án:** TH Collaborator - Quản lý cộng tác viên & hợp đồng  
> **Module:** th_collaborator (16.0.1.3.0), th_collaborator_sign_vnpt (16.0.1.0.0)  
> **Nền tảng:** Odoo 16 (Community/Enterprise), Python 3.10, PostgreSQL  
> **Cập nhật:** 18/10/2026 · **Tác giả:** Sonbn

## 1. Tóm tắt

Quản lý CTV và hợp đồng trên Odoo 16: hồ sơ CTV, 2 kho hợp đồng, gửi mail từ người phụ trách, CTV tải hợp đồng qua link không cần đăng nhập (token + SĐT), xử lý file hàng loạt, template PDF đục lỗ thông tin (có màn hình thiết kế), tạo hợp đồng, ký số bên A bằng USB Token VNPT với khung mở rộng cho nhà cung cấp khác.

![Sơ đồ tổng quan](images/so_do_tong_quan.png)

## 2. Số liệu chính

| Chỉ số | Giá trị |
|---|---|
| Yêu cầu nghiệp vụ | 16 |
| Yêu cầu chức năng | 22 (hoàn thành 22) |
| Model | 6 |
| Route HTTP | 4 |
| Kịch bản kiểm thử | 25 (đạt 14, chưa test 11) |
| Vấn đề tồn đọng | 20 (cao 2, trung bình 7, thấp 11) |

## 3. Bộ tài liệu

| Tài liệu | Nội dung |
|---|---|
| [01_thiet_ke_he_thong.md](01_thiet_ke_he_thong.md) | Kiến trúc, sơ đồ, mô hình dữ liệu, luồng xử lý, bảo mật, mở rộng |
| [02_yeu_cau_nghiep_vu_chuc_nang.md](02_yeu_cau_nghiep_vu_chuc_nang.md) | BR, FR, NFR, ma trận truy vết |
| [03_huong_dan_su_dung_kiem_thu.md](03_huong_dan_su_dung_kiem_thu.md) | Hướng dẫn từng chức năng + kịch bản kiểm thử |
| [04_bao_tri_ton_dong.md](04_bao_tri_ton_dong.md) | Bảo trì, vận hành, vấn đề tồn đọng |
| [TH_Collaborator_Tai_lieu_tong_hop.xlsx](TH_Collaborator_Tai_lieu_tong_hop.xlsx) | Toàn bộ nội dung trên trong 1 file Excel |

## 4. Các giai đoạn đã thực hiện

| Giai đoạn | Nội dung |
|---|---|
| 1 | Module CTV: thông tin, 2 kho hợp đồng, gửi mail, link upload công khai, upload/tải hàng loạt |
| 2 | Bổ sung rule: xác nhận gửi lại, chọn hình thức upload, PDF/ảnh, mail người phụ trách, lọc CTV của tôi, 1 quyền |
| 3 | Điều kiện gửi mail, icon, 2 nút tải ZIP 1 cấp thư mục, đặt tên SĐT_Tên, tên & loại hợp đồng |
| 4 | Template PDF có ô form: đục lỗ tiếng Việt, preview, mẫu email, đính kèm hợp đồng |
| 5 | Cấu hình đục lỗ chọn trường; màn hình thiết kế vẽ ô trên PDF không có ô form |
| 6 | Nút Tạo hợp đồng lưu vào Hợp đồng công ty |
| 7 | Ký số bên A: khung đa nhà cung cấp + module VNPT-CA Plugin (USB Token), ký lẻ & hàng loạt |

## 5. Việc cần làm tiếp (ưu tiên cao)

- **ISS-01** License VNPT-CA Plugin trong file mẫu là license TEST, hết hạn 30/10/2026 → Xin license chính thức theo domain Odoo, nhập vào Cấu hình ký số
- **ISS-02** Chưa ký thử với USB Token thật (mới test với plugin giả lập) → Chạy TC-20, TC-21 trên máy có token
