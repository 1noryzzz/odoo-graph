/** @odoo-module alias=ifs.gar.invite.ListView **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class PartnerInviteListController extends listView.Controller {
  onClickCreate() {
    this.actionService.doActionButton({
      name: 'start_invite',
      type: "object",
      resModel: this.model.root.resModel,
      context: this.props.context,
      onClose: async () => {
          await this.model.root.load();
          this.model.notify();
      },
    });
  }
}

PartnerInviteListController.template = `ifs_gar_invite.ListView`;

export const PartnerInviteListView = {
  ...listView,
  Controller: PartnerInviteListController,
};

registry.category("views").add("partner_invite", PartnerInviteListView);
