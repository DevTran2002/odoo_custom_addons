# -*- coding: utf-8 -*-
"""Nội dung tài liệu dự án TH Collaborator - nguồn chung để sinh Markdown + Excel."""

PROJECT = {
    'name': 'TH Collaborator - Quản lý cộng tác viên & hợp đồng',
    'modules': 'th_collaborator (16.0.1.3.0), th_collaborator_sign_vnpt (16.0.1.0.0)',
    'platform': 'Odoo 16 (Community/Enterprise), Python 3.10, PostgreSQL',
    'path': r'D:\work\odoo-16.0\Owl-odoo',
    'author': 'Sonbn',
    'date': '18/10/2026',
}

# ---------------------------------------------------------------------------
# 1. THIẾT KẾ HỆ THỐNG
# ---------------------------------------------------------------------------
COMPONENTS = [
    # (Thành phần, Loại, File chính, Trách nhiệm)
    ('Hồ sơ CTV', 'Model', 'models/th_collaborator_profile.py',
     'Lưu thông tin CTV, 2 kho hợp đồng, gửi mail, tạo hợp đồng từ template, ký số bên A, tải ZIP'),
    ('Loại hợp đồng', 'Model', 'models/th_collaborator_contract_type.py',
     'Danh mục loại hợp đồng dạng tag có màu, cấu hình được'),
    ('Template hợp đồng', 'Model', 'models/th_collaborator_contract_template.py',
     'Lưu PDF mẫu, đọc ô form, đục lỗ (vẽ chữ Unicode + flatten), dữ liệu màn hình thiết kế, ô chữ ký'),
    ('Dòng cấu hình đục lỗ', 'Model', 'models/th_collaborator_contract_template_line.py',
     'Map ô form/ô vẽ tay -> trường CTV; toạ độ ô vẽ tay; ô chữ ký bên A; định dạng giá trị'),
    ('Cấu hình ký số', 'Model', 'models/th_collaborator_sign_config.py',
     'Khung ký số độc lập nhà cung cấp: kiểu hiển thị, ảnh, tuỳ chọn; hook cho module nhà cung cấp'),
    ('Wizard tải hàng loạt', 'TransientModel', 'wizard/th_collaborator_upload_wizard.py',
     'Upload nhiều file / ZIP, tự map file vào CTV theo SĐT trong tên file/thư mục'),
    ('Controller', 'HTTP', 'controllers/th_main.py',
     'Trang upload công khai cho CTV, preview PDF đục lỗ, tải ZIP hợp đồng'),
    ('Màn hình thiết kế ô đục lỗ', 'OWL client action', 'static/src/js/th_contract_template_designer.js',
     'Render PDF bằng pdf.js, vẽ/di chuyển/đổi kích thước ô, chọn trường, ô chữ ký'),
    ('Action ký số', 'OWL client action (function)', 'static/src/js/th_contract_sign_action.js',
     'Registry nhà cung cấp ký số kiểu client; gom hợp đồng theo cấu hình, gọi provider, lưu kết quả'),
    ('Nhà cung cấp VNPT-CA Plugin', 'Module riêng', 'th_collaborator_sign_vnpt/*',
     'Selection_add th_provider, license key, map cấu hình -> PdfSigner, gọi vnpt-plugin.js (wss://localhost)'),
    ('Mẫu email', 'Data', 'data/th_collaborator_mail_template_data.xml',
     'Mail mời CTV: "Xin chào {tên}", link upload; người gửi = người phụ trách'),
    ('Phân quyền', 'Security', 'security/*',
     '1 role "Nhân viên quản lý CTV" -> 1 access group giữ ACL'),
]

