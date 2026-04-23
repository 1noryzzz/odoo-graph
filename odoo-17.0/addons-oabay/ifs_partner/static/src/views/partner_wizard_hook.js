/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { useComponent } from "@odoo/owl";

export function usePartnerWizard() {
    const component = useComponent();
    const action = useService("action");
    return (wizard_action) => {
        action.doAction(wizard_action, {
            onClose: async () => {
                await component.model.load();
                component.model.notify();
            },
        });
    }
}
