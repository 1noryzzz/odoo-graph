/** @odoo-module alias=ifs.gar.trade.merchant.selector.ListView **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class MerchantSelectorListController extends listView.Controller {
  setup() {
    super.setup();
    this.props.allowSelectors = false;
  }
}

export const MerchantSelectorListView = {
  ...listView,
  Controller: MerchantSelectorListController,
};

registry.category("views").add("merchant_selector", MerchantSelectorListView);
