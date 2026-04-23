/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { PropertyDefinition } from "@web/views/fields/properties/property_definition";

patch(PropertyDefinition, {
    props: {
        ...PropertyDefinition.props,
        canChangeName: { type: Boolean, optional: true },
        showRequiredOption: { type: Boolean, optional: true },
    },
    components: {
        ...PropertyDefinition.components,
        ModelFieldSelector,
    }
});

patch(PropertyDefinition.prototype, {
    /**
     * We selected a new property type.
     *
     * @param {string} newType
     */
    onPropertyTypeChange(newType) {
        super.onPropertyTypeChange(...arguments);
        if (this.state.propertyDefinition.field) {
            const propertyDefinition = {
                ...this.state.propertyDefinition,
                field: false,
            };

            this.props.onChange(propertyDefinition);
            this.state.propertyDefinition = propertyDefinition;
        }
    },
    /**
     * We changed the name of the property.
     *
     * @param {object} newDefault
     */
    onNameChange(event) {
        const newName = event.target.value;
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            newName,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    },
    /**
     * The model of the relational property (many2one / many2many) has been changed.
     *
     * @param {string} newModel
     */
    async onModelChange(newModel) {
        await super.onModelChange(...arguments);

        const { label, technical } = newModel;
        const modelChanged = technical !== this.state.resModel;
        if (modelChanged) {
            const propertyDefinition = {
                ...this.state.propertyDefinition,
                field: false,
            };
            this.props.onChange(propertyDefinition);
            this.state.propertyDefinition = propertyDefinition;
            await this._updateMatchingRecordsCount();
        }
    },
    async onModelFieldChange(newModelField) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            field: newModelField,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    },

    onFieldIsRequiredChange(newIsRequired) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            is_required: newIsRequired,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }
});
