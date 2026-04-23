/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import { fileTypeMagicWordMap } from '@web/views/fields/image/image_field';

import '@mail/models/attachment_image';

registerPatch({
    name: 'AttachmentImage',
    fields: {

        imageUrl: ({
            compute() {
                if (!this.attachment) {
                    return;
                }
                if (this.attachment.fieldsView && this.attachment.fieldsView.model) {
                    if (this.attachment.base64Data) {
                        const magic = fileTypeMagicWordMap[this.attachment.base64Data[0]] || "png";
                        return `data:image/${magic};base64,${this.attachment.base64Data}`;
                    }
                    const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}&${Math.random()}` : `?${Math.random()}`;
                    return `/web/image/${this.attachment.fieldsView.model}/${this.attachment.fieldsView.id}/${this.attachment.fieldName}/${this.width}x${this.height}${accessToken}`;
                }
                return this._super(...arguments);
            },
        }),
        height: ({
            compute() {
                if (this.attachmentList.attachmentFieldsViewOwner) {
                    return 160;
                }
                return this._super(...arguments);
            },
        }),
        hasDownloadButton: ({
            compute() {
                if (!this.attachment || !this.attachmentList || this.attachment.base64Data) {
                    return clear();
                }
                return this._super(...arguments);
            },
        }),
    },
});
