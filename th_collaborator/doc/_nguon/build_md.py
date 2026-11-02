# -*- coding: utf-8 -*-
"""Sinh 5 tài liệu Markdown từ content.py."""
import os
import sys
from collections import Counter

import content as c

OUT = sys.argv[1]


def table(headers, rows):
    def esc(value):
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    lines = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|']
    lines += ['| ' + ' | '.join(esc(v) for v in row) + ' |' for row in rows]
    return '\n'.join(lines)


def header(title):
    p = c.PROJECT
    return (f'# {title}\n\n'
            f'> **Dự án:** {p["name"]}  \n> **Module:** {p["modules"]}  \n'
            f'> **Nền tảng:** {p["platform"]}  \n> **Cập nhật:** {p["date"]} · **Tác giả:** {p["author"]}\n\n')


def write(name, text):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text.rstrip() + '\n')


MERMAID_ARCH = '''```mermaid
flowchart LR
    subgraph U[Người dùng]
        NV[Nhân viên / Bên A]
        CTV["Cộng tác viên<br/>không đăng nhập"]
        QT[Quản trị hệ thống]
    end
    subgraph CORE[Odoo 16 · th_collaborator]
        UI[Form/List CTV, Template,<br/>Cấu hình ký số, Wizard]
        DES[Màn hình thiết kế OWL<br/>pdf.js]
        SIGN[Action ký số OWL<br/>signProviderRegistry]
        PRO[(th.collaborator.profile)]
        TPL[(contract.template + line<br/>đục lỗ PDF)]
        CFG[(sign.config)]
        PUB["Controller công khai<br/>upload theo token"]
        INT["Controller nội bộ<br/>preview, ZIP"]
    end
    subgraph EXT[Thành phần ngoài]
        VN[th_collaborator_sign_vnpt<br/>vnpt-plugin.js]
        TOKEN[VNPT-CA Plugin<br/>+ USB Token]
        SMTP[Máy chủ mail]
        DB[(PostgreSQL + Filestore)]
    end
    NV --> UI --> PRO
    NV --> DES --> TPL
    NV --> SIGN --> CFG
    CTV -->|link + SĐT| PUB --> PRO
    QT --> CFG
    PRO <--> TPL
    PRO --> INT
    SIGN -->|registry| VN
    VN <-->|wss localhost| TOKEN
    PRO -->|mail.template| SMTP
    PRO --> DB
```'''

MERMAID_ERD = '''```mermaid
erDiagram
    TH_COLLABORATOR_PROFILE }o--|| RES_USERS : "user_id (người phụ trách)"
    TH_COLLABORATOR_PROFILE }o--o{ TH_COLLABORATOR_CONTRACT_TYPE : "th_contract_type_ids"
    TH_COLLABORATOR_PROFILE }o--o{ IR_ATTACHMENT : "th_company_attachment_ids / th_self_attachment_ids"
    TH_COLLABORATOR_PROFILE }o--o| IR_ATTACHMENT : "th_filled_attachment_id"
    TH_COLLABORATOR_PROFILE }o--o| TH_COLLABORATOR_CONTRACT_TEMPLATE : "th_contract_template_id"
    TH_COLLABORATOR_CONTRACT_TEMPLATE ||--o{ TH_COLLABORATOR_CONTRACT_TEMPLATE_LINE : "th_field_line_ids"
    TH_COLLABORATOR_CONTRACT_TEMPLATE }o--o| TH_COLLABORATOR_SIGN_CONFIG : "th_sign_config_id"
    TH_COLLABORATOR_CONTRACT_TEMPLATE }o--o| MAIL_TEMPLATE : "th_mail_template_id"
    TH_COLLABORATOR_CONTRACT_TEMPLATE }o--o{ TH_COLLABORATOR_CONTRACT_TYPE : "th_contract_type_ids"
    TH_COLLABORATOR_PROFILE {
        char name
        char th_email
        char th_phone_normalized UK
        char th_access_token UK
        selection state
        boolean th_is_signed
    }
    TH_COLLABORATOR_CONTRACT_TEMPLATE_LINE {
        char th_pdf_field_name
        selection th_field_name
        boolean th_is_manual
        boolean th_is_signature
        float th_pos_x_y_width_height
    }
    TH_COLLABORATOR_SIGN_CONFIG {
        selection th_provider
        selection th_appearance_type
        binary th_image
        text th_vnpt_license_key
    }
```'''

