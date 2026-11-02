# -*- coding: utf-8 -*-
"""Vẽ sơ đồ tổng quan & quy trình (PNG) bằng Pillow."""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = 'C:/Windows/Fonts/arial.ttf'
FONT_B = 'C:/Windows/Fonts/arialbd.ttf'
S = 2  # supersampling

C = {
    'bg': (255, 255, 255), 'text': (33, 37, 41), 'muted': (90, 98, 110), 'line': (70, 80, 95),
    'actor': (255, 243, 205), 'actor_b': (214, 168, 0),
    'core': (225, 240, 255), 'core_b': (30, 110, 200),
    'ext': (232, 245, 233), 'ext_b': (46, 125, 50),
    'vnpt': (255, 232, 236), 'vnpt_b': (198, 40, 70),
    'group': (247, 249, 252), 'group_b': (160, 170, 185),
}


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size * S)


def wrap(draw, text, fnt, width):
    lines = []
    for para in text.split('\n'):
        words, cur = para.split(' '), ''
        for word in words:
            test = (cur + ' ' + word).strip()
            if draw.textlength(test, font=fnt) <= width:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def box(draw, xy, title, body='', fill='core', border='core_b', title_size=15, body_size=12):
    x1, y1, x2, y2 = [v * S for v in xy]
    draw.rounded_rectangle([x1, y1, x2, y2], radius=10 * S, fill=C[fill], outline=C[border], width=2 * S)
    ft, fb = font(title_size, True), font(body_size)
    lines_t = wrap(draw, title, ft, x2 - x1 - 20 * S)
    lines_b = wrap(draw, body, fb, x2 - x1 - 20 * S) if body else []
    total = len(lines_t) * (title_size + 4) * S + (len(lines_b) * (body_size + 4) * S + 6 * S if lines_b else 0)
    y = (y1 + y2) / 2 - total / 2
    for line in lines_t:
        draw.text(((x1 + x2) / 2, y), line, font=ft, fill=C['text'], anchor='mt')
        y += (title_size + 4) * S
    y += 6 * S
    for line in lines_b:
        draw.text(((x1 + x2) / 2, y), line, font=fb, fill=C['muted'], anchor='mt')
        y += (body_size + 4) * S


def group(draw, xy, label):
    x1, y1, x2, y2 = [v * S for v in xy]
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14 * S, fill=C['group'], outline=C['group_b'], width=2 * S)
    draw.text((x1 + 14 * S, y1 + 10 * S), label, font=font(16, True), fill=C['muted'])


def arrow(draw, p1, p2, label='', both=False, label_dy=-14):
    (x1, y1), (x2, y2) = [(a * S, b * S) for a, b in (p1, p2)]
    draw.line([x1, y1, x2, y2], fill=C['line'], width=2 * S)

    def head(xa, ya, xb, yb):
        ang = math.atan2(yb - ya, xb - xa)
        size = 10 * S
        pts = [(xb, yb), (xb - size * math.cos(ang - 0.4), yb - size * math.sin(ang - 0.4)),
               (xb - size * math.cos(ang + 0.4), yb - size * math.sin(ang + 0.4))]
        draw.polygon(pts, fill=C['line'])
    head(x1, y1, x2, y2)
    if both:
        head(x2, y2, x1, y1)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + label_dy * S
        fnt = font(11)
        w = draw.textlength(label, font=fnt)
        draw.rectangle([mx - w / 2 - 4 * S, my - 8 * S, mx + w / 2 + 4 * S, my + 8 * S], fill=C['bg'])
        draw.text((mx, my), label, font=fnt, fill=C['muted'], anchor='mm')


def title(draw, w, text, sub):
    draw.text((w * S / 2, 22 * S), text, font=font(22, True), fill=C['text'], anchor='mt')
    draw.text((w * S / 2, 54 * S), sub, font=font(13), fill=C['muted'], anchor='mt')


