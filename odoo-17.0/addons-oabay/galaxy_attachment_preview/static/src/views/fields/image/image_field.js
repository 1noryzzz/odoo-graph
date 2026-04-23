/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { patch } from "@web/core/utils/patch";
import { imageField, ImageField } from "@web/views/fields/image/image_field";
import { onPatched, onWillRender, onWillDestroy, useState } from "@odoo/owl";

patch(ImageField, {
    props: {
        ...ImageField.props,
        placeholder: { type: String, optional: true },
        description: { type: String, optional: true },
    },
    defaultProps: {
        ...ImageField.defaultProps,
        placeholder: "/web/static/img/placeholder.png",
    },
});
// ImageField.props = {
//     ...ImageField.props,
//     placeholder: { type: String, optional: true },
//     description: { type: String, optional: true },
// };
// ImageField.defaultProps = {
//     ...ImageField.defaultProps,
//     placeholder: "/web/static/img/placeholder.png",
// };
patch(ImageField.prototype, {
    setup() {
        super.setup();

        this.store = useService("mail.store");
        this.fileViewer = useFileViewer();
        this.attachment = undefined;
        this.thread = this.store.Thread.insert({ model: this.props.record.resModel, id: this.props.record.resId || -1 });
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
                this.state.isUploading = false;
            }
        });

        onWillRender(() => {
            this.env.bus.addEventListener("RPC:REQUEST", this.block.bind(this));
            this.env.bus.addEventListener("RPC:RESPONSE", this.unblock.bind(this));
        });

        onWillDestroy(() => {
            if (this.attachment) {
                this.attachment.delete();
            }
            this.env.bus.removeEventListener("RPC:REQUEST", this.block.bind(this));
            this.env.bus.removeEventListener("RPC:RESPONSE", this.unblock.bind(this));
        });
    },

    block() {
        this.state.isUploading = true;
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
                url: this.getUrl(this.props.name),
                mimetype: "image/jpeg",
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
                url: this.getUrl(this.props.name),
                mimetype: "image/jpeg",
                originThread: this.thread,
            });
        }
        this.state.isUploading = false;
    },

    onOpenPreview() {
        this.fileViewer.open(this.currentAttachment, this.thread.previewAttachments);
    },

    async onFileUploaded(info) {
        this.state.isUploading = true;
        await super.onFileUploaded(info);
    },

    getUrl(previewFieldName) {
        if (this.state.isValid && this.props.record.data[this.props.name]) {
            return super.getUrl(previewFieldName);
        }
        return this.props.placeholder;
    },

    get additinalClassName() {
        if (this.props.value) return ' o_AttachmentImage';
        return '';
    },

    get description() {
        return this.props.description;
    },
});

patch(imageField, {
    extractProps: ({ attrs, options }) => ({
        enableZoom: options.zoom,
        zoomDelay: options.zoom_delay,
        previewImage: options.preview_image,
        acceptedFileExtensions: options.accepted_file_extensions,
        width: options.size && Boolean(options.size[0]) ? options.size[0] : attrs.width,
        height: options.size && Boolean(options.size[1]) ? options.size[1] : attrs.height,
        reload: "reload" in options ? Boolean(options.reload) : true,
        placeholder: options.placeholder ? options.placeholder : attrs.placeholder,
        description: options.description,
    }),
});
