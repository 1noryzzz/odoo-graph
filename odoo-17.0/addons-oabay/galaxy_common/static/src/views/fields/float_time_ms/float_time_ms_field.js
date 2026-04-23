/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTimeMs } from "../formatters";
import { parseFloatTimeMs } from "../parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";
import { floatTimeField, FloatTimeField } from "@web/views/fields/float_time/float_time_field";


export class FloatTimeMilliField extends FloatTimeField {
    static defaultProps = {
        inputType: "text",
        displaySeconds: true,
    };

    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTimeMs(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        return formatFloatTimeMs(this.props.record.data[this.props.name], {
            displaySeconds: this.props.displaySeconds,
        });
    }
}

export const floatTimeMilliField = {
    ...floatTimeField,
    displayName: _t("Time Ms"),
}


registry.category("fields").add("float_time_ms", floatTimeMilliField);
