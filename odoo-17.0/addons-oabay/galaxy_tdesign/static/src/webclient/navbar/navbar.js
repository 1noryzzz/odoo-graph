/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from '@web/webclient/navbar/navbar';
import { session } from "@web/session";
const { onMounted } = owl;

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.hide_menu = false
        if (window.location.href.indexOf('hide_menu') !== -1) {
            this.hide_menu = true
        }

        onMounted(() => {
            if (this.hide_menu) {
                $("#closeSidebar").hide();
                $("#openSidebar").show();
                $("#sidebar_panel").css({ 'display': 'none' });
                $(".top_heading").addClass("sidebar_close");
                $(".o_action_manager").addClass("sidebar_close");
            }
        });
    },

    getWebIcon(menu) {
        if (menu.webIconData) {
            const prefix = menu.webIconData.startsWith("P")
                ? "data:image/svg+xml;base64,"
                : "data:image/png;base64,";
            return menu.webIconData.startsWith("data:image")
                ? menu.webIconData
                : prefix + menu.webIconData.replace(/\s/g, "");
        } else if(menu.webIcon) {
            return menu.webIcon.replace(',', '/');
        }
    },

    get currentAppSections() {
        const currentItemId = this.menuService.getCurrentItemId()
        let currentApp = this.menuService.getMenu(currentItemId)
        if (currentApp && currentApp.id !== currentApp.appID) {
            currentApp = this.menuService.searchSecondMenu(currentItemId)
        }
        const a = (currentApp && this.menuService.getMenuAsTree(currentApp.id).childrenTree)
        return (
            (a && a.length !== 0 && typeof a !== 'undefined' ? a : (typeof currentApp !== 'undefined' && currentApp.length !== 0 ? [currentApp] : []))
        );
    },

    get sessionMenuSetting() {
        const menuStyle = session.main_menu_style
        return menuStyle
    },

    set sessionMenuSetting(_) {},

    get currentAppId() {
        let currentApp = this.menuService.getCurrentApp();
        if (!currentApp) {
            let currentAppId = this.menuService.getMenu("root").children[0]
            currentApp = this.menuService.getMenu(currentAppId)
        }
        return currentApp
    },

    set currentAppId(_) {},
});