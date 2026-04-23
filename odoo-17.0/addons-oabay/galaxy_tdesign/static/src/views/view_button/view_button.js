/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";

patch(ViewButton.prototype, {
    get is_step() {
        return this.props.attrs?.step;
    },

    get disabled() {
        if (this.is_step) {
            const { name, type, special } = this.clickParams;
            return (!name && !type && !special) || this.props.disabled || this.props.attrs?.disabled 
                || parseInt(this.props.attrs?.step) > this.props.record.data[this.props.attrs?.current_step];
        } else {
            super.disabled;
        }
    },

    get className() {
        if (this.is_step) {
            if (parseInt(this.props.attrs?.step) === this.props.record.data[this.props.attrs?.current_step]) {
                return "current";
            } else if (parseInt(this.props.attrs?.step) < this.props.record.data[this.props.attrs?.current_step]) {
                return "done";
            } else {
                return "background_gray";
            }
        } else {
            super.className;
        }
    }
})