MODELS = [
    # (Model, Mô tả, [(field, kiểu, ý nghĩa)])
    ('th.collaborator.profile', 'Hồ sơ cộng tác viên (kế thừa mail.thread, mail.activity.mixin)', [
        ('name', 'Char', 'Họ và tên'),
        ('th_email', 'Char', 'Email CTV (kiểm tra định dạng)'),
        ('th_phone', 'Char', 'Số điện thoại'),
        ('th_phone_normalized', 'Char (compute, store, unique)', 'SĐT chuẩn hoá 0xxxxxxxxx – khoá map file/xác thực'),
        ('user_id', 'Many2one res.users', 'Người phụ trách (mặc định người tạo) – email gửi đi'),
        ('state', 'Selection', 'Mới / Đã gửi mail / CTV đã tải hợp đồng'),
        ('th_contract_name', 'Char', 'Tên hợp đồng'),
        ('th_contract_type_ids', 'Many2many', 'Loại hợp đồng (tag)'),
        ('th_company_attachment_ids', 'Many2many ir.attachment', 'Hợp đồng công ty (gửi kèm mail)'),
        ('th_self_attachment_ids', 'Many2many ir.attachment', 'Hợp đồng CTV tự tải lên'),
        ('th_access_token', 'Char (unique)', 'Token ngẫu nhiên của link upload công khai'),
        ('th_upload_url', 'Char (compute)', 'Link upload gửi trong mail'),
        ('th_mail_sent_date / th_last_upload_date', 'Datetime', 'Ngày gửi mail / ngày CTV tải lên'),
        ('th_contract_template_id', 'Many2one', 'Template hợp đồng dùng để đục lỗ'),
        ('th_filled_attachment_id', 'Many2one ir.attachment', 'Bản hợp đồng do hệ thống tạo (đục lỗ / đã ký) mới nhất'),
        ('th_sign_config_id', 'Many2one (related)', 'Cấu hình ký số của template'),
        ('th_is_signed / th_signed_date / th_signer_id / th_signer_cert_info', 'Bool/Datetime/M2o/Char',
         'Trạng thái và vết ký số bên A'),
    ]),
    ('th.collaborator.contract.type', 'Loại hợp đồng', [
        ('name', 'Char (unique)', 'Tên loại'), ('sequence', 'Integer', 'Thứ tự'),
        ('th_color', 'Integer', 'Màu tag'), ('active', 'Boolean', 'Đang sử dụng'),
    ]),
    ('th.collaborator.contract.template', 'Template hợp đồng PDF', [
        ('name', 'Char', 'Tên template'),
        ('th_template_file / th_template_filename', 'Binary / Char', 'File PDF mẫu (có hoặc không có ô form)'),
        ('th_detected_field_names', 'Char (compute, store)', 'Ô form đọc được từ PDF'),
        ('th_field_line_ids', 'One2many', 'Cấu hình đục lỗ'),
        ('th_mail_template_id', 'Many2one mail.template', 'Mẫu email gửi hợp đồng'),
        ('th_contract_type_ids', 'Many2many', 'Loại hợp đồng áp dụng'),
        ('th_sign_config_id', 'Many2one', 'Cấu hình ký số bên A'),
    ]),
    ('th.collaborator.contract.template.line', 'Dòng cấu hình đục lỗ', [
        ('th_pdf_field_name', 'Char (unique/template)', 'Tên ô form hoặc khoá manual_N của ô vẽ tay'),
        ('th_field_name', 'Selection động', 'Trường CTV được in vào ô'),
        ('th_is_manual', 'Boolean', 'Ô vẽ tay trên màn hình thiết kế'),
        ('th_is_signature', 'Boolean', 'Ô vị trí chữ ký số bên A'),
        ('th_page, th_pos_x, th_pos_y, th_width, th_height', 'Integer/Float', 'Trang + toạ độ PDF (point, gốc dưới-trái)'),
        ('th_font_size', 'Float', 'Cỡ chữ (0 = tự động)'),
    ]),
    ('th.collaborator.sign.config', 'Cấu hình ký số (độc lập nhà cung cấp)', [
        ('th_provider', 'Selection (mở rộng bằng selection_add)', 'Nhà cung cấp chữ ký số'),
        ('th_appearance_type', 'Selection', 'Chỉ mô tả / Mô tả + tên / Mô tả + ảnh / Chỉ ảnh / Ẩn'),
        ('th_image', 'Binary', 'Ảnh con dấu/chữ ký'),
        ('th_is_*_visible', 'Boolean', 'Hiện người ký / email / chức vụ / thời gian ký'),
        ('th_description, th_text_size, th_text_color', 'Text/Float/Char', 'Dòng mô tả ({thoi_gian}), cỡ, màu chữ'),
        ('th_is_initial_all_pages, th_tsa_url', 'Boolean/Char', 'Ký nháy mọi trang, dấu thời gian TSA'),
        ('th_vnpt_license_key', 'Text (module VNPT)', 'License key VNPT-CA Plugin'),
    ]),
    ('th.collaborator.upload.wizard', 'Wizard tải hợp đồng hàng loạt', [
        ('th_target_type', 'Selection', 'Hợp đồng công ty / Hợp đồng CTV'),
        ('th_upload_mode', 'Selection', 'Nhiều file (PDF/ảnh) / File ZIP'),
        ('th_attachment_ids / th_zip_file', 'Many2many / Binary', 'File upload'),
        ('th_result_note, th_is_done', 'Text / Boolean', 'Kết quả map'),
    ]),
]

ROUTES = [
    # (Route, auth, method, mô tả)
    ('/th_collaborator/upload/<token>', 'public', 'GET', 'Form upload hợp đồng cho CTV (không đăng nhập)'),
    ('/th_collaborator/upload/<token>/submit', 'public (CSRF)', 'POST',
     'Nhận file: xác thực token + SĐT, ≤10 file, ≤20MB/file, chỉ PDF/ảnh (kiểm tra nội dung)'),
    ('/th_collaborator/contract/preview/<profile|template>/<id>', 'user', 'GET',
     'Trả PDF đục lỗ inline, không lưu file (CTV: dữ liệu thật; template: nhãn trường)'),
    ('/th_collaborator/download_zip?contract_type=&ids=', 'user', 'GET',
     'ZIP hợp đồng công ty hoặc CTV, mỗi CTV 1 thư mục SĐT_Tên, stream qua file tạm'),
]

SECURITY = [
    ('Role group', 'th_role_collaborator_officer – "Nhân viên quản lý CTV"', 'Gán cho user; không ACL; kế thừa access group'),
    ('Access group', 'th_access_collaborator_user (ẩn)', 'Giữ toàn bộ ACL (đọc/ghi/tạo/xoá) cho 6 model'),
    ('Menu', 'Gắn group th_access_collaborator_user', 'Ẩn module với user không có quyền'),
    ('Trường M2x', 'no_create / no_create_edit', 'Không tạo nhanh từ ô chọn (theo quy tắc đội)'),
    ('sudo()', 'Chỉ 2 chỗ, có comment', 'Tra CTV theo token ở trang công khai; đọc ir.config_parameter font'),
    ('Trang công khai', 'Token 32 byte + SĐT', 'Phải khớp cả 2; CSRF; kiểm tra định dạng & dung lượng'),
    ('ir.attachment', 'res_model/res_id = CTV', 'Quyền xem file đi theo quyền bản ghi CTV'),
]

