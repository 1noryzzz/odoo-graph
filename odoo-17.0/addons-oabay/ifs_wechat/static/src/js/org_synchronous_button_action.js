/** @odoo-module */

import {
  registry
} from "@web/core/registry";

export function _on_click_synchronous(env, action) {
    const params = action.params || {};
    this.actionService.doActionButton({
      name: 'org_synchronous',
      type: "object",
      resModel: 'oa.org.synchronous',
      context: params.get('start_index'),
    });
    console.log('+++++++++++++', params.get('start_index'))
  };

registry.category("actions").add("org_synchronous_button", _on_click_synchronous);