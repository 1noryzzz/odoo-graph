/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { View } from "@web/views/view";
import { Component } from "@odoo/owl";

import { escape } from '@web/core/utils/strings';

const { markup } = owl;

export class SubviewX2ManyField extends Component {
    static template = "galaxy_common.SubviewX2ManyField";
    static useSubView = true;
    static components = { View };
    static props = {
        ...standardFieldProps,
        editable: { type: "string", optional: true },
        inverse: { type: "string", optional: true },
    };

    setup() {
        this.activeField = this.props.record.activeFields[this.props.name];
        this.field = this.props.record.fields[this.props.name];
        this.viewMode = this.activeField.viewMode;
    }

    get viewProps() {
        let domain = [];
        if (this.props.inverse) {
            domain.push([
                this.props.inverse, '=', this.props.record.data.id
            ]);
        }
        return {
            allowSelectors: true,
            display: { searchPanel: false },
            editable: this.props.editable, // readonly
            noBreadcrumbs: true,
            noContentHelp: markup(`<p>${escape(this.env._t("No records found!"))}</p>`),
            showButtons: false,
            context: typeof this.activeField.context === 'string' ? 
                JSON.parse(this.activeField.context.replaceAll("'", "\"")) : this.activeField.context,
            domain,
            // dynamicFilters: this.props.dynamicFilters,
            resModel: this.props.value.resModel,
            searchViewId: this.props.value.searchViewId,
            type: this.viewMode
        }
    }
}

export const subviewX2ManyField = {
    component: SubviewX2ManyField,
    displayName: _t("Sub View"),
    supportedTypes: ["one2many", "many2many"],
    extractProps({ attrs }, dynamicInfo) {
        return {
            inverse: attrs.inverse,
        };
    },
}

registry.category("fields").add("subview_x2many", subviewX2ManyField);
