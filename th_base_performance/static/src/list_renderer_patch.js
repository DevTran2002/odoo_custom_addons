/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched, onWillPatch, onWillRender, onWillUnmount, useState } from "@odoo/owl";

const INITIAL_CHUNK = 30;
const LOAD_CHUNK = 25;
const TRIGGER_VIEWPORT_MULTIPLIER = 1.5;
const VIRTUAL_THRESHOLD = 30;

patch(ListRenderer.prototype, "th_base_performance.progressive_scroll_renderer", {
    setup() {
        this._super(...arguments);

        this.thVirtual = useState({ endIndex: INITIAL_CHUNK });

        this._thScrollEl = null;
        this._thScrollFn = null;
        this._thLastHash = "";
        this._thSpacerBot = null;
        this._thRowHeight = 40;
        this._thTbodyEl = null;
        this._thTicking = false;

        // Ghi đè getter list.records để chỉ trả về phân đoạn bản ghi từ 0 đến endIndex
        onWillRender(() => {
            const list = this.props.list;
            if (!list || list.isGrouped || !list.records) {
                return;
            }

            const currentRaw =
                list._thRawRecords !== undefined ? list._thRawRecords : list.records;
            const total = currentRaw.length;

            const firstId = total > 0 ? (currentRaw[0]?.id ?? "") : "";
            const lastId = total > 0 ? (currentRaw[total - 1]?.id ?? "") : "";
            const hash = `${total}:${firstId}:${lastId}`;

            // Reset vị trí nạp khi dữ liệu thay đổi (chuyển trang, lọc dữ liệu)
            if (this._thLastHash !== hash) {
                this._thLastHash = hash;
                this.thVirtual.endIndex = Math.min(total, INITIAL_CHUNK);
                this._thTbodyEl = null;
            }

            if (list._thPatched) {
                return;
            }

            let _internal = list.records;
            list._thRawRecords = _internal;

            const self = this;
            Object.defineProperty(list, "records", {
                get() {
                    const raw = _internal || [];
                    if (raw.length <= VIRTUAL_THRESHOLD) {
                        return raw;
                    }
                    return raw.slice(0, self.thVirtual.endIndex);
                },
                set(val) {
                    _internal = val;
                    list._thRawRecords = val;
                    self.thVirtual.endIndex = Math.min((val || []).length, INITIAL_CHUNK);
                    self._thTbodyEl = null;
                },
                configurable: true,
                enumerable: true,
            });

            list._thPatched = true;
        });

        onMounted(() => {
            if (this._thNeedVirtual()) {
                this._thAttachScroll();
                this._thUpdateSpacerBot();
                this._thOnScroll();
            }
        });

        // Xóa spacer trước khi OWL cập nhật DOM để tránh xung đột reconciliation
        onWillPatch(() => {
            this._thRemoveSpacerBot();
        });

        onPatched(() => {
            if (this._thNeedVirtual()) {
                this._thAttachScroll();
                this._thUpdateSpacerBot();
                this._thOnScroll();
            }
        });

        onWillUnmount(() => {
            this._thDetachScroll();
        });
    },

    // Kiểm tra điều kiện áp dụng cuộn phân đoạn (bỏ qua danh sách nhóm, x2many hoặc sắp xếp lại dòng)
    _thNeedVirtual() {
        const list = this.props.list;
        if (!list || list.isGrouped || this.isX2Many || this.canResequenceRows) {
            return false;
        }
        const raw = list._thRawRecords || list.records || [];
        return raw.length > VIRTUAL_THRESHOLD;
    },

    // Xác định phần tử cuộn thực sự (chỉ chọn phần tử có overflow và scrollHeight > clientHeight)
    _thFindScrollContainer() {
        if (!this.rootRef.el) {
            return window;
        }

        let el = this.rootRef.el.parentElement;
        while (el && el !== document.body && el !== document.documentElement) {
            const style = getComputedStyle(el);
            const overflowY = style.overflowY;
            const isScrollable = overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay";

            if (isScrollable && el.clientHeight > 0 && el.scrollHeight > el.clientHeight) {
                return el;
            }
            el = el.parentElement;
        }

        const oContent =
            this.rootRef.el.closest(".o_content") ||
            this.rootRef.el.closest(".modal-body") ||
            document.querySelector(".o_content");

        if (oContent && oContent.clientHeight > 0 && oContent.scrollHeight > oContent.clientHeight) {
            return oContent;
        }

        return window;
    },

    // Đăng ký sự kiện cuộn trên phần tử cuộn và window làm dự phòng
    _thAttachScroll() {
        if (!this.rootRef.el) {
            return;
        }

        this._thDetachScroll();

        const scrollEl = this._thFindScrollContainer();
        this._thScrollEl = scrollEl;

        // Throttle sự kiện scroll bằng requestAnimationFrame để tối ưu CPU
        this._thScrollFn = () => {
            if (!this._thTicking) {
                requestAnimationFrame(() => {
                    this._thOnScroll();
                    this._thTicking = false;
                });
                this._thTicking = true;
            }
        };

        if (scrollEl && scrollEl !== window) {
            scrollEl.addEventListener("scroll", this._thScrollFn, { passive: true });
        }

        window.addEventListener("scroll", this._thScrollFn, { passive: true });
    },

    _thDetachScroll() {
        if (this._thScrollFn) {
            if (this._thScrollEl && this._thScrollEl !== window) {
                this._thScrollEl.removeEventListener("scroll", this._thScrollFn);
            }
            window.removeEventListener("scroll", this._thScrollFn);
        }
        this._thScrollEl = null;
        this._thScrollFn = null;
    },

    // Khi vị trí cuộn cách đáy dưới 1.5 lần chiều cao viewport thì nạp thêm bản ghi
    _thOnScroll() {
        if (!this._thNeedVirtual()) {
            return;
        }

        const list = this.props.list;
        const raw = list._thRawRecords || [];
        const total = raw.length;
        const currentEnd = this.thVirtual.endIndex;

        if (currentEnd >= total) {
            return;
        }

        const scrollEl = this._thScrollEl || window;
        let scrollTop, viewportH, scrollHeight;

        if (scrollEl === window) {
            scrollTop = window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
            viewportH = window.innerHeight || document.documentElement.clientHeight;
            scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
        } else {
            scrollTop = scrollEl.scrollTop;
            viewportH = scrollEl.clientHeight;
            scrollHeight = scrollEl.scrollHeight;
        }

        const distanceToBottom = scrollHeight - (scrollTop + viewportH);
        const triggerDistance = viewportH * TRIGGER_VIEWPORT_MULTIPLIER;

        if (distanceToBottom <= triggerDistance) {
            this.thVirtual.endIndex = Math.min(total, currentEnd + LOAD_CHUNK);
        }
    },

    // Cập nhật dòng đệm ở cuối bảng để giữ thanh cuộn đúng chiều cao tổng thể
    _thUpdateSpacerBot() {
        if (!this.rootRef.el) {
            return;
        }

        const list = this.props.list;
        const raw = list._thRawRecords || [];
        const total = raw.length;
        const endIndex = this.thVirtual.endIndex;

        if (endIndex >= total) {
            this._thRemoveSpacerBot();
            return;
        }

        // Cache tham chiếu tbody để tuyệt đối không gọi lại querySelector("tbody")
        if (!this._thTbodyEl || !this._thTbodyEl.isConnected) {
            this._thTbodyEl = this.rootRef.el.querySelector("tbody");
        }
        const tbody = this._thTbodyEl;
        if (!tbody) {
            return;
        }

        // Chỉ đo chiều cao dòng 1 lần duy nhất để tránh querySelector("tr.o_data_row") và reflow
        if (this._thRowHeight === 40) {
            const firstRow = tbody.querySelector("tr.o_data_row");
            if (firstRow && firstRow.offsetHeight > 0) {
                this._thRowHeight = firstRow.offsetHeight;
            }
        }

        const heightBot = (total - endIndex) * this._thRowHeight;

        if (!this._thSpacerBot) {
            this._thSpacerBot = document.createElement("tr");
            this._thSpacerBot.className = "th-virtual-spacer-bot";
            this._thSpacerBot.setAttribute("aria-hidden", "true");
            this._thSpacerBot.style.pointerEvents = "none";
            const td = document.createElement("td");
            td.colSpan = 999;
            td.innerHTML = `<div class="th-loading-indicator"><i class="fa fa-circle-o-notch fa-spin me-2"></i>Đang tải thêm dữ liệu...</div>`;
            this._thSpacerBot.appendChild(td);
        }

        this._thSpacerBot.style.height = heightBot + "px";
        tbody.appendChild(this._thSpacerBot);
    },

    _thRemoveSpacerBot() {
        if (this._thSpacerBot && this._thSpacerBot.parentNode) {
            this._thSpacerBot.parentNode.removeChild(this._thSpacerBot);
        }
    },
});
