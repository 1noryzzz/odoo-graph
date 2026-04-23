/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';
import { onMounted } from "@odoo/owl";

import { usePartnerWizard } from './partner_wizard_hook';

export class IfsPartnerFormController extends FormController {
    setup() {
        super.setup();
        this.partnerWizard = usePartnerWizard();

        onMounted(() => {
            if (this.props.context.open_wizard) {
                this.partnerWizard(this.props.context.wizard_action);
            }
        });
    }
}

registry.category('views').add('ifs_partner_form', {
    ...formView,
    Controller: IfsPartnerFormController,
});
