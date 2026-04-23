/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.listItemDivWidget = publicWidget.Widget.extend({
  selector: '.bill-list',
  events: {
    click: '_onClickListItem'
  },

  _onClickListItem() {
    let bill_id = this.$el.attr("id");
    window.location.href = `/openapi/bill/bill_info_details?bill_id=${bill_id}`;
  }
});