EXTENSION_STEPS = [
    'Tạo module mới th_collaborator_sign_<tên>, depends ["th_collaborator"].',
    'Kế thừa th.collaborator.sign.config: th_provider = fields.Selection(selection_add=[("<mã>", "<Tên>")], ondelete={"<mã>": "set null"}) + các trường cấu hình riêng.',
    'Override _get_provider_sign_mode(): trả "client" (ký trên trình duyệt qua plugin/USB Token) hoặc "server" (ký qua API).',
    'Kiểu client: override _get_client_sign_options() để thêm tuỳ chọn riêng; viết JS đăng ký signProviderRegistry.add("<mã>", { async sign(env, items, options) {...} }) trả [{signed_pdf_base64, cert_base64} | {error}].',
    'Kiểu server: override _sign_pdf_server(pdf_data, sign_box, page_count) trả {"signed_pdf": bytes, "cert_base64": str}.',
    'Kế thừa form th_collaborator_sign_config_form_view để hiện trường cấu hình riêng. Không cần sửa th_collaborator.',
]

# ---------------------------------------------------------------------------
# 2. YÊU CẦU NGHIỆP VỤ + CHỨC NĂNG
# ---------------------------------------------------------------------------
BUSINESS_REQS = [
    # (ID, Yêu cầu, Mục tiêu / lý do, Ưu tiên)
    ('BR-01', 'Quản lý thông tin CTV: họ tên, email, SĐT, người phụ trách, tên hợp đồng, loại hợp đồng', 'Một nơi tra cứu CTV', 'Cao'),
    ('BR-02', 'Lưu 2 loại hợp đồng: do công ty đẩy lên và do CTV tự đẩy lên', 'Tách bản công ty gửi / bản CTV ký', 'Cao'),
    ('BR-03', 'Gửi mail cho CTV tự map tên + email ("Xin chào <Tên>"), gửi bằng email người phụ trách', 'Giảm thao tác, đúng người liên hệ', 'Cao'),
    ('BR-04', 'CTV không đăng nhập vẫn tải được hợp đồng qua link trong mail, dùng SĐT để xác thực/map bản ghi', 'CTV không có tài khoản hệ thống', 'Cao'),
    ('BR-05', 'Đẩy và tải hợp đồng số lượng lớn cùng lúc', 'Xử lý hàng trăm CTV', 'Cao'),
    ('BR-06', 'Upload file thường chỉ nhận PDF hoặc ảnh', 'Chuẩn hoá hồ sơ', 'Trung bình'),
    ('BR-07', 'Hỏi xác nhận trước khi gửi lại mail; chỉ gửi khi có email và hợp đồng công ty/template', 'Tránh gửi trùng/thiếu', 'Trung bình'),
    ('BR-08', 'Có bộ lọc sẵn "CTV của tôi" theo người phụ trách', 'Nhân viên tập trung CTV mình phụ trách', 'Trung bình'),
    ('BR-09', 'Phân quyền đơn giản: chỉ 1 quyền nhân viên', 'Dễ vận hành', 'Trung bình'),
    ('BR-10', 'Hợp đồng CTV gửi lên được đặt tên chuẩn SĐT_Tên', 'Dễ tra cứu, lưu trữ', 'Trung bình'),
    ('BR-11', 'Tải template hợp đồng, đục lỗ thông tin CTV vào hợp đồng, xem trước, cấu hình mẫu email', 'Tự động hoá soạn hợp đồng', 'Cao'),
    ('BR-12', 'Chọn thông tin cần đục lỗ và gắn với trường mong muốn; vẽ ô trên PDF không có ô form', 'Dùng được mọi mẫu hợp đồng', 'Cao'),
    ('BR-13', 'Tạo hợp đồng từ template lưu vào Hợp đồng công ty', 'Kiểm soát bản gửi CTV', 'Cao'),
    ('BR-14', 'Bên A ký số hợp đồng bằng USB Token qua VNPT-CA Plugin, ký lẻ và ký hàng loạt', 'Hợp đồng có giá trị pháp lý điện tử', 'Cao'),
    ('BR-15', 'Có thể chuyển sang nhà cung cấp chữ ký số khác mà không viết lại hệ thống', 'Không phụ thuộc 1 nhà cung cấp', 'Cao'),
    ('BR-16', 'Tuân thủ quy tắc lập trình của đội (đặt tên th_, phân quyền role/access, logging, docstring...)', 'Chất lượng & bảo trì', 'Bắt buộc'),
]

