/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from '@web/views/utils';
import { usePopover } from "@web/core/popover/popover_hook";
import { PropertyDefinition } from "@web/views/fields/properties/property_definition";
import { propertiesField, PropertiesField } from '@web/views/fields/properties/properties_field';

export class DynamicPropertiesField extends PropertiesField {
    static template = "galaxy_common.DynamicPropertiesField";
    static props = {
        ...PropertiesField.props,
        columns: {
            type: Number,
            optional: true,
            validate: (columns) => [1, 2, 3].includes(columns),
        },
        showRequiredOption: { type: Boolean, optional: true }
    }

    setup() {
        super.setup();
        this.popover = usePopover(PropertyDefinition, {
            closeOnClickAway: true,//this.checkPopoverClose,
            popoverClass: "o_property_field_popover",
            position: "top",
            onClose: () => this.onCloseCurrentPopover?.(),
            fixedPosition: true,
            arrow: true,
        });
    }

    /**
     * 这里重载掉原方法，不再根据类型变化，更换name属性
     * 而改为由用户设置name
     *
     * @param {object} propertyDefinition
     */
    _regeneratePropertyName(propertyDefinition) {
        const newName = propertyDefinition.newName;
        delete propertyDefinition.newName;

        if (newName) {
            const initialValues = this.initialValues[propertyDefinition.name];
            if (initialValues && initialValues.name === propertyDefinition.name) {
                this.initialValues[newName] = initialValues;
            }
            propertyDefinition.name = newName;
        }
    }

    /**
     * 打开属性定义界面时，把属性name打开，并处于可编辑状态
     *
     * @param {DomElement} target
     * @param {string} propertyName
     * @param {boolean} isNewlyCreated
     */
    _openPropertyDefinition(target, propertyName, isNewlyCreated = false) {
        const propertiesList = this.propertiesList;
        const propertyIndex = propertiesList.findIndex(
            (property) => property.name === propertyName
        );

        // maybe the property has been renamed because the type / model
        // changed, retrieve the new one
        const currentName = (propertyName) => {
            let nextpropertyName = undefined;
            const propertiesList = this.propertiesList;
            for (const [newName, initialValue] of Object.entries(this.initialValues)) {
                if (initialValue.name === propertyName) {
                    const prop = propertiesList.find((prop) => prop.name === newName);
                    if (prop) {
                        return newName;
                    }
                }
                // 当 name 被修改多次时，因为initialValues 里只在打开时取了一次，中间状态未刷新它，所以这里查找中间值
                if (newName === propertyName) {
                    nextpropertyName = initialValue.name;
                }
            }
            for (const [newName, initialValue] of Object.entries(this.initialValues)) {
                if (initialValue.name === nextpropertyName) {
                    const prop = propertiesList.find((prop) => prop.name === newName);
                    if (prop) {
                        return newName;
                    }
                }
            }

            // 如果没有找到，再试着从propertiesList里取出definition_changed 为true的那一项
            const prop = propertiesList.find((prop) => prop.definition_changed);
            if (prop) {
                return prop.name;
            }
            return propertyName;
        };

        this.onCloseCurrentPopover = () => {
            this.onCloseCurrentPopover = null;
            this.state.movedPropertyName = null;
            target.classList.remove("disabled");
            if (isNewlyCreated) {
                this._setDefaultPropertyValue(currentName(propertyName));
            }
        };

        this.popover.open(target, {
            readonly: this.props.readonly || !this.state.canChangeDefinition,
            canChangeDefinition: this.state.canChangeDefinition,
            canChangeName: true,
            checkDefinitionWriteAccess: () => this.checkDefinitionWriteAccess(),
            propertyDefinition: this.propertiesList.find(
                (property) => property.name === currentName(propertyName)
            ),
            context: this.props.context,
            onChange: this.onPropertyDefinitionChange.bind(this),
            onDelete: () => this.onPropertyDelete(currentName(propertyName)),
            onPropertyMove: (direction) =>
                this.onPropertyMove(currentName(propertyName), direction),
            isNewlyCreated: isNewlyCreated,
            propertyIndex: propertyIndex,
            propertiesSize: propertiesList.length,
            showRequiredOption: this.props.showRequiredOption,
        });
    }

