/** @odoo-module alias=ifs.gar.account.ListView **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class FeeSolutionListController extends listView.Controller {
  onClickCreate() {
    this.actionService.doActionButton({
      name: 'create_solution_ver',
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
        name: 'view_solution_ver',
        type: "object",
        resModel: record.resModel,
        resId: record.resId,
        context: this.props.context,
        onClose: async () => {
            await this.model.root.load();
            this.model.notify();
        },
      });
    }
  }
}

export const FeeSolutionListView = {
  ...listView,
  Controller: FeeSolutionListController,
};

registry.category("views").add("solution_list", FeeSolutionListView);
