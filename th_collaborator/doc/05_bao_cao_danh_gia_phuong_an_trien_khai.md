# BÁO CÁO ĐÁNH GIÁ PHƯƠNG ÁN TRIỂN KHAI
## PHÂN HỆ QUẢN LÝ HỢP ĐỒNG CỘNG TÁC VIÊN VÀ KÝ SỐ

- Dự án: Phân hệ Quản lý Hợp đồng CTV
- Căn cứ quy trình: QT02 (Lập, ký và lưu trữ HĐ theo tài liệu AUM.BOF_10.2026_QUẢN LÝ HĐ & KÝ SỐ.ver5.xlsx)
- Đơn vị thẩm định: Đội ngũ phát triển hệ thống
- Ngày lập: 28/10/2026

---

### 1. Mục tiêu và bối cảnh

**Mục tiêu xây dựng phân hệ:**
Thu thập, tổng hợp dữ liệu nghiệm thu; gửi hàng loạt biên bản nghiệm thu để ký và tiếp nhận, lưu trữ các biên bản đã ký hoàn tất trên 1 hệ thống duy nhất.

**Bối cảnh lựa chọn phương án:**
Cần lựa chọn kiến trúc triển khai cho phân hệ:
- Phương án A: Tách thành một hệ thống riêng biệt.
- Phương án B: Gộp trực tiếp vào hệ thống B2B hiện tại.

Các yếu tố thực tế chi phối quyết định:
- Nhân viên phòng BOF thường gom khoảng 80 hợp đồng hoặc biên bản trong một lượt để tạo PDF, gửi mail và lưu trữ.
- Hệ thống B2B là cổng thông tin cho đối tác, có nhiệm vụ cốt lõi là tiếp nhận và đồng bộ liên tục dữ liệu cơ hội về các kho với Sambala Core.
- Giai đoạn 1 tập trung vào quy trình QT02 chưa bật ký số, giai đoạn 2 sẽ mở rộng tính năng ký số và quy trình nghiệm thu QT03.

---

### 2. Ưu và nhược điểm của hai phương án

#### 2.1. Phương án A: Tách thành Hệ thống riêng biệt (Khuyến nghị)

**Ưu điểm:**
- Bảo đảm luồng đồng bộ B2B: Thao tác tạo 80 file PDF và gửi email hàng loạt không chiếm dụng tài nguyên của B2B, luồng đồng bộ cơ hội về kho giữa B2B và Sambala Core luôn thông suốt.
- Quản lý tập trung toàn bộ vòng đời: Đáp ứng trọn vẹn mục tiêu thu thập dữ liệu nghiệm thu, gửi ký và lưu trữ toàn bộ hợp đồng, biên bản nghiệm thu đã ký trên một hệ thống duy nhất cho phòng BOF.
- Bảo mật thông tin nội bộ: Dữ liệu cá nhân nhạy cảm của CTV (CCCD, mã số thuế, số tài khoản ngân hàng, ảnh hồ sơ) được cô lập trong cơ sở dữ liệu riêng, chỉ nhân viên BOF truy cập, không có rủi ro lộ lọt sang các tài khoản đối tác trên B2B.
- Tách biệt lưu trữ: Hàng nghìn file PDF hợp đồng, biên bản nghiệm thu và ảnh hồ sơ không làm phình to filestore B2B, giúp việc sao lưu dữ liệu kinh doanh của B2B gọn nhẹ.
- Sẵn sàng mở rộng Ký số: Khi triển khai Phase 2, việc xử lý các gói dữ liệu Base64 lớn và kết nối USB Token/CA diễn ra độc lập, không gây rủi ro nghẽn mạng cho B2B.
- Thiết kế chuẩn mực: Phân hệ hợp đồng hiện chỉ phụ thuộc module mail, việc chạy độc lập rất sạch sẽ và không phát sinh nợ kỹ thuật.

**Nhược điểm:**
- Cần khởi tạo và duy trì thêm một instance/cơ sở dữ liệu độc lập.
- Cần thiết lập một webhook đơn giản nếu B2B cần nhận trạng thái hợp đồng để tính hoa hồng.

