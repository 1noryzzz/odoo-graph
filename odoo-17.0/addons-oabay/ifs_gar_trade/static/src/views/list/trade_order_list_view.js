/** @odoo-module alias=ifs.gar.trade.order.ListView **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class TradeOrderListController extends listView.Controller {
  onClickCreate() {
    this.actionService.doActionButton({
      name: 'selector_merchant',
      type: "object",
      resModel: this.model.root.resModel,
      context: this.props.context,
      onClose: async () => {
          await this.model.root.load();
          this.model.notify();
      },
    });
  }
  async openRecord(record) {
    if (this.archInfo.openAction) {
      this._super(...arguments);
    } else {
      this.actionService.doActionButton({
        name: 'view_trade_order',
        type: "object",
        resId: record.resId,
        resModel: this.model.root.resModel,
        context: this.props.context,
        onClose: async () => {
            await this.model.root.load();
            this.model.notify();
        },
      });
    }
  }
}

TradeOrderListController.template = `ifs_gar_trade.ListView`;

export const TradeOrderListView = {
  ...listView,
  Controller: TradeOrderListController,
};

registry.category("views").add("trade_order", TradeOrderListView);
