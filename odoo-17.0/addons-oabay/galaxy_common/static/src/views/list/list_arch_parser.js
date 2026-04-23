/** @odoo-module **/

import { ListArchParser } from "@web/views/list/list_arch_parser";
import { patch } from "@web/core/utils/patch";

patch(ListArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        const defaultOrder = xmlDoc.getAttribute("default_order");
        const archInfo = super.parse(xmlDoc, models, modelName);

        if (defaultOrder == "none_order") {
            archInfo.defaultOrder = [];
        }

        return archInfo;
    }
});
