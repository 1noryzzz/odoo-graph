/** @odoo-module **/

import { registry } from "@web/core/registry";
import { JsonField, jsonField } from "@web/views/fields/jsonb/jsonb";
import { markup } from "@odoo/owl";

export class JSONField extends JsonField {
    static template = "galaxy_common.JSONField";
    setup() {
        hljs.configure({
            ignoreUnescapedHTML: true,
        })
    }
    get formattedValue() {
        try {
            const value = this.props.record.data[this.props.name];
            return markup(hljs.highlightAuto(value ? JSON.stringify(value, null, 2) : '').value);
        } catch (e) {
            return super.formattedValue;
        }
    }
}

export const jsonFormattedField = {
    ...jsonField,
    component: JSONField,
};

registry.category("fields").add("json", jsonFormattedField);