def overview(path):
    W, H = 1500, 900
    img = Image.new('RGB', (W * S, H * S), C['bg'])
    d = ImageDraw.Draw(img)
    title(d, W, 'SƠ ĐỒ TỔNG QUAN HỆ THỐNG TH COLLABORATOR',
          'Odoo 16 · module th_collaborator (lõi) + th_collaborator_sign_vnpt (nhà cung cấp ký số)')
    # Actors
    group(d, (20, 90, 250, 880), 'Người dùng')
    box(d, (40, 140, 230, 300), 'Nhân viên / Bên A', 'Role "Nhân viên quản lý CTV": quản lý CTV, template, gửi mail, ký số', 'actor', 'actor_b')
    box(d, (40, 360, 230, 520), 'Cộng tác viên (CTV)', 'Không đăng nhập; nhận mail, mở link, nhập SĐT, tải hợp đồng', 'actor', 'actor_b')
    box(d, (40, 580, 230, 740), 'Quản trị hệ thống', 'Cài module, phân quyền, font, SMTP, license VNPT', 'actor', 'actor_b')
    # Odoo core
    group(d, (290, 90, 1080, 880), 'Odoo 16 – module th_collaborator')
    box(d, (310, 140, 560, 290), 'Giao diện backend', 'Form/List CTV, Template, Cấu hình ký số, Wizard tải hàng loạt')
    box(d, (580, 140, 830, 290), 'Màn hình thiết kế (OWL)', 'pdf.js render PDF, vẽ ô đục lỗ & ô chữ ký bên A')
    box(d, (850, 140, 1060, 290), 'Action ký số (OWL)', 'Registry nhà cung cấp ký số kiểu client')
    box(d, (310, 330, 560, 500), 'Hồ sơ CTV', 'th.collaborator.profile: 2 kho hợp đồng, gửi mail, tạo HĐ, ký số, ZIP')
    box(d, (580, 330, 830, 500), 'Template & đục lỗ', 'contract.template + line: đọc ô form, vẽ chữ Unicode, flatten, preview')
    box(d, (850, 330, 1060, 500), 'Cấu hình ký số', 'sign.config: kiểu hiển thị, ảnh, hook provider client/server')
    box(d, (310, 540, 560, 700), 'Controller công khai', '/upload/<token>: CTV tải HĐ (token + SĐT, PDF/ảnh)')
    box(d, (580, 540, 830, 700), 'Controller nội bộ', 'Preview PDF inline, tải ZIP (SĐT_Tên/)')
    box(d, (850, 540, 1060, 700), 'Wizard + Loại HĐ', 'Map file theo SĐT; tag loại hợp đồng')
    box(d, (310, 740, 1060, 860), 'Phân quyền & dữ liệu', 'th_role_collaborator_officer -> th_access_collaborator_user (ACL) · ir.attachment gắn CTV · mail.thread chatter · mail.template')
    # External
    group(d, (1120, 90, 1480, 880), 'Thành phần ngoài')
    box(d, (1140, 140, 1460, 290), 'th_collaborator_sign_vnpt', 'selection_add "vnpt_plugin", license key, map PdfSigner, nạp vnpt-plugin.js', 'vnpt', 'vnpt_b')
    box(d, (1140, 330, 1460, 480), 'VNPT-CA Plugin + USB Token', 'Phần mềm trên máy người ký (wss://localhost:4433…), nhập PIN', 'vnpt', 'vnpt_b')
    box(d, (1140, 520, 1460, 660), 'Máy chủ mail (SMTP)', 'Gửi mail từ email người phụ trách', 'ext', 'ext_b')
    box(d, (1140, 700, 1460, 860), 'PostgreSQL + Filestore', 'Dữ liệu CTV, cấu hình; file hợp đồng (ir.attachment)', 'ext', 'ext_b')
    # Arrows
    arrow(d, (230, 220), (310, 215), 'thao tác')
    arrow(d, (230, 440), (310, 615), 'link + SĐT')
    arrow(d, (230, 660), (310, 790), 'cấu hình')
    arrow(d, (435, 290), (435, 330))
    arrow(d, (705, 290), (705, 330))
    arrow(d, (955, 290), (955, 330))
    arrow(d, (560, 415), (580, 415), both=True)
    arrow(d, (830, 415), (850, 415), both=True)
    arrow(d, (1060, 215), (1140, 215), 'registry')
    arrow(d, (1300, 290), (1300, 330), 'JS gọi', both=True, label_dy=0)
    arrow(d, (1060, 770), (1140, 610), 'gửi mail')
    arrow(d, (1060, 830), (1140, 800), 'lưu')
    img.resize((W, H), Image.LANCZOS).save(path)


