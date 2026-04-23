/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import '@mail/models/messaging';

registerModel({
    name: 'AttachmentFieldsView',
    fields: {
        id: attr({
            identifying: true,
        }),
        model: attr({
            identifying: true,
        }),
        allAttachments: many('Attachment', {
            inverse: 'fieldsView',
            isCausal: true,
        }),
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', {
            compute() {
                return (this.allAttachments && this.allAttachments.length > 0)
                    ? {}
                    : clear();
            },
            inverse: 'attachmentFieldsViewOwner',
        }),
    },
});
