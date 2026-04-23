/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';


export class IfsWizardFormController extends FormController {
    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name?.startsWith('nosave_')) {
            if (this.props.onSave) {
                this.props.onSave(this.model.root);
            }
            return true;
        } else {
            return super.beforeExecuteActionButton(clickParams);
        }
    }
}

registry.category('views').add('ifs_wizard_form', {
    ...formView,
    Controller: IfsWizardFormController,
});
