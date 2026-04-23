/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { menuService } from '@web/webclient/menus/menu_service';

patch(menuService, {
    async start(env) {
        let menu_service = await super.start(env);
        let currentAppId;
        let currentItemId;
        return {
            ...menu_service,
            getCurrentItemId() {
                return currentItemId
            },
            searchSecondMenu(currentId) {
                const menu = menu_service.getAll().find(menuData => {
                    return menuData.children.some(child => currentId === child);
                });
                if (menu) {
                    return (menu.id === menu.appID ? this.getMenu(currentId) : this.searchSecondMenu(menu.id));
                }
            },
            getMenu(menuID) {
                const menu = menu_service.getMenu(menuID);
                if (menu && !menu.actionID && menu.children.length > 0) {
                    menu.actionID = this.getMenu(menu.children[0]).actionID
                }
                return menu;
            },
            async selectMenu(menu) {
                menu = typeof menu === "number" ? this.getMenu(menu) : this.getMenu(menu.id);
                if (!menu.actionID) {
                    return;
                }
                await env.services.action.doAction(menu.actionID, { clearBreadcrumbs: true });
                this.setCurrentMenu(menu);
            },
            setCurrentMenu(menu) {
                menu = typeof menu === "number" ? this.getMenu(menu) : menu;
                if (menu) {
                    currentItemId = menu.id
                    currentAppId = menu.appID;
                    env.bus.trigger("MENUS:APP-CHANGED");
                    // FIXME: lock API: maybe do something like
                    // pushState({menu_id: ...}, { lock: true}); ?
                    env.services.router.pushState({ menu_id: menu.id }, { lock: true });
                }
            },
            getCurrentApp() {
                if (!currentAppId) {
                    return;
                }
                return this.getMenu(currentAppId);
            },
        }
    },
});