---

#### 2.2. Phương án B: Gộp trực tiếp vào hệ thống B2B

**Ưu điểm:**
- Tận dụng hạ tầng máy chủ hiện có, không cần khởi tạo instance mới.
- Dữ liệu nằm chung một hệ thống, không cần cấu hình liên kết hay webhook đồng bộ trạng thái.

**Nhược điểm:**
- Nguy cơ nghẽn luồng đồng bộ cơ hội: Việc xử lý đồng loạt 80 hợp đồng hoặc biên bản nghiệm thu tiêu tốn nhiều CPU và băng thông mạng, dễ làm chậm tiến trình tiếp nhận cơ hội và đồng bộ kho với Sambala Core.
- Rủi ro bảo mật dữ liệu: Dữ liệu CCCD, thuế và ngân hàng của CTV nằm chung hệ thống với các tài khoản đối tác bên ngoài, tăng rủi ro lộ lọt thông tin do phân quyền.
- Gánh nặng lưu trữ cho B2B: Dung lượng filestore tăng nhanh hàng chục Gigabyte, kéo dài thời gian sao lưu và phục hồi hệ thống B2B.
- Chi phí bóc tách lớn sau này: Nếu đưa vào B2B rồi mới tách ra ở giai đoạn Ký số, việc gỡ liên kết bảng và di chuyển hàng nghìn tệp đính kèm rất phức tạp và tốn kém.

---

### 3. Bảng so sánh tổng hợp

| Tiêu chí | Phương án A: Tách riêng (Khuyến nghị) | Phương án B: Gộp vào B2B |
|---|---|---|
| Tập trung quản lý HĐ và Nghiệm thu | Đạt mục tiêu: 1 hệ thống duy nhất quản lý toàn bộ HĐ, BBNT và ký số cho BOF. | Phân tán nghiệp vụ tài chính/nghiệm thu vào hệ thống bán hàng đối tác. |
| Đồng bộ cơ hội về kho B2B - Sambala | 100% không ảnh hưởng, chạy độc lập. | Rủi ro cao, dễ nghẽn khi BOF chạy đợt 80 hồ sơ. |
| Bảo mật thông tin (CCCD, Thuế, Ngân hàng) | Tuyệt đối an toàn trong cơ sở dữ liệu riêng. | Tiềm ẩn rủi ro lộ dữ liệu cho đối tác ngoài. |
| Tải khi xử lý lô 80 hồ sơ | Cách ly hoàn toàn trên máy chủ riêng. | Chiếm dụng CPU, RAM và mạng của B2B. |
| Lưu trữ và Sao lưu dữ liệu | Filestore độc lập, không ảnh hưởng B2B. | Làm phình to dung lượng sao lưu của B2B. |
| Mở rộng Ký số (Phase 2) | Thuận lợi, hạ tầng sẵn sàng cho dữ liệu lớn. | Khó khăn, dễ quá tải bộ nhớ và nghẽn RPC. |
| Chi phí kỹ thuật dài hạn | Thấp, cấu trúc module sạch ngay từ đầu. | Rất cao nếu sau này phải bóc tách dữ liệu. |
| Chi phí vận hành ban đầu | Cần thêm 1 instance/cơ sở dữ liệu. | Tận dụng hạ tầng hiện tại. |

---

### 4. Đề xuất kết luận

**Kiến nghị lựa chọn: Phương án A (Tách thành Hệ thống riêng biệt).**

Lộ trình thực hiện:
- **Giai đoạn 1 (QT02):** Thiết lập một instance Odoo độc lập cho phòng BOF, bổ sung các trường thông tin theo biểu mẫu BM1, BM4, cập nhật trạng thái hồ sơ và mẫu email BM3.
- **Giai đoạn 2 (Ký số & Nghiệm thu):** Bật tính năng ký số USB Token VNPT trên hệ thống riêng, mở rộng quy trình nghiệm thu QT03 (lập và ký BBNT hàng loạt), cấu hình webhook cập nhật trạng thái sang B2B khi hoàn tất.