FUNC_REQS = [
    # (ID, Chức năng, Mô tả chi tiết / tiêu chí chấp nhận, BR, Trạng thái)
    ('FR-01', 'Quản lý hồ sơ CTV', 'Form/list/search CTV; bắt buộc tên, SĐT, email, người phụ trách, tên hợp đồng trên view; email đúng định dạng; SĐT ≥9 số và không trùng (chuẩn hoá +84/0)', 'BR-01', 'Hoàn thành'),
    ('FR-02', 'Loại hợp đồng dạng tag', 'Menu Cấu hình > Loại hợp đồng; tag có màu, sắp xếp, lưu trữ; ô chọn trên CTV không cho tạo nhanh', 'BR-01', 'Hoàn thành'),
    ('FR-03', '2 kho hợp đồng', 'Tab Hợp đồng công ty / Hợp đồng CTV tải lên (many2many_binary, chỉ PDF/ảnh); file gắn res_model/res_id = CTV', 'BR-02', 'Hoàn thành'),
    ('FR-04', 'Gửi mail hợp đồng', 'Nút trên form (ẩn khi thiếu email hoặc thiếu HĐ công ty/template); nút gửi lại có xác nhận; nút gửi hàng loạt trên list có xác nhận; From/Reply-To = người phụ trách; đính kèm toàn bộ Hợp đồng công ty', 'BR-03, BR-07', 'Hoàn thành'),
    ('FR-05', 'Link upload công khai', 'Token ngẫu nhiên/CTV; CTV nhập SĐT đã đăng ký; ≤10 file, ≤20MB/file; PDF/ảnh kiểm tra nội dung thật; nút tạo lại link vô hiệu link cũ', 'BR-04, BR-06', 'Hoàn thành'),
    ('FR-06', 'Đặt tên hợp đồng CTV', 'File CTV gửi lên đổi tên SĐT_Tên.<đuôi>, các file sau SĐT_Tên_2, _3 (đếm tiếp theo số file đã có)', 'BR-10', 'Hoàn thành'),
    ('FR-07', 'Upload hàng loạt (wizard)', 'Chọn loại HĐ + hình thức (Nhiều file PDF/ảnh | ZIP); map theo SĐT ở đầu tên file hoặc tên thư mục; báo file không map được; giới hạn ZIP 2.000 file/1GB', 'BR-05', 'Hoàn thành'),
    ('FR-08', 'Tải ZIP hàng loạt', '2 nút: Tải HĐ công ty (ZIP), Tải HĐ CTV (ZIP); 1 cấp thư mục SĐT_Tên/; trùng tên thêm id', 'BR-05', 'Hoàn thành'),
    ('FR-09', 'Bộ lọc CTV của tôi', 'Action mặc định search_default_th_filter_my; nhóm theo trạng thái/người phụ trách/loại HĐ', 'BR-08', 'Hoàn thành'),
    ('FR-10', 'Phân quyền 1 role', 'Role "Nhân viên quản lý CTV" -> access group giữ ACL; menu theo group', 'BR-09, BR-16', 'Hoàn thành'),
    ('FR-11', 'Template hợp đồng PDF', 'Upload PDF (có/không ô form); nhận diện ô form; gắn mẫu email, loại HĐ, cấu hình ký số', 'BR-11', 'Hoàn thành'),
    ('FR-12', 'Cấu hình đục lỗ', 'Bảng ô form -> trường CTV (Selection động, gợi ý ten/email/sdt...); "Đọc lại ô form" giữ cấu hình cũ', 'BR-12', 'Hoàn thành'),
    ('FR-13', 'Màn hình thiết kế ô đục lỗ', 'Render PDF (pdf.js), kéo vẽ ô, di chuyển, đổi kích thước, Delete xoá, chọn trường + cỡ chữ, chuyển trang, lưu, xem thử', 'BR-12', 'Hoàn thành'),
    ('FR-14', 'Đục lỗ PDF tiếng Việt', 'Vẽ chữ bằng font Unicode tại toạ độ ô, tự thu nhỏ chữ cho vừa, flatten ô đã điền; định dạng ngày dd/mm/yyyy, selection, tag', 'BR-11', 'Hoàn thành'),
    ('FR-15', 'Xem trước hợp đồng', 'Trên CTV (dữ liệu thật) và template (nhãn trường); PDF inline, không lưu file', 'BR-11', 'Hoàn thành'),
    ('FR-16', 'Cấu hình mẫu email', 'Menu Cấu hình > Mẫu email hợp đồng (mail.template của CTV); mỗi template HĐ chọn 1 mẫu', 'BR-11', 'Hoàn thành'),
    ('FR-17', 'Tạo hợp đồng', 'Nút Tạo hợp đồng / Tạo lại hợp đồng (xác nhận) lưu vào Hợp đồng công ty; thay bản cũ, xoá bản cũ nếu chưa gửi mail; reset trạng thái ký', 'BR-13', 'Hoàn thành'),
    ('FR-18', 'Cấu hình ký số', 'Nhà cung cấp, kiểu hiển thị (5 kiểu), ảnh, bật/tắt thông tin, mô tả {thoi_gian}, cỡ/màu chữ, ký nháy, TSA', 'BR-14', 'Hoàn thành'),
    ('FR-19', 'Ô chữ ký bên A', 'Vẽ trên màn hình thiết kế, loại ô "Chữ ký số bên A", tối đa 1 ô/template', 'BR-14', 'Hoàn thành'),
    ('FR-20', 'Ký số lẻ & hàng loạt', 'Nút Ký số bên A (form) / Ký số hàng loạt (list); chọn chứng thư 1 lần, nhập PIN 1 lần/lô; lưu file _da_ky.pdf; vết người ký, thời gian, chứng thư', 'BR-14', 'Hoàn thành (chưa test token thật)'),
    ('FR-21', 'Ràng buộc sau ký', 'Chặn gửi mail khi template yêu cầu ký mà chưa ký; chặn ký lại; tạo lại hợp đồng thì bỏ chữ ký', 'BR-14', 'Hoàn thành'),
    ('FR-22', 'Khung đa nhà cung cấp ký số', 'Hook Python + registry JS; nhà cung cấp kiểu client/server; module VNPT là provider đầu tiên', 'BR-15', 'Hoàn thành'),
]

