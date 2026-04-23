/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

patch(ListRenderer.prototype, {
  getFormattedValue(column, record) {
    const fieldName = column.name;
    const field = this.fields[fieldName];
    if (field.type === "properties") {
      const formatter = registry.category("formatters").get(field.type, (val) => val);
      const formatOptions = {
        escape: false,
        data: record.data,
        isPassword: "password" in column.rawAttrs,
        digits: column.rawAttrs.digits ? JSON.parse(column.rawAttrs.digits) : field.digits,
        field: record.fields[fieldName],
        property: column.options?.property,
      };
      return record.data[fieldName] !== undefined
        ? formatter(record.data[fieldName], formatOptions)
        : "";
    } else {
      return super.getFormattedValue(column, record);
    }
  }
});
