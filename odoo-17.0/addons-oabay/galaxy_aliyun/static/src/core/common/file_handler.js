/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, useRef, useState } from "@odoo/owl";

export class FileUploaderOss extends Component {
    setup() {
        this.notification = useService("notification");
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            isUploading: false,
        });
    }

    /**
     * @param {Event} ev
     */
    async onFileChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        const { target } = ev;
        this.state.isUploading = true;
        try {
            await this.props.onUploaded(ev.target.files);
        }
        finally {
            this.state.isUploading = false;
        }
        target.value = null;
        if (this.props.multiUpload && this.props.onUploadComplete) {
            this.props.onUploadComplete({});
        }
    }

    async onSelectFileButtonClick(ev) {
        if (this.props.onClick) {
            const ok = await this.props.onClick(ev);
            if (ok !== undefined && !ok) {
                return;
            }
        }
        this.fileInputRef.el.click();
    }
}

FileUploaderOss.template = "galaxy_aliyun.FileUploaderOss";
FileUploaderOss.props = {
    onClick: { type: Function, optional: true },
    onUploaded: Function,
    onUploadComplete: { type: Function, optional: true },
    multiUpload: { type: Boolean, optional: true },
    inputName: { type: String, optional: true },
    fileUploadClass: { type: String, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
    slots: { type: Object, optional: true },
    showUploadingText: { type: Boolean, optional: true },
};
FileUploaderOss.defaultProps = {
    showUploadingText: true,
};