NON_FUNC_REQS = [
    ('NFR-01', 'Hiệu năng', 'Gửi nhiều mail không treo màn hình (khuyến nghị force_send=False); ZIP stream qua file tạm, đọc trực tiếp filestore; ký 1 lô 1 lần PIN'),
    ('NFR-02', 'Bảo mật', 'Token + SĐT, CSRF, kiểm tra nội dung file, chặn zip bomb, sudo có lý do, quyền file theo bản ghi'),
    ('NFR-03', 'Tiếng Việt', 'Font Unicode khi đục lỗ; giao diện & thông báo tiếng Việt'),
    ('NFR-04', 'Mở rộng', 'Thêm nhà cung cấp ký số bằng module riêng, không sửa lõi'),
    ('NFR-05', 'Tuân thủ quy tắc đội', 'Prefix th_, đặt tên XML ID th_<module>_<object>_<type>, _logger, docstring, không required/readonly trên field'),
]

# ---------------------------------------------------------------------------
# 3. HƯỚNG DẪN SỬ DỤNG + KỊCH BẢN KIỂM THỬ
# ---------------------------------------------------------------------------
USER_GUIDE = [
    # (Mục, Bước thực hiện)
    ('Cài đặt & phân quyền', [
        'Thêm thư mục D:\\work\\odoo-16.0\\Owl-odoo vào addons_path.',
        'Cài module "TH Collaborator"; nếu ký số VNPT cài thêm "TH Collaborator - Ký số VNPT-CA Plugin".',
        'Settings > Users: gán quyền "Nhân viên quản lý CTV" (nhóm Cộng tác viên) cho nhân viên.',
        'Đảm bảo user có email (dùng làm người gửi mail).',
    ]),
    ('Tạo CTV', [
        'Menu Cộng tác viên > Cộng tác viên > Mới.',
        'Nhập Tên hợp đồng, Họ tên, SĐT, Email, Người phụ trách, Loại hợp đồng, Template hợp đồng.',
        'Lưu. Link upload riêng của CTV hiện ở ô "Link upload hợp đồng" (có nút copy).',
        'Tạo hàng loạt: Favorites > Import records từ Excel (cột Họ tên, Email, SĐT...).',
    ]),
    ('Cấu hình loại hợp đồng & mẫu email', [
        'Cấu hình > Loại hợp đồng: thêm dòng, chọn màu.',
        'Cấu hình > Mẫu email hợp đồng: sửa tiêu đề/nội dung; dùng object.name, object.th_upload_url.',
    ]),
    ('Template hợp đồng & đục lỗ', [
        'Cấu hình > Template hợp đồng > Mới: nhập tên, upload PDF, chọn mẫu email, lưu.',
        'PDF có ô form: tab Cấu hình đục lỗ tự sinh dòng; chọn trường CTV cho từng ô.',
        'PDF không có ô form: bấm "Thiết kế ô đục lỗ", kéo chuột vẽ ô, chọn trường, chỉnh cỡ chữ, Lưu.',
        'Bấm "Xem thử với dữ liệu mẫu" để kiểm tra vị trí.',
    ]),
    ('Tạo hợp đồng & gửi mail', [
        'Trên CTV chọn Template hợp đồng > "Xem trước hợp đồng" (không lưu).',
        'Bấm "Tạo hợp đồng": file SĐT_Tên_<template>.pdf vào tab Hợp đồng công ty.',
        'Bấm "Gửi mail hợp đồng" (lần sau là "Gửi lại", có xác nhận). Mail gửi từ email người phụ trách, kèm Hợp đồng công ty.',
        'Gửi nhiều: chọn CTV trên danh sách > "Gửi mail hợp đồng".',
    ]),
    ('CTV tải hợp đồng lên', [
        'CTV mở link trong mail, nhập SĐT đã đăng ký, chọn tối đa 10 file PDF/ảnh (≤20MB/file), bấm Gửi.',
        'Hệ thống đổi tên SĐT_Tên.pdf, lưu vào tab Hợp đồng CTV tải lên, trạng thái "CTV đã tải hợp đồng", báo người phụ trách trên chatter.',
    ]),
    ('Tải lên / tải về hàng loạt', [
        'Menu Tải hợp đồng hàng loạt: chọn Loại hợp đồng + Hình thức (Nhiều file | ZIP).',
        'Đặt tên file 0912345678_hopdong.pdf hoặc ZIP có thư mục 0912345678/. SĐT không có dấu cách/gạch.',
        'Bấm Tải lên, xem kết quả và danh sách file không map được.',
        'Tải về: chọn CTV trên danh sách > "Tải HĐ công ty (ZIP)" hoặc "Tải HĐ CTV (ZIP)".',
    ]),
    ('Ký số bên A (VNPT USB Token)', [
        'Máy người ký: cài VNPT-CA Plugin, cắm USB Token.',
        'Cấu hình > Cấu hình ký số > Mới: Nhà cung cấp VNPT-CA Plugin, License key, kiểu hiển thị, ảnh con dấu, mô tả.',
        'Template hợp đồng: chọn Cấu hình ký số bên A; vào Thiết kế ô đục lỗ vẽ 1 ô, Loại ô = "Chữ ký số bên A", Lưu.',
        'CTV: Tạo hợp đồng > "Ký số bên A" > chọn chứng thư > nhập PIN. Hàng loạt: chọn nhiều CTV > "Ký số hàng loạt" (PIN 1 lần).',
        'File _da_ky.pdf thay bản chưa ký; sau đó mới gửi mail được.',
    ]),
]

