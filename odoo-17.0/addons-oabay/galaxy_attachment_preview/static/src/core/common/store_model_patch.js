/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

patch(Store, {
    /** @type {typeof import("@galaxy_attachment_preview/core/common/preview_attachment_model").PreviewAttachment} */
    PreviewAttachment: undefined,
    // setup() {
    //     super.setup();
    //     this.PreviewAttachment = Record.many("PreviewAttachment");
    // },
});