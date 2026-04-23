/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
  getColumnIndex(record) {
    let index = this.props.list.records.findIndex(function (e) { return record.id === e.id });
    if (index > -1) {
      return index + 1;
    } else {
      return '';
    }
  },

  getGroupNameCellColSpan(group) {
    let colspan = super.getGroupNameCellColSpan(group);
    colspan++;
    return colspan;
  },

  setDefaultColumnWidths() {
    const widths = this.state.columns.map((col) => this.calculateColumnWidth(col));
    const sumOfRelativeWidths = widths
      .filter(({ type }) => type === "relative")
      .reduce((sum, { value }) => sum + value, 0);

    // 1 because nth-child selectors are 1-indexed, 2 when the first column contains
    // the checkboxes to select records.
    const columnOffset = this.hasSelectors ? 3 : 2;
    widths.forEach(({ type, value }, i) => {
      const headerEl = this.tableRef.el.querySelector(`th:nth-child(${i + columnOffset})`);
      if (!headerEl) {
        return;
      }
      if (type === "absolute") {
        if (this.isEmpty) {
          headerEl.style.width = value;
        } else {
          headerEl.style.minWidth = value;
        }
      } else if (type === "relative" && this.isEmpty) {
        headerEl.style.width = `${((value / sumOfRelativeWidths) * 100).toFixed(2)}%`;
      }
    });
  },
});