def process(path):
    W, H = 1500, 620
    img = Image.new('RGB', (W * S, H * S), C['bg'])
    d = ImageDraw.Draw(img)
    title(d, W, 'QUY TRÌNH NGHIỆP VỤ HỢP ĐỒNG CTV', 'Từ tạo CTV đến lưu hợp đồng CTV gửi lại (bên A ký số, bên B ký và tải lên)')
    row1 = [
        ('1. Tạo CTV', 'Tên, SĐT, email, người phụ trách, template'),
        ('2. Cấu hình template', 'Upload PDF, map ô / vẽ ô, ô chữ ký, mẫu email'),
        ('3. Xem trước', 'PDF đục lỗ inline, không lưu'),
        ('4. Tạo hợp đồng', 'Lưu SĐT_Tên_<template>.pdf vào Hợp đồng công ty'),
        ('5. Ký số bên A', 'USB Token, lẻ hoặc hàng loạt, lưu _da_ky.pdf'),
    ]
    row2 = [
        ('6. Gửi mail', 'Từ email người phụ trách, kèm Hợp đồng công ty'),
        ('7. CTV mở link', 'Nhập SĐT đã đăng ký (token + SĐT)'),
        ('8. CTV tải hợp đồng', '≤10 file PDF/ảnh, đổi tên SĐT_Tên'),
        ('9. Theo dõi', 'Trạng thái, chatter, lọc CTV của tôi'),
        ('10. Tải ZIP / lưu trữ', 'HĐ công ty / HĐ CTV, thư mục SĐT_Tên'),
    ]
    bw, gap, x0 = 250, 40, 40
    for i, (t, b) in enumerate(row1):
        x = x0 + i * (bw + gap)
        fill, border = ('vnpt', 'vnpt_b') if i == 4 else ('core', 'core_b')
        box(d, (x, 110, x + bw, 270), t, b, fill, border)
        if i:
            arrow(d, (x - gap, 190), (x, 190))
    for i, (t, b) in enumerate(row2):
        x = x0 + (4 - i) * (bw + gap)
        fill, border = ('actor', 'actor_b') if i in (1, 2) else ('ext', 'ext_b')
        box(d, (x, 380, x + bw, 540), t, b, fill, border)
        if i:
            arrow(d, (x + bw + gap, 460), (x + bw, 460))
    arrow(d, (x0 + 4 * (bw + gap) + bw / 2, 270), (x0 + 4 * (bw + gap) + bw / 2, 380))
    # Chú thích
    legend = [('core', 'core_b', 'Nhân viên (Odoo)'), ('vnpt', 'vnpt_b', 'Ký số VNPT'),
              ('actor', 'actor_b', 'CTV (trang công khai)'), ('ext', 'ext_b', 'Gửi mail / lưu trữ')]
    lx = 40
    for fill, border, label in legend:
        d.rounded_rectangle([lx * S, 575 * S, (lx + 22) * S, 597 * S], radius=4 * S, fill=C[fill], outline=C[border], width=2 * S)
        d.text(((lx + 30) * S, 586 * S), label, font=font(13), fill=C['text'], anchor='lm')
        lx += 230
    img.resize((W, H), Image.LANCZOS).save(path)


if __name__ == '__main__':
    out = sys.argv[1]
    overview(out + '/so_do_tong_quan.png')
    process(out + '/so_do_quy_trinh.png')
    print('ok')
