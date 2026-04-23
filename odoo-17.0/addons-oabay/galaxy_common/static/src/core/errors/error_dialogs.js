/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ErrorDialog, ClientErrorDialog, NetworkErrorDialog, RPCErrorDialog, WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

ErrorDialog.title = _t("错误提示");
ClientErrorDialog.title = _t("客户端错误提示");
NetworkErrorDialog.title = _t("网络错误提示");

patch(RPCErrorDialog.prototype, {
    inferTitle() {
        switch (this.props.type) {
            case "server":
                this.title = _t("服务端错误");
                break;
            case "script":
                this.title = _t("客户端错误");
                break;
            case "network":
                this.title = _t("网络连接错误");
                break;
            default:
                super.inferTitle();
                break;
        }
    }
});

patch(WarningDialog.prototype, {
    inferTitle() {
        var title = super.inferTitle();
        if (title === _t("Odoo Warning")) {
            title = _t("警告信息");
        }
        return title;
    }
});