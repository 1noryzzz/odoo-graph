/** @odoo-module */

import { WebClient } from "@web/webclient/webclient";
// import BasicModel from 'web.BasicModel';
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.title.setParts({ zopenerp: _t("云腾智慧") });
    }
});

// BasicModel.include({
//     isNew: function (id) {
//         if (this._super.apply(this, arguments)) {
//             var data = this.localData[id];
//             if (data.data && data.res_id && data.data.id === data.res_id) {
//                 return false;
//             }
//             return true;
//         }
//         return false;
//     },
// });
