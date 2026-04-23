/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatPercent } from "../formatters";
import { parsePercent } from "../parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";

import { Component, useState } from "@odoo/owl";

export class PercentField extends Component {
    static template = "web.FloatField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        step: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        inputType: "text",
    };

    setup() {
        this.state = useState({
            hasFocus: false,
        });
        this.inputRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parsePercent(v),
        });
        useNumpadDecimal();
    }

    onFocusIn() {
        this.state.hasFocus = true;
    }

    onFocusOut() {
        this.state.hasFocus = false;
    }

    get formattedValue() {
        return formatPercent(this.value);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const percentField = {
    component: PercentField,
    displayName: _t("Percent"),
    supportedOptions: [
        {
            label: _t("Type"),
            name: "type",
            type: "string",
            default: "text",
        },
        {
            label: _t("Step"),
            name: "step",
            type: "number",
        },
    ],
    supportedTypes: ["float", "percent"],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => ({
        inputType: options.type,
        step: options.step,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("percent", percentField);
