/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { fileTypeMagicWordMap } from '@web/views/fields/image/image_field';

import '@mail/models/attachment_viewer_viewable';

registerPatch({
    name: "AttachmentViewerViewable",
    fields: {
        imageUrl: ({
            compute() {
                if (!this.attachmentOwner) return;
                if (this.attachmentOwner.fieldsView && this.attachmentOwner.fieldsView.model) {
                    if (this.attachmentOwner.base64Data) {
                        const magic = fileTypeMagicWordMap[this.attachmentOwner.base64Data[0]] || "png";
                        return `data:image/${magic};base64,${this.attachmentOwner.base64Data}`;
                    }
                    if (this.attachmentOwner.objectUrl) {
                        return this.attachmentOwner.objectUrl;
                    }
                    const accessToken = this.attachmentOwner.accessToken
                        ? `?access_token=${this.attachmentOwner.accessToken}&${Math.random()}`
                        : `?${Math.random()}`;
                    return `/web/image/${this.attachmentOwner.fieldsView.model}/${this.attachmentOwner.fieldsView.id}/${this.attachmentOwner.fieldName}${accessToken}`;
                }
                return this._super(...arguments);
            },
        }),
    },
});
