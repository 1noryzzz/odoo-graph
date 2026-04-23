/** @odoo-module alias=ifs.contract.sign.ListView **/

import {
  formView
} from "@web/views/form/form_view";
import {
  registry
} from "@web/core/registry";
import {
  Component,
  useState,
  useRef,
  onMounted,
  onWillDestroy
} from "@odoo/owl";

export class InclusiveFinancingContractSignRenderer extends formView.Renderer {
  setup() {
    super.setup();

    onMounted(() => {
      this.env.services['bus_service'].addEventListener('notification', this._handleNotifications.bind(this));
    })

    onWillDestroy(() => {
      this.env.services['bus_service'].removeEventListener('notification', this._handleNotifications);
    })
  }

  async _handleNotifications({
    detail: notifications
  }) {
    const proms = notifications.map(async message => {
      if (typeof message === 'object') {
        switch (message.type) {
          case 'ifs_contract_signed':
            await this.props.record.model.action.doAction({
              type: 'ir.actions.act_window_close',
              infos: {
                special: true
              }
            });
            await this.props.record.model.action.doAction({
              type: "ir.actions.client",
              tag: "display_notification",
              params: {
                'type': 'info',
                'sticky': false,
                'message': "签名成功!窗口已关闭"
              },
            });
            if (message.payload && message.payload !== '') {
              await this.props.record.model.action.doAction(message.payload);
            }
            return
          default:
            return
        }
      }
    });
    await Promise.all(proms);
  }
}

export const InclusiveFinancingContractSignView = {
  ...formView,
  Renderer: InclusiveFinancingContractSignRenderer,
};

registry.category("views").add("ifs_contract_sign", InclusiveFinancingContractSignView);