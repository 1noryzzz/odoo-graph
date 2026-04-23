/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

import '@mail/models/attachment_list';

registerPatch({
    name: 'AttachmentList',
    fields: {
        /**
         * Link with a AttachmentFieldsView to handle attachments.
         */
        attachmentFieldsViewOwner: one('AttachmentFieldsView', {
            identifying: true,
            inverse: 'attachmentList',
        }),
        attachments: ('Attachment', {
            compute() {
                if (this.attachmentFieldsViewOwner) {
                    return this.attachmentFieldsViewOwner.allAttachments;
                }
                return this._super(...arguments);
            },
        }),
    },
});
