/** @odoo-module alias=ifs.gar.entry.ListView **/

import { patch } from "@web/core/utils/patch";
import { PartnerInviteListController } from '@ifs_gar_invite/views/list/partner_invite_list_view';

patch(PartnerInviteListController.prototype, {
  async openRecord(record) {
    if (this.archInfo.openAction) {
      this._super(...arguments);
    } else {
      if (['draft', 'sended'].includes(record.data.state)) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds });
      } else {
        this.actionService.doActionButton({
          name: 'view_invite',
          type: "object",
          resModel: record.resModel,
          resId: record.resId,
          context: this.props.context,
          // onClose: async () => {
          //     await self.model.root.load();
          //     self.model.notify();
          // },
        });
      }
    }
  }
});
