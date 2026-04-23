/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { fileTypeMagicWordMap } from '@web/views/fields/image/image_field';

import '@mail/models/messaging';
import '@mail/models/attachment';

registerPatch({
    name: 'Attachment',
    fields: {
        fieldsView: one('AttachmentFieldsView', {
            inverse: 'allAttachments',
        }),
        fieldName: attr({}),
        base64Data: attr({}),
        objectUrl: attr({}),
        ownerObject: attr({}),
        defaultSource: ({
            compute() {
                if (this.fieldsView && this.fieldsView.model) {
                    if (this.isImage) {
                        if (this.base64Data) {
                            const magic = fileTypeMagicWordMap[this.base64Data[0]] || "png";
                            return `data:image/${magic};base64,${this.base64Data}`;
                        }
                        return `/web/image/${this.fieldsView.model}/${this.fieldsView.id}/${this.fieldName}?${Math.random()}`;
                    }
                    if (this.isPdf) {
                        if (this.objectUrl) {
                            return this.objectUrl;
                        }
                        const pdf_lib = `/web/static/lib/pdfjs/web/viewer.html?file=`
                        const accessToken = this.accessToken ? `?access_token%3D${this.accessToken}&${Math.random()}` : `?${Math.random()}`;
                        return `${pdf_lib}/web/content/${this.fieldsView.model}/${this.fieldsView.id}/${this.fieldName}${accessToken}`;
                    }
                    const accessToken = this.accessToken ? `?access_token=${this.accessToken}&${Math.random()}` : `?${Math.random()}`;
                    return `/web/content/${this.fieldsView.model}/${this.fieldsView.id}/${this.fieldName}${accessToken}`;
                }

                return this._super(...arguments);
            },
        }),
        downloadUrl: ({
            compute() {
                if (this.fieldsView && this.fieldsView.model) {
                    const accessToken = this.accessToken ? `access_token=${this.accessToken}&${Math.random()}&` : `${Math.random()}&`;
                    return `/web/content/${this.fieldsView.model}/${this.fieldsView.id}/${this.fieldName}?${accessToken}download=true`;
                }
                return this._super(...arguments);
            },
        }),
        /**
         * States whether this attachment is deletable.
         */
        isDeletable: ({
            compute() {
                if (this.fieldsView && this.fieldsView.model) {
                    return false;
                }
                return this._super(...arguments);
            },
        }),
    }
});