MERMAID_SEQ_UPLOAD = '''```mermaid
sequenceDiagram
    actor NV as Nhân viên
    participant O as Odoo (CTV)
    participant M as SMTP
    actor C as CTV
    participant P as Trang upload (token)
    NV->>O: Gửi mail hợp đồng (xác nhận nếu gửi lại)
    O->>O: Kiểm tra email, HĐ công ty/template, đã ký (nếu yêu cầu)
    O->>M: mail.template · From = người phụ trách · kèm Hợp đồng công ty
    M-->>C: "Xin chào <Tên>" + link upload
    C->>P: Mở link (token)
    C->>P: Nhập SĐT + chọn file (POST, CSRF)
    P->>P: SĐT khớp? ≤10 file, ≤20MB, PDF/ảnh (nội dung)
    P->>O: sudo: lưu file đổi tên SĐT_Tên, state = uploaded, chatter
    P-->>C: "Đã nhận N file"
```'''

MERMAID_SEQ_FILL = '''```mermaid
sequenceDiagram
    actor NV as Nhân viên
    participant T as Template
    participant D as Màn hình thiết kế (pdf.js)
    participant R as _render_filled_pdf
    participant P as CTV
    NV->>T: Upload PDF → đọc ô form → sinh dòng cấu hình
    NV->>D: Vẽ ô / ô chữ ký, chọn trường → th_save_designer_boxes
    NV->>P: Xem trước → route preview (không lưu)
    NV->>P: Tạo hợp đồng
    P->>R: Giá trị theo cấu hình (format ngày/selection/tag)
    R->>R: reportlab vẽ chữ Unicode tại toạ độ, thu nhỏ vừa ô, bỏ widget đã điền, mergePage
    R-->>P: PDF → Hợp đồng công ty (thay bản cũ, reset ký)
```'''

MERMAID_SEQ_SIGN = '''```mermaid
sequenceDiagram
    actor A as Bên A (USB Token)
    participant L as List/Form CTV
    participant J as Action ký số (JS)
    participant V as Provider vnpt_plugin
    participant K as VNPT-CA Plugin
    participant S as Server Odoo
    A->>L: Ký số bên A / Ký số hàng loạt
    L->>S: th_action_sign_contract(_batch) → _check_can_sign
    S-->>J: client action th_collaborator.sign_contracts
    J->>S: th_get_sign_payloads (PDF base64, ô ký, tuỳ chọn)
    J->>V: sign(items, options) theo từng cấu hình
    V->>K: checkPlugin · setLicenseKey · getCertInfo
    V->>K: signArrDataAdvanced([PdfSigner...]) – nhập PIN 1 lần
    K-->>V: PDF đã ký (base64)
    V-->>J: signed_pdf_base64 + cert_base64
    J->>S: th_save_signed_contracts → kiểm tra /ByteRange, lưu _da_ky.pdf, vết chứng thư
    J-->>L: act_window_close → tải lại dữ liệu
```'''


def doc_design():
    t = header('01. Thiết kế hệ thống TH Collaborator')
    t += '## 1. Mục đích & phạm vi\n\nHệ thống quản lý cộng tác viên (CTV) và vòng đời hợp đồng trên Odoo 16: lưu hồ sơ CTV, soạn hợp đồng tự động từ template PDF (đục lỗ), bên A ký số bằng USB Token, gửi mail cho CTV, CTV không đăng nhập vẫn tải hợp đồng đã ký lên, xử lý file hàng loạt.\n\n'
    t += '## 2. Sơ đồ tổng quan\n\n![Sơ đồ tổng quan](images/so_do_tong_quan.png)\n\n' + MERMAID_ARCH + '\n\n'
    t += '## 3. Kiến trúc 2 module\n\n' + table(['Module', 'Vai trò', 'Phụ thuộc'], [
        ('th_collaborator', 'Lõi nghiệp vụ + khung ký số độc lập nhà cung cấp', 'mail'),
        ('th_collaborator_sign_vnpt', 'Nhà cung cấp ký số VNPT-CA Plugin (USB Token)', 'th_collaborator'),
    ]) + '\n\n'
    t += '## 4. Thành phần\n\n' + table(['Thành phần', 'Loại', 'File chính', 'Trách nhiệm'], c.COMPONENTS) + '\n\n'
    t += '## 5. Mô hình dữ liệu\n\n' + MERMAID_ERD + '\n\n'
    for model, desc, fields in c.MODELS:
        t += f'### `{model}` – {desc}\n\n' + table(['Trường', 'Kiểu', 'Ý nghĩa'], fields) + '\n\n'
    t += '## 6. Luồng xử lý chính\n\n### 6.1 Gửi mail & CTV tải hợp đồng\n\n' + MERMAID_SEQ_UPLOAD
    t += '\n\n### 6.2 Template & đục lỗ hợp đồng\n\n' + MERMAID_SEQ_FILL
    t += '\n\n### 6.3 Ký số bên A\n\n' + MERMAID_SEQ_SIGN + '\n\n'
    t += '![Quy trình nghiệp vụ](images/so_do_quy_trinh.png)\n\n'
    t += '## 7. Giao tiếp HTTP\n\n' + table(['Route', 'Auth', 'Method', 'Mô tả'], c.ROUTES) + '\n\n'
    t += '## 8. Bảo mật & phân quyền\n\n' + table(['Hạng mục', 'Thiết kế', 'Ghi chú'], c.SECURITY) + '\n\n'
    t += '## 9. Thiết kế đục lỗ PDF\n\n'
    t += ('- Toạ độ lưu theo **hệ PDF** (point, gốc dưới-trái); màn hình thiết kế đổi qua lại bằng `viewport.convertToPdfPoint` / `convertToViewportRectangle` (pdf.js 2.2.228) nên đúng với trang lệch gốc.\n'
          '- Không điền vào ô form mà **vẽ chữ** bằng reportlab với font Unicode (DejaVu/Noto/Liberation/Arial hoặc `th_collaborator.pdf_font_path`), rồi bỏ widget đã điền → tiếng Việt đúng trên mọi trình đọc, CTV không sửa được.\n'
          '- Chữ dài tự thu nhỏ (tối thiểu 5pt); cỡ chữ lấy từ `/DA` của ô form hoặc cấu hình ô vẽ tay (0 = 70% chiều cao, tối đa 11pt).\n'
          '- Danh sách trường chọn là **Selection động** (không dùng Many2one `ir.model.fields` vì nhân viên không có quyền đọc model này).\n\n')
    t += '## 10. Mở rộng nhà cung cấp ký số\n\n' + '\n'.join(f'{i}. {s}' for i, s in enumerate(c.EXTENSION_STEPS, 1)) + '\n'
    write('01_thiet_ke_he_thong.md', t)