TEST_CASES = [
    # (ID, Chức năng, Điều kiện, Bước, Kết quả mong đợi, Kết quả thực tế, Trạng thái)
    ('TC-01', 'FR-01', 'Đăng nhập nhân viên', 'Tạo CTV SĐT +84912345678; tạo CTV khác SĐT 0912345678', 'CTV 2 bị chặn: "Số điện thoại đã tồn tại"', '', 'Chưa test'),
    ('TC-02', 'FR-01', '', 'Nhập email "abc@"', 'Báo email không hợp lệ', '', 'Chưa test UI'),
    ('TC-03', 'FR-04', 'CTV chưa có email / chưa HĐ & template', 'Mở form CTV', 'Ẩn nút Gửi mail; gửi từ list báo lỗi kèm tên CTV', '', 'Chưa test'),
    ('TC-04', 'FR-04', 'CTV đã gửi mail', 'Bấm "Gửi lại mail hợp đồng"', 'Hiện hộp xác nhận', 'Nút có confirm', 'Đạt (view)'),
    ('TC-05', 'FR-04', 'Template có ký số, đã ký', 'Gửi mail', 'Mail From = người phụ trách, đính kèm bản _da_ky.pdf', 'Đính kèm đúng; mail exception do DB test không có SMTP', 'Đạt'),
    ('TC-06', 'FR-05', 'Có link upload', 'Mở link, nhập sai SĐT, gửi file', 'Báo SĐT không khớp, không lưu', '', 'Chưa test'),
    ('TC-07', 'FR-05/06', 'Có link upload', 'Nhập đúng SĐT, gửi 2 file PDF', 'Lưu SĐT_Tên.pdf, SĐT_Tên_2.pdf; trạng thái CTV đã tải', '', 'Chưa test'),
    ('TC-08', 'FR-05', '', 'Gửi file .docx đổi đuôi .pdf', 'Báo chỉ chấp nhận PDF/ảnh', '', 'Chưa test'),
    ('TC-09', 'FR-07', 'CTV có SĐT', 'Wizard ZIP chứa 0912345678/hd.pdf và abc.pdf', 'hd.pdf gắn đúng CTV; abc.pdf trong danh sách không map', '', 'Chưa test'),
    ('TC-10', 'FR-08', '2 CTV có HĐ', 'Tải HĐ công ty (ZIP)', 'ZIP có thư mục SĐT_Tên/ chứa file', '', 'Chưa test'),
    ('TC-11', 'FR-11', '', 'Upload PDF không có ô form', 'Lưu được, không lỗi', 'Lưu thành công', 'Đạt'),
    ('TC-12', 'FR-12', 'PDF có ô ten/email/sdt/chu_ky', 'Upload template', 'Sinh 4 dòng, gợi ý name/th_email/th_phone; chu_ky để trống', 'Nhận diện 4 ô', 'Đạt'),
    ('TC-13', 'FR-13', 'Template PDF', 'Vẽ 4 ô, di chuyển, đổi kích thước, Delete, vẽ lại, Lưu', 'Toạ độ PDF lưu đúng', 'Đúng (mô phỏng sự kiện chuột)', 'Đạt'),
    ('TC-14', 'FR-14/15', 'CTV tên "Nguyễn Thị Hồng Nhung"', 'Xem trước hợp đồng', 'Chữ đủ dấu, đúng dòng; ngày dd/mm/yyyy HH:MM', 'Hiển thị đúng', 'Đạt'),
    ('TC-15', 'FR-14', 'Ô nhỏ, tên dài', 'Xem trước', 'Chữ tự thu nhỏ vừa ô', 'Đúng', 'Đạt'),
    ('TC-16', 'FR-17', 'CTV có template', 'Tạo hợp đồng 2 lần', 'Bản lần 1 (chưa gửi mail) bị xoá; bản đã gửi mail được giữ', 'Đúng', 'Đạt'),
    ('TC-17', 'FR-17', 'Chưa chọn template', 'Tạo hợp đồng', 'Báo "chưa chọn template"', 'Đúng', 'Đạt'),
    ('TC-18', 'FR-19', 'Template', 'Vẽ ô, Loại ô = Chữ ký số bên A; đặt ô thứ 2 làm chữ ký', 'Ô viền xanh; ô cũ tự về ô thông tin; server chặn >1 ô', 'Hiển thị đúng', 'Đạt'),
    ('TC-19', 'FR-20', '2 CTV đã tạo HĐ, plugin giả lập', 'Chọn 2 CTV > Ký số hàng loạt', '1 lần signArrDataAdvanced (2 file); PdfSigner đúng trang/toạ độ/SigType/ảnh/mô tả; lưu _da_ky.pdf + chứng thư', 'Đúng; cert "CÔNG TY TNHH ABC (TEST) | Serial 54010101abcdef"', 'Đạt (plugin giả)'),
    ('TC-20', 'FR-20', 'USB Token thật + license chính thức', 'Ký 1 hợp đồng, mở bằng Adobe/Foxit', 'Chữ ký hợp lệ, hiển thị đúng kiểu cấu hình', '', 'Chưa test – cần token'),
    ('TC-21', 'FR-18', 'Token thật', 'Thử lần lượt 5 kiểu hiển thị, màu chữ, ký nháy', 'Hiển thị đúng từng kiểu', '', 'Chưa test – cần token'),
    ('TC-22', 'FR-21', 'Template có ký số, chưa ký', 'Gửi mail', 'Báo "chưa được bên A ký số"', 'Đúng', 'Đạt'),
    ('TC-23', 'FR-21', 'Đã ký', 'Ký lại / Tạo lại hợp đồng', 'Ký lại bị chặn; tạo lại thì is_signed = False', 'Đúng', 'Đạt'),
    ('TC-24', 'FR-22', 'Cài module VNPT', 'Mở Cấu hình ký số', 'Có lựa chọn VNPT-CA Plugin + ô license; registry JS có "vnpt_plugin"', 'Đúng', 'Đạt'),
    ('TC-25', 'FR-10', 'User không có role', 'Đăng nhập', 'Không thấy menu Cộng tác viên', '', 'Chưa test'),
]

