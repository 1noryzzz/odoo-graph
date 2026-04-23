/** @odoo-module **/

import { NameAndSignature } from "@web/core/signature/name_and_signature";

export class GalaxyMobileSignature extends NameAndSignature {
    setup() {
        super.setup();
        this.state.signMode = "draw";
    }
}

GalaxyMobileSignature.template = "galaxy_tdesign.sign_name_and_signature"