def doc_requirements():
    t = header('02. Yêu cầu nghiệp vụ & yêu cầu chức năng')
    t += '## 1. Yêu cầu nghiệp vụ (BR)\n\n' + table(['ID', 'Yêu cầu', 'Mục tiêu', 'Ưu tiên'], c.BUSINESS_REQS) + '\n\n'
    t += '## 2. Yêu cầu chức năng (FR)\n\n' + table(['ID', 'Chức năng', 'Mô tả / tiêu chí chấp nhận', 'BR', 'Trạng thái'], c.FUNC_REQS) + '\n\n'
    t += '## 3. Yêu cầu phi chức năng (NFR)\n\n' + table(['ID', 'Nhóm', 'Yêu cầu'], c.NON_FUNC_REQS) + '\n\n'
    t += '## 4. Ma trận truy vết BR → FR\n\n'
    rows = []
    for br in c.BUSINESS_REQS:
        frs = [fr[0] for fr in c.FUNC_REQS if br[0] in fr[3]]
        rows.append((br[0], br[1][:70] + ('…' if len(br[1]) > 70 else ''), ', '.join(frs) or '(quy tắc chung – NFR-05)'))
    t += table(['BR', 'Yêu cầu', 'Chức năng đáp ứng'], rows) + '\n'
    write('02_yeu_cau_nghiep_vu_chuc_nang.md', t)


def doc_guide_tests():
    t = header('03. Hướng dẫn sử dụng & kịch bản kiểm thử')
    t += '## Phần A – Hướng dẫn sử dụng\n\n![Quy trình](images/so_do_quy_trinh.png)\n\n'
    for i, (section, steps) in enumerate(c.USER_GUIDE, 1):
        t += f'### A{i}. {section}\n\n' + '\n'.join(f'{j}. {s}' for j, s in enumerate(steps, 1)) + '\n\n'
    stat = Counter('Đạt' if tc[6].startswith('Đạt') else 'Chưa test' for tc in c.TEST_CASES)
    t += f'## Phần B – Kịch bản kiểm thử\n\nTổng {len(c.TEST_CASES)} kịch bản · **Đạt: {stat["Đạt"]}** · **Chưa test: {stat["Chưa test"]}**. '
    t += 'Môi trường đã test: DB riêng `th_collaborator_test`, Odoo 16 local cổng 8099; ký số dùng plugin giả lập (chưa có USB Token).\n\n'
    t += table(['ID', 'FR', 'Điều kiện', 'Các bước', 'Kết quả mong đợi', 'Kết quả thực tế', 'Trạng thái'], c.TEST_CASES) + '\n'
    write('03_huong_dan_su_dung_kiem_thu.md', t)


