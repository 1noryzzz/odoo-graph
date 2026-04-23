/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';


export class IfsGarEntryFormController extends FormController {
    setup() {
        super.setup();
        this.display.controlPanel = false;
    }
    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name?.startsWith('nosave_')) {
            if (this.props.discardRecord) {
                this.props.discardRecord(this.model.root);
                return true;
            }
            await this.model.root.discard();
            if (this.props.onDiscard) {
                this.props.onDiscard(this.model.root);
            }
            return true;
        } else {
            return super.beforeExecuteActionButton(clickParams);
        }
    }
}

registry.category('views').add('ifs_gar_entry_form', {
    ...formView,
    Controller: IfsGarEntryFormController,
});
