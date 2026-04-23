/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
// 通过这个import ，确保js的加载顺序，避免user_menuitems比这个文件后载入
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";

export function changePasswrodItem(env) {
    return {
        type: "item",
        id: "changepwd",
        description: _t("修改密码"),
        callback: async function () {
            const actionDescription = await env.services.orm.call(
                "res.users", "preference_change_password", ['res.users']);
            actionDescription.views = [[false, "form"]];
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}
registry.category("user_menuitems").add('changepwd', changePasswrodItem, { force: true })

registry.category("user_menuitems").remove('documentation')
registry.category("user_menuitems").remove('support')
// registry.category("user_menuitems").remove('profile')
registry.category("user_menuitems").remove('odoo_account')
