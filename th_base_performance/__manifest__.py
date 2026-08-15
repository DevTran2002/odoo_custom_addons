# -*- coding: utf-8 -*-
{
    'name': 'TH Base Performance Optimization',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Tối ưu hiệu năng tải dữ liệu Tree View cho bảng ghi lớn',
    'description': """
        Module tối ưu hiệu năng Odoo Base:
        - Override web_search_read trên model base để áp dụng giới hạn count_limit mặc định khi đếm bản ghi (search_count).
        - Giúp tăng tốc độ load trang Tree View đáng kể đối meo các model có hàng triệu bản ghi.
    """,
    'author': 'AUM',
    'website': 'https://thgroup.vn',
    'depends': ['base', 'web'],
    'data': [],
    'assets': {
        # Đăng ký các file JS và CSS tối ưu hiệu năng vào bundle backend của Odoo
        'web.assets_backend': [
            'th_base_performance/static/src/tree_scroll_perf.css',
            'th_base_performance/static/src/orm_cache.js',
            'th_base_performance/static/src/list_renderer_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
