/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { many2ManyTagsField, Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "@web/core/tags_list/tags_list";


export class FieldMany2ManyTagsPropertiesTagsList extends TagsList { }
// FieldMany2ManyTagsPropertiesTagsList.template = "FieldMany2ManyTagsPropertiesTagsList";

export class FieldMany2ManyTagsProperties extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        TagsList: FieldMany2ManyTagsPropertiesTagsList,
    };
    static props = {
        ...Many2ManyTagsField.props,
        propertiesField: { type: String, optional: true },
        tagNames: { type: Array, optional: true },
    };
    static defaultProps = {
        ...Many2ManyTagsField.defaultProps,
        propertiesField: "json_datas",
        tagNames: ['name'],
    };
    get tags() {
        const tags = super.tags;
        const propsByResId = this.props.record.data[this.props.name].records.reduce((acc, record) => {
            acc[record.resId] = record.data[this.props.propertiesField].reduce((text, property) => {
                if (this.props.tagNames.includes(property.name)) {
                    if (text !== '') text += ', ';

                    text += (this.props.tagNames.length > 1 ? (property.string + ': ') : '') + property.value;
                }

                return text;
            }, '')
            return acc;
        }, {});
        tags.forEach(tag => tag.text = propsByResId[tag.resId]);
        return tags.filter(tag => tag.text !== '');
    }
};

export const fieldMany2ManyTagsProperties = {
    ...many2ManyTagsField,
    additionalClasses: [...many2ManyTagsField.additionalClasses || [], "o_field_many2many_tags"],
    component: FieldMany2ManyTagsProperties,
    supportedTypes: ["many2many", "one2many"],
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions,
        {
            label: _t("Properties field"),
            name: "properties_field",
            type: "field",
        },
    ],
    extractProps({ attrs, options }) {
        const props = many2ManyTagsField.extractProps(...arguments);
        return {
            ...props,
            propertiesField: attrs.properties_field,
            tagNames: options.tag_names,
        };
    },
}

registry.category("fields").add("many2many_tags_properties", fieldMany2ManyTagsProperties);
