/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useEffect, useRef, useState } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { useBus } from "@web/core/utils/hooks";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.indicateState = useState({
            fieldIsDirty: false,
        });
        useBus(
            this.model.bus,
            "FIELD_IS_DIRTY",
            (ev) => (this.indicateState.fieldIsDirty = ev.detail)
        );
        if (this.canEdit) {
            useEffect(
                () => {
                    if (!this.model.root.isNew && this.indicatorMode === "invalid") {
                        this.saveButton.el?.setAttribute("disabled", "1");
                    } else {
                        this.saveButton.el?.removeAttribute("disabled");
                    }
                },
                () => [this.model.root.isValid]
            );
    
            this.saveButton = useRef("save");
        }
    },
    get displaySaveButtons() {
        return this.indicatorMode !== "saved";
    },
    get indicatorMode() {
        if (this.model.root.isNew) {
            return this.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.model.root.isValid) {
            return "invalid";
        } else if (this.model.root.dirty || this.indicateState.fieldIsDirty) {
            return "dirty";
        } else {
            return "saved";
        }
    }
});
