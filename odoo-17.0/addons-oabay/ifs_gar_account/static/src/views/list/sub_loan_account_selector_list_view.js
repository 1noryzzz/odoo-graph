/** @odoo-module alias=ifs.gar.account.sub.loan.account.selector.ListView **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class SubLoanAccountSelectorListController extends listView.Controller {
  setup() {
    super.setup();
    this.props.allowSelectors = false;
  }
}

export const SubLoanAccountSelectorListView = {
  ...listView,
  Controller: SubLoanAccountSelectorListController,
};

registry.category("views").add("sub_account_selector", SubLoanAccountSelectorListView);