# ---------------------------------------------------------------------------
# 4. BẢO TRÌ + TỒN ĐỌNG
# ---------------------------------------------------------------------------
MAINTENANCE = [
    # (Hạng mục, Nội dung)
    ('Cài đặt / nâng cấp', 'odoo-bin -c odoo.conf -d <db> -u th_collaborator,th_collaborator_sign_vnpt. Sửa Python cần restart; sửa view/field/data cần -u.'),
    ('addons_path', 'Phải chứa D:\\work\\odoo-16.0\\Owl-odoo (hiện odoo.conf chưa có).'),
    ('Font đục lỗ', 'Linux: apt install fonts-dejavu-core, hoặc tham số hệ thống th_collaborator.pdf_font_path = đường dẫn .ttf. Đổi font cần restart.'),
    ('Mail', 'Kiểm tra Settings > Technical > Emails (Outgoing/Exception). Cron "Mail: Email Queue Manager" phải chạy (max_cron_threads > 0). Email người phụ trách nên cùng domain SMTP (SPF/DMARC).'),
    ('Giới hạn upload', 'Trang CTV: TH_UPLOAD_MAX_FILES=10, TH_UPLOAD_MAX_FILE_SIZE=20MB (controllers/th_main.py). Wizard ZIP: 2.000 file/1GB. Nginx client_max_body_size, Odoo limit_request, limit_time_real.'),
    ('License VNPT', 'Cấu hình > Cấu hình ký số > License key. Gia hạn trước ngày hết hạn; key gắn domain.'),
    ('Mẫu email', 'Data noupdate=1: sửa trên giao diện, upgrade không ghi đè. Người gửi luôn bị ép = người phụ trách trong code.'),
    ('Thêm trường đục lỗ', 'Trường mới của CTV (char/text/date/selection/m2o/m2m...) tự xuất hiện trong danh sách chọn; loại trừ ở TH_EXCLUDED_FIELD_NAMES.'),
    ('Thêm nhà cung cấp ký số', 'Xem mục Mở rộng trong tài liệu thiết kế (module th_collaborator_sign_<tên>).'),
    ('Log', '_logger ghi: gửi mail, CTV upload, sai SĐT, import hàng loạt, tải ZIP, ký số, lưu ô thiết kế.'),
    ('Xử lý lỗi quyền', 'Kiểm tra user có role "Nhân viên quản lý CTV" -> group th_access_collaborator_user -> ACL ir.model.access.csv.'),
    ('Sao lưu', 'Sao lưu DB + filestore (hợp đồng là ir.attachment trong filestore).'),
    ('Dọn dẹp', 'Các bản hợp đồng cũ đã gửi mail được giữ (chatter tham chiếu) – theo dõi dung lượng filestore.'),
]