def doc_maintenance():
    t = header('04. Bảo trì & vấn đề tồn đọng')
    t += '## 1. Hướng dẫn bảo trì\n\n' + table(['Hạng mục', 'Nội dung'], c.MAINTENANCE) + '\n\n'
    t += '### Lệnh thường dùng\n\n```bash\n# Nâng cấp module\nodoo-bin -c odoo.conf -d <db> -u th_collaborator,th_collaborator_sign_vnpt\n# Cài font tiếng Việt (Linux)\nsudo apt install fonts-dejavu-core\n```\n\n'
    t += '### Quy trình tiếp nhận lỗi quyền (theo quy tắc đội)\n\n1. Kiểm tra role được cấp cho user.\n2. Tìm group bị báo lỗi (`th_access_collaborator_user`) và ACL tương ứng.\n3. Xác định view/field/menu dùng group đó.\n\n'
    sev = Counter(i[2] for i in c.OPEN_ISSUES)
    t += f'## 2. Vấn đề tồn đọng\n\nTổng {len(c.OPEN_ISSUES)} vấn đề · Cao: {sev["Cao"]} · Trung bình: {sev["Trung bình"]} · Thấp: {sev["Thấp"]}\n\n'
    t += table(['ID', 'Vấn đề', 'Mức độ', 'Ảnh hưởng', 'Đề xuất', 'Phụ trách'], c.OPEN_ISSUES) + '\n'
    write('04_bao_tri_ton_dong.md', t)


def doc_overview():
    t = header('00. Tổng quan dự án TH Collaborator')
    stat = Counter('Đạt' if tc[6].startswith('Đạt') else 'Chưa test' for tc in c.TEST_CASES)
    sev = Counter(i[2] for i in c.OPEN_ISSUES)
    t += '## 1. Tóm tắt\n\nQuản lý CTV và hợp đồng trên Odoo 16: hồ sơ CTV, 2 kho hợp đồng, gửi mail từ người phụ trách, CTV tải hợp đồng qua link không cần đăng nhập (token + SĐT), xử lý file hàng loạt, template PDF đục lỗ thông tin (có màn hình thiết kế), tạo hợp đồng, ký số bên A bằng USB Token VNPT với khung mở rộng cho nhà cung cấp khác.\n\n'
    t += '![Sơ đồ tổng quan](images/so_do_tong_quan.png)\n\n'
    t += '## 2. Số liệu chính\n\n' + table(['Chỉ số', 'Giá trị'], [
        ('Yêu cầu nghiệp vụ', len(c.BUSINESS_REQS)),
        ('Yêu cầu chức năng', f'{len(c.FUNC_REQS)} (hoàn thành {sum(1 for f in c.FUNC_REQS if f[4].startswith("Hoàn thành"))})'),
        ('Model', len(c.MODELS)), ('Route HTTP', len(c.ROUTES)),
        ('Kịch bản kiểm thử', f'{len(c.TEST_CASES)} (đạt {stat["Đạt"]}, chưa test {stat["Chưa test"]})'),
        ('Vấn đề tồn đọng', f'{len(c.OPEN_ISSUES)} (cao {sev["Cao"]}, trung bình {sev["Trung bình"]}, thấp {sev["Thấp"]})'),
    ]) + '\n\n'
    t += '## 3. Bộ tài liệu\n\n' + table(['Tài liệu', 'Nội dung'], [
        ('[01_thiet_ke_he_thong.md](01_thiet_ke_he_thong.md)', 'Kiến trúc, sơ đồ, mô hình dữ liệu, luồng xử lý, bảo mật, mở rộng'),
        ('[02_yeu_cau_nghiep_vu_chuc_nang.md](02_yeu_cau_nghiep_vu_chuc_nang.md)', 'BR, FR, NFR, ma trận truy vết'),
        ('[03_huong_dan_su_dung_kiem_thu.md](03_huong_dan_su_dung_kiem_thu.md)', 'Hướng dẫn từng chức năng + kịch bản kiểm thử'),
        ('[04_bao_tri_ton_dong.md](04_bao_tri_ton_dong.md)', 'Bảo trì, vận hành, vấn đề tồn đọng'),
        ('[TH_Collaborator_Tai_lieu_tong_hop.xlsx](TH_Collaborator_Tai_lieu_tong_hop.xlsx)', 'Toàn bộ nội dung trên trong 1 file Excel'),
    ]) + '\n\n'
    t += '## 4. Các giai đoạn đã thực hiện\n\n' + table(['Giai đoạn', 'Nội dung'], c.TIMELINE) + '\n\n'
    t += '## 5. Việc cần làm tiếp (ưu tiên cao)\n\n' + '\n'.join(
        f'- **{i[0]}** {i[1]} → {i[4]}' for i in c.OPEN_ISSUES if i[2] == 'Cao') + '\n'
    write('00_tong_quan.md', t)


if __name__ == '__main__':
    doc_overview(); doc_design(); doc_requirements(); doc_guide_tests(); doc_maintenance()
    print(sorted(os.listdir(OUT)))