    /**
     * 这里覆盖掉原方法，仅仅是为了在有newName时，用newName查找 index
     * The property definition or value has been changed.
     *
     * @param {object} propertyDefinition
     */
    async onPropertyDefinitionChange(propertyDefinition) {
        propertyDefinition["definition_changed"] = true;
        if (propertyDefinition.type === "separator") {
            // remove all other keys
            propertyDefinition = pick(
                propertyDefinition,
                "name",
                "string",
                "definition_changed",
                "type"
            );
        }
        const propertiesValues = this.propertiesList;
        const propertyIndex = this._getPropertyIndex(propertyDefinition.newName ? propertyDefinition.newName : propertyDefinition.name);

        const oldType = propertiesValues[propertyIndex]?.type;
        const newType = propertyDefinition.type;

        this._regeneratePropertyName(propertyDefinition);

        propertiesValues[propertyIndex] = propertyDefinition;
        await this.props.record.update({ [this.props.name]: propertiesValues });

        if (newType === "separator" && oldType !== "separator") {
            // unfold automatically the new separator
            this._unfoldSeparators([propertyDefinition.name], true);
            // layout has been changed, move the definition popover
            this.movePopoverToProperty = propertyDefinition.name;
        } else if (oldType === "separator" && newType !== "separator") {
            // unfold automatically the previous separator
            const previousSeperator = propertiesValues.findLast(
                (property, index) => index < propertyIndex && property.type === "separator"
            );
            if (previousSeperator) {
                this._unfoldSeparators([previousSeperator.name], true);
            }
            // layout has been changed, move the definition popover
            this.movePopoverToProperty = propertyDefinition.name;
        }
    }

    async onPropertyCreate() {
        if (!(await this.checkDefinitionWriteAccess())) {
            this.notification.add(
                _t("You need edit access on the parent document to update these property fields"),
                { type: "warning" }
            );
            return;
        }
        const propertiesDefinitions = this.propertiesList || [];

        if (
            propertiesDefinitions.length &&
            propertiesDefinitions.some(
                (prop) => prop.type !== "separator" && (!prop.string || !prop.string.length)
            )
        ) {
            // do not allow to add new field until we set a label on the previous one
            this.propertiesRef.el.closest(".o_field_dynamic_properties").classList.add("o_field_invalid");

            this.notification.add(_t("Please complete your properties before adding a new one"), {
                type: "warning",
            });
            return;
        }

        this._unfoldPropertyGroup(propertiesDefinitions.length - 1, propertiesDefinitions);

        this.propertiesRef.el.closest(".o_field_dynamic_properties").classList.remove("o_field_invalid");

        const newName = this.generatePropertyName();
        propertiesDefinitions.push({
            name: newName,
            string: _t("Property %s", propertiesDefinitions.length + 1),
            type: "char",
            definition_changed: true,
        });
        this.openPropertyDefinition = newName;
        this.state.showAddButton = true;
        this.props.record.update({ [this.props.name]: propertiesDefinitions });
        this.initialValues[newName] = {
            name: newName,
            type:  "char",
            comodel: undefined
        }; // 这里存在新建的这个属性，以便在打开后修改了名字时，可以找回原来的属性名
    }
}

export const dynamicPropertiesField = {
    component: DynamicPropertiesField,
    displayName: _t("DynamicProperties"),
    supportedTypes: ["properties"],
    extractProps({ attrs }, dynamicInfo) {
        const showRequiredOption = archParseBoolean(attrs.showRequiredOption);
        return {
            ...propertiesField.extractProps({ attrs }, dynamicInfo),
            showRequiredOption
        };
    },
};

registry.category("fields").add("dynamic_properties", dynamicPropertiesField);
