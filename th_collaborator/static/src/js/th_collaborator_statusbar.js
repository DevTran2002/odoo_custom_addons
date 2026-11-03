/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(StatusBarField.prototype, "th_collaborator.StatusBarFieldConfirm", {
    selectItem(item) {
        const record = this.props.record;
        if (
            record &&
            record.resModel === "th.collaborator.contract" &&
            item.id === "sent" &&
            !record.data.th_mail_sent_date
        ) {
            const superFn = this._super ? this._super.bind(this) : null;
            this.env.services.dialog.add(ConfirmationDialog, {
                title: _t("Xác nhận chuyển trạng thái"),
                body: _t(
                    'Hợp đồng này chưa được gửi mail qua hệ thống. Bạn có chắc chắn muốn chuyển trạng thái sang "Gửi mail" không?'
                ),
                confirmLabel: _t("Đồng ý"),
                cancelLabel: _t("Hủy"),
                confirm: () => {
                    if (superFn) {
                        superFn(item);
                    } else if (this.props.type === "many2one") {
                        this.props.update([item.id, item.name], { save: true });
                    } else {
                        this.props.update(item.id, { save: true });
                    }
                },
            });
            return;
        }
        this._super(item);
    },
});