OPEN_ISSUES = [
    # (ID, Vấn đề, Mức độ, Ảnh hưởng, Đề xuất, Phụ trách)
    ('ISS-01', 'License VNPT-CA Plugin trong file mẫu là license TEST, hết hạn 30/10/2026', 'Cao', 'Hết hạn sẽ không ký được', 'Xin license chính thức theo domain Odoo, nhập vào Cấu hình ký số', 'Nghiệp vụ / VNPT'),
    ('ISS-02', 'Chưa ký thử với USB Token thật (mới test với plugin giả lập)', 'Cao', 'Rủi ro khác biệt định dạng kết quả plugin', 'Chạy TC-20, TC-21 trên máy có token', 'Kỹ thuật'),
    ('ISS-03', 'Chưa xác nhận: SigType=3 cho "Chỉ ảnh", định dạng SigColorRGB, PagesArray khi ký lô', 'Trung bình', 'Hiển thị chữ ký có thể sai', 'Ký thử từng kiểu, đối chiếu tài liệu VNPT', 'Kỹ thuật'),
    ('ISS-04', 'Server chỉ kiểm tra PDF có /ByteRange, không xác thực chuỗi chứng thư/CRL/OCSP', 'Trung bình', 'Không phát hiện chữ ký giả mạo nếu RPC bị can thiệp', 'Bổ sung xác thực (pyHanko/endesive) hoặc API kiểm tra của VNPT', 'Kỹ thuật'),
    ('ISS-05', 'force_send=True nhưng comment ghi False và thông báo list ghi "đưa vào hàng đợi"', 'Thấp', 'Gửi nhiều mail có thể treo request; thông báo sai', 'Form gửi ngay, list dùng hàng đợi (force_send theo tham số); sửa comment/thông báo', 'Kỹ thuật'),
    ('ISS-06', 'Gửi mail bằng email người phụ trách qua SMTP công ty', 'Trung bình', 'Mail có thể bị chặn/spam (SPF/DMARC)', 'Dùng email cùng domain hoặc cấu hình alias/mail.default.from', 'Hạ tầng'),
    ('ISS-07', 'File trong ZIP chưa giới hạn PDF/ảnh (rule 3 chỉ áp dụng upload thường)', 'Thấp', 'Có thể có file sai định dạng', 'Xác nhận nghiệp vụ; nếu cần lọc & báo file sai định dạng', 'Nghiệp vụ'),
    ('ISS-08', 'Trang upload công khai: không giới hạn tần suất, token không hết hạn', 'Trung bình', 'Lộ link + biết SĐT có thể upload thay', 'Thêm hạn link, rate limit, captcha; dùng "Tạo lại link upload" khi lộ', 'Kỹ thuật'),
    ('ISS-09', 'Nhân viên có quyền xoá CTV; chưa chặn 1 user nhiều role', 'Thấp', 'Xoá nhầm dữ liệu', 'Xác nhận với quản lý; có thể bỏ perm_unlink', 'Quản lý'),
    ('ISS-10', 'Tải ZIP truyền ids qua URL GET', 'Thấp', 'Chọn quá nhiều CTV có thể vượt độ dài URL', 'Chuyển sang POST/wizard khi cần', 'Kỹ thuật'),
    ('ISS-11', 'Ký hàng loạt gửi toàn bộ PDF base64 trong 1 RPC', 'Trung bình', 'Lô lớn (hàng trăm) có thể chậm/timeout', 'Chia lô (ví dụ 20 hợp đồng/lần) trong JS', 'Kỹ thuật'),
    ('ISS-12', 'Đục lỗ trên trang PDF bị xoay (/Rotate) chưa test', 'Thấp', 'Chữ có thể sai hướng', 'Test với PDF xoay; xử lý xoay trong overlay', 'Kỹ thuật'),
    ('ISS-13', 'Tên file tiếng Việt trong ZIP tạo trên Windows có thể lỗi font', 'Thấp', 'Tên hiển thị khó đọc (map vẫn đúng)', 'Đặt tên không dấu hoặc nén bằng 7-Zip', 'Người dùng'),
    ('ISS-14', 'File CTV upload trước khi có quy tắc SĐT_Tên vẫn giữ tên cũ', 'Thấp', 'Tên không đồng nhất', 'Viết script đổi tên hàng loạt nếu cần', 'Kỹ thuật'),
    ('ISS-15', 'Màn hình thiết kế mới test bằng mô phỏng sự kiện; màn hình hẹp chật', 'Thấp', 'Trải nghiệm kéo thả thật chưa xác nhận', 'Test bằng chuột thật; dùng màn hình ≥1280px', 'Kỹ thuật'),
    ('ISS-16', 'Bên B (CTV) chưa ký số, vẫn upload bản ký tay/scan', 'Trung bình', 'Hợp đồng chưa có chữ ký số 2 bên', 'Thêm provider kiểu server (VNPT SmartCA...) theo khung mở rộng', 'Nghiệp vụ'),
    ('ISS-17', 'Chưa có test tự động (odoo tests)', 'Trung bình', 'Khó phát hiện lỗi hồi quy', 'Viết TransactionCase cho đục lỗ, map ZIP, ký số (mock), controller', 'Kỹ thuật'),
    ('ISS-18', 'Bản hợp đồng cũ đã gửi mail không bao giờ bị xoá', 'Thấp', 'Filestore tăng dần', 'Theo dõi; có thể thêm cron lưu trữ', 'Kỹ thuật'),
    ('ISS-19', 'Trường chọn đục lỗ lưu tên field; đổi/xoá field CTV sau này sẽ làm dòng cấu hình mất tác dụng', 'Thấp', 'Ô đục lỗ để trống', 'Kiểm tra cấu hình template sau khi đổi field', 'Kỹ thuật'),
    ('ISS-20', 'DB thử nghiệm th_collaborator_test vẫn tồn tại trên PostgreSQL local', 'Thấp', 'Chiếm dung lượng', 'Xoá khi không còn dùng', 'Kỹ thuật'),
]

TIMELINE = [
    # (Giai đoạn, Nội dung)
    ('1', 'Module CTV: thông tin, 2 kho hợp đồng, gửi mail, link upload công khai, upload/tải hàng loạt'),
    ('2', 'Bổ sung rule: xác nhận gửi lại, chọn hình thức upload, PDF/ảnh, mail người phụ trách, lọc CTV của tôi, 1 quyền'),
    ('3', 'Điều kiện gửi mail, icon, 2 nút tải ZIP 1 cấp thư mục, đặt tên SĐT_Tên, tên & loại hợp đồng'),
    ('4', 'Template PDF có ô form: đục lỗ tiếng Việt, preview, mẫu email, đính kèm hợp đồng'),
    ('5', 'Cấu hình đục lỗ chọn trường; màn hình thiết kế vẽ ô trên PDF không có ô form'),
    ('6', 'Nút Tạo hợp đồng lưu vào Hợp đồng công ty'),
    ('7', 'Ký số bên A: khung đa nhà cung cấp + module VNPT-CA Plugin (USB Token), ký lẻ & hàng loạt'),
]
