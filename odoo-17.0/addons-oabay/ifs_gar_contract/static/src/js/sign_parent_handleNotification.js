/** @odoo-module **/

import {
    formView
  } from "@web/views/form/form_view";
  import {
    registry
  } from "@web/core/registry";
  import {
    onMounted,
    onWillDestroy
  } from "@odoo/owl";
  
  export class SignParentHandleNotificationRenderer extends formView.Renderer {
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
            case 'ifs_contract_parent_close':
              this.env.model.load()
              return
            default:
              return
          }
        }
      });
      await Promise.all(proms);
    }
  }
  
  export const SignParentHandleNotificationView = {
    ...formView,
    Renderer: SignParentHandleNotificationRenderer,
  };
  
  registry.category("views").add("sign_parent_handleNotification", SignParentHandleNotificationView);