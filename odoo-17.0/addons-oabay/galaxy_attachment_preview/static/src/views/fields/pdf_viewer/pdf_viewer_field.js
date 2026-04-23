/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { PdfViewerField, pdfViewerField } from "@web/views/fields/pdf_viewer/pdf_viewer_field";
import { url } from "@web/core/utils/urls";
import { onPatched, onWillRender, onWillDestroy, useState } from "@odoo/owl";
import { imageCacheKey } from "@web/views/fields/image/image_field";

patch(PdfViewerField, {
    props: {
        ...PdfViewerField.props,
        placeholder: { type: String, optional: true },
        description: { type: String, optional: true },
        previewPlaceholder: { type: String, optional: true },
        width: { type: String, optional: true },
        height: { type: String, optional: true },
    },
});

patch(PdfViewerField.prototype, {
    setup() {
        super.setup();

        this.store = useService("mail.store");
        this.fileViewer = useFileViewer();
        this.thread = this.store.Thread.insert({ model: this.props.record.resModel, id: this.props.record.resId || -1 });
        this.attachment = null;
        this.state = useState({
            isValid: true,
            isUploading: false,
        });
        this._insertOrUpdateFromProps();

        onPatched(() => {
            this.thread = this.store.Thread.insert({ model: this.props.record.resModel, id: this.props.record.resId || -1 });
            if (!this.env.inDialog && this.props.record.resId) {
                if (this.props.record.data[this.props.name]) {
                    this._insertOrUpdateFromProps();
                } else if (this.attachment) {
                    this.attachment.delete();
                }
            } else {
                // this.state.isUploading = false;
            }
        });
        
        onWillRender(() => {
            this.env.bus.addEventListener("RPC:RESPONSE", this.unblock.bind(this));
        });

        onWillDestroy(() => {
            if (this.attachment) {
                this.attachment.delete();
            }
            this.env.bus.removeEventListener("RPC:RESPONSE", this.unblock.bind(this));
        });
    },

    unblock() {
        this.state.isUploading = false;
    },

    get currentAttachment() {
        if (!this.attachment) {
            this.attachment = this.store.PreviewAttachment.insert({
                id: this.props.name + '_' + this.props.record.resId,
                rid: this.props.record.resId,
                filename: this.props.record.data.name,
                name: this.props.name,
                type: 'url',
                url: this.url,
                mimetype: "application/pdf",
                originThread: this.thread,
            });
        }
        return this.attachment;
    },

    _insertOrUpdateFromProps() {
        if (this.props.record.data[this.props.name]) {
            this.attachment = this.store.PreviewAttachment.insert({
                id: this.props.name + '_' + this.props.record.resId,
                rid: this.props.record.resId,
                filename: this.props.record.data.name,
                name: this.props.name,
                type: 'url',
                url: this.url,
                mimetype: "application/pdf",
                originThread: this.thread,
            });
        }
        // this.state.isUploading = false;
    },

    onOpenPreview(el) {
        this.fileViewer.open(this.currentAttachment, this.thread.previewAttachments);
    },

    async onFileUploaded(info) {
        this.state.isUploading = true;
        await super.onFileUploaded(info);
    },

    get additinalClassName() {
        if (this.props.value) return ' o_AttachmentImage';
        return '';
    },

    get previewImg() {
        if (this.state.isValid) {
            if (!this.rawCacheKey) {
                this.rawCacheKey = this.props.record.data.__last_update;
            }
            return url("/web/image", {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.previewImage || this.props.name + '_picture',
                unique: imageCacheKey(this.rawCacheKey),
            });
        }
        return this.placeholder;
    },

    get placeholder() {
        if (this.props.value) {
            return this.props.previewPlaceholder;
        }

        return this.props.placeholder;
    },

    get description() {
        return this.props.description;
    },

});

patch(pdfViewerField, {
    extractProps: ({ attrs, options }) => ({
        fileNameField: attrs.filename,
        previewPlaceholder: options.previewPlaceholder,
        previewImage: options.previewImage,
        width: options.size && Boolean(options.size[0]) ? options.size[0] : attrs.width,
        height: options.size && Boolean(options.size[1]) ? options.size[1] : attrs.height,
        placeholder: options.placeholder ? options.placeholder : attrs.placeholder,
        description: options.description,
    }),
});