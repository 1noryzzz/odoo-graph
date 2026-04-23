/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TextField, textField } from "@web/views/fields/text/text_field";
import { markup } from "@odoo/owl";

export class PlainJSONField extends TextField {
    static template = "galaxy_common.PlainJSONField";
    setup() {
        hljs.configure({
            ignoreUnescapedHTML: true,
        })
    }
    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        try {
            return markup(hljs.highlightAuto(value ? JSON.stringify(JSON.parse(value), null, 2) : '').value);
        } catch (e) {
            return value ? value : '';
        }
    }
}

export const plainJSONField = {
    ...textField,
    component: PlainJSONField,
    displayName: _t("Multiline JSON Text"),
    supportedTypes: ["html", "text", "json", "jsonb"],
};

registry.category("fields").add("json.text", plainJSONField);
