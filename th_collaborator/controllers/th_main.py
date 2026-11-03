# -*- coding: utf-8 -*-
import logging
import os
import re

from odoo import _, http
from odoo.http import content_disposition, request

from odoo.addons.th_collaborator.models.th_collaborator_profile import TH_CONTRACT_ALLOWED_EXTENSIONS

_logger = logging.getLogger(__name__)

TH_UPLOAD_MAX_FILES = 10
TH_UPLOAD_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB / file


class ThCollaboratorController(http.Controller):

    def _get_contract_by_token(self, token):
        """Tìm Hợp đồng theo token của link upload (hỗ trợ tương thích ngược với token CTV cũ)."""
        Contract = request.env['th.collaborator.contract']
        if not token or len(token) < 20:
            return Contract.browse()
        # sudo: CTV truy cập cổng công khai không có phiên đăng nhập nhân viên nội bộ;
        # chỉ tra đúng 1 bản ghi hợp đồng theo token bảo mật ngẫu nhiên, không làm lộ các dữ liệu khác.
        contract = Contract.sudo().search([('th_access_token', '=', token)], limit=1)
        if not contract:
            # Hỗ trợ tương thích ngược: Tìm theo token cũ trên hồ sơ CTV nếu có link đã gửi trước đây
            Profile = request.env['th.collaborator.profile']
            profile = Profile.sudo().search([('th_access_token', '=', token)], limit=1)
            if profile:
                contract = profile.sudo().th_contract_ids.filtered(lambda c: c.state != 'cancel')[:1]
        return contract

    def _render_upload_page(self, values):
        """Render trang upload hợp đồng công khai."""
        values.update({
            'th_max_files': TH_UPLOAD_MAX_FILES,
            'th_max_file_size_mb': TH_UPLOAD_MAX_FILE_SIZE // (1024 * 1024),
            'th_accept': ','.join(TH_CONTRACT_ALLOWED_EXTENSIONS),
        })
        return request.render('th_collaborator.th_collaborator_upload_page_template', values)

    def _read_uploaded_files(self):
        """Đọc và kiểm tra file CTV gửi lên; trả về (danh sách file, lỗi)."""
        storages = [f for f in request.httprequest.files.getlist('th_contract_files') if f.filename]
        if not storages:
            return [], _('Vui lòng chọn ít nhất 1 file hợp đồng.')
        if len(storages) > TH_UPLOAD_MAX_FILES:
            return [], _('Chỉ được tải tối đa %s file mỗi lần.') % TH_UPLOAD_MAX_FILES
        Profile = request.env['th.collaborator.profile']
        files = []
        for storage in storages:
            file_name = os.path.basename(storage.filename)
            content = storage.read(TH_UPLOAD_MAX_FILE_SIZE + 1)
            if len(content) > TH_UPLOAD_MAX_FILE_SIZE:
                return [], _('File "%s" vượt quá dung lượng cho phép.') % file_name
            if not Profile._is_allowed_contract_file(file_name, content=content):
                return [], _('File "%s" không hợp lệ, chỉ chấp nhận PDF hoặc ảnh.') % file_name
            files.append((file_name, content))
        return files, False

    @http.route('/th_collaborator/upload/<string:token>', type='http', auth='public', website=True, methods=['GET'])
    def render_upload_form(self, token, **kwargs):
        """Hiển thị form portal để CTV tải hợp đồng lên theo từng hợp đồng bằng token bảo mật."""
        contract = self._get_contract_by_token(token)
        if not contract:
            return request.not_found()
        values = {
            'token': token,
            'contract': contract,
            'profile': contract.th_collaborator_id,
        }
        if contract.state in ('close', 'cancel'):
            values['error'] = _('Hợp đồng này đã hoàn tất hoặc đã hủy, cổng tiếp nhận tệp đã đóng.')
        elif contract.th_is_expired:
            values['error'] = _('Hợp đồng này đã hết hạn hiệu lực, cổng tiếp nhận tệp đã đóng.')
        return self._render_upload_page(values)

    @http.route('/th_collaborator/upload/<string:token>/submit', type='http', auth='public', website=True, methods=['POST'])
    def submit_upload_form(self, token, **kwargs):
        """Nhận file hợp đồng CTV gửi lên và gán trực tiếp vào hợp đồng theo token truy cập."""
        contract = self._get_contract_by_token(token)
        if not contract:
            return request.not_found()

        profile = contract.th_collaborator_id
        values = {
            'token': token,
            'contract': contract,
            'profile': profile,
        }

        # 1. Kiểm tra trạng thái hợp đồng: Nếu đã hoàn tất, hủy hoặc hết hạn thì từ chối tiếp nhận
        if contract.state in ('close', 'cancel'):
            values['error'] = _('Hợp đồng này đã kết thúc hoặc đã hủy, cổng tiếp nhận đã đóng.')
            return self._render_upload_page(values)
        if contract.th_is_expired:
            values['error'] = _('Hợp đồng này đã hết hạn hiệu lực, không thể tiếp nhận thêm tệp.')
            return self._render_upload_page(values)

        # 2. Đọc và kiểm tra các file tải lên
        files, error = self._read_uploaded_files()
        if error:
            values['error'] = error
            return self._render_upload_page(values)

        # sudo: Người dùng public nộp file hợp đồng vào đúng bản ghi hợp đồng mục tiêu mà không cần đăng nhập hệ thống nội bộ
        contract.sudo()._add_self_contracts(files)

        values['success'] = _('Xin chào %s, hệ thống đã nhận %s file cho hợp đồng "%s" (Mã: %s). Cảm ơn bạn!') % (
            profile.name, len(files), contract.name, contract.th_code)
        return self._render_upload_page(values)

    @http.route('/th_collaborator/download_file', type='http', auth='user', methods=['GET'])
    def download_contract_file(self, contract_id, contract_type='company', stt='1', **kwargs):
        """Tải trực tiếp file hợp đồng về máy theo chuẩn [stt].AUM-HĐDVTT/[Tên CTV] mà không cần đóng ZIP."""
        contract = request.env['th.collaborator.contract'].browse(int(contract_id)).exists()
        if not contract:
            return request.not_found()
        contract.check_access_rights('read')
        contract.check_access_rule('read')

        if contract_type == 'company':
            attachments = contract._get_company_mail_attachments()
        elif contract_type == 'self':
            attachments = contract.th_self_attachment_ids
        else:
            attachments = contract.th_final_attachment_id

        if not attachments:
            return request.not_found()

        attachment = attachments[0]
        ext = os.path.splitext(attachment.name or '')[1].lower() or '.pdf'
        folder_code = contract.th_code or 'AUM-HĐDVTT'
        ctv_name = re.sub(r'[\\/:*?"<>|]+', '_', contract.th_collaborator_id.name or 'CTV').strip()
        idx = int(stt) if str(stt).isdigit() else 1
        download_filename = f"{idx:02d}.{folder_code} - {ctv_name}{ext}"

        file_content = attachment.raw
        if not file_content and attachment.store_fname:
            full_path = attachment._full_path(attachment.store_fname)
            if os.path.isfile(full_path):
                with open(full_path, 'rb') as f:
                    file_content = f.read()

        _logger.info('User %s downloaded contract file %s for contract %s',
                     request.env.uid, download_filename, contract.id)
        return request.make_response(
            file_content,
            headers=[
                ('Content-Type', attachment.mimetype or 'application/octet-stream'),
                ('Content-Length', len(file_content or b'')),
                ('Content-Disposition', content_disposition(download_filename)),
            ]
        )
