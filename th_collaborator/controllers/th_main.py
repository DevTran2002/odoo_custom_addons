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

    def _get_profile_by_token(self, token):
        """Tìm CTV theo token của link upload."""
        Profile = request.env['th.collaborator.profile']
        if not token or len(token) < 20:
            return Profile.browse()
        # sudo: CTV truy cập ẩn danh (public user) không có quyền đọc model;
        # chỉ tra đúng 1 bản ghi theo token ngẫu nhiên, không lộ dữ liệu khác.
        return Profile.sudo().search([('th_access_token', '=', token)], limit=1)

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
        """Hiển thị form portal để CTV tải hợp đồng lên bằng token bảo mật."""
        profile = self._get_profile_by_token(token)
        if not profile:
            return request.not_found()
        # sudo: Đọc danh sách hợp đồng của CTV để hiển thị trên portal công khai
        contracts = profile.sudo().th_contract_ids.filtered(lambda c: c.state != 'cancel')
        return self._render_upload_page({
            'token': token,
            'profile': profile,
            'contracts': contracts,
        })

    @http.route('/th_collaborator/upload/<string:token>/submit', type='http', auth='public', website=True, methods=['POST'])
    def submit_upload_form(self, token, contract_id=None, **kwargs):
        """Nhận file hợp đồng CTV gửi lên và gán đúng hợp đồng theo token truy cập."""
        profile = self._get_profile_by_token(token)
        if not profile:
            return request.not_found()

        # sudo: Đọc danh sách hợp đồng của CTV để hiển thị lại nếu có lỗi
        contracts = profile.sudo().th_contract_ids.filtered(lambda c: c.state != 'cancel')
        values = {
            'token': token,
            'profile': profile,
            'contracts': contracts,
            'contract_id': contract_id,
        }

        # 1. Xác định Hợp đồng mục tiêu
        target_contract = False
        if contract_id and str(contract_id).isdigit():
            # sudo: Tìm hợp đồng được chỉ định thuộc CTV này
            target_contract = profile.sudo().th_contract_ids.filtered(lambda c: c.id == int(contract_id))
        elif len(contracts) == 1:
            target_contract = contracts[0]

        if not target_contract:
            values['error'] = _('Vui lòng chọn hợp đồng bạn muốn nộp file.')
            return self._render_upload_page(values)

        # 2. Đọc và kiểm tra các file tải lên
        files, error = self._read_uploaded_files()
        if error:
            values['error'] = error
            return self._render_upload_page(values)

        # sudo: Lưu file vào đúng hợp đồng mục tiêu của CTV
        target_contract.sudo()._add_self_contracts(files)

        values['success'] = _('Xin chào %s, hệ thống đã nhận %s file cho hợp đồng "%s" (Mã: %s). Cảm ơn bạn!') % (
            profile.name, len(files), target_contract.name, target_contract.th_code)
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
            attachments = contract.th_company_attachment_ids
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
