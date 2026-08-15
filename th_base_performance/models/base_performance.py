# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

TH_DEFAULT_COUNT_LIMIT = 10001


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, count_limit=None):
        """
        Ghi đè phương thức web_search_read của Odoo base để tối ưu hiệu năng Tree View.
        
        Mặc định Odoo base sẽ đếm toàn bộ bản ghi khi số bản ghi vượt quá limit của 1 trang.
        Đối với các bảng dữ liệu lớn, câu lệnh COUNT(*) sẽ rất chậm.
        
        Logic cải tiến:
        - Tự động cộng offset vào count_limit: count_limit = offset + TH_DEFAULT_COUNT_LIMIT.
        - Đảm bảo khi người dùng sang các trang tiếp theo (trang 10,000+), Pager không bị dừng
          mà tiếp tục cho phép chuyển trang sang các bản ghi phía sau mà vẫn đếm tối ưu.
        """
        if count_limit is None and not self._context.get('disable_th_count_limit'):
            try:
                param_limit = self.env['ir.config_parameter'].sudo().get_param(
                    'th_base_performance.default_count_limit', 
                    default=TH_DEFAULT_COUNT_LIMIT
                )
                base_limit = int(param_limit)
            except Exception as e:
                _logger.warning("Lỗi khi đọc cấu hình th_base_performance.default_count_limit: %s", e)
                base_limit = TH_DEFAULT_COUNT_LIMIT

            # Cộng offset vào base_limit để không bị dừng Pager khi offset lớn hơn count_limit ban đầu
            count_limit = (offset or 0) + base_limit

        return super().web_search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit
        )
