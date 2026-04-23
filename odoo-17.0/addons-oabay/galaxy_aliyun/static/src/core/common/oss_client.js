/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { FileUploaderOss } from "./file_handler";

import { Component, useState, onWillDestroy } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {string} resModel
 * @property {function} [onOssUploaded]
 * @property {import("@web/core/utils/hooks").Ref} [dropzoneRef]
 * @property {string} [className]
 * @extends {Component<Props, Env>}
 */
export class OssClient extends Component {
    static components = {
        FileUploaderOss,
    };
    static props = [
        "resModel",
        "onOssUploaded?",
        "dropzoneRef?",
        "className?",
    ];
    static defaultProps = {
        className: "",
    };
    static template = "galaxy_aliyun.OssClient";

    setup() {
        this.store = useState(useService("mail.store"));
        this.ossClientService = useService("galaxy_aliyun.oss_client");
        this.state = useState({
            active: true,
            allowUpload: false,
            multiUpload: false,
            isUploading: false,
            acceptFileType: "*", // "image/*,video/*,audio/*"
            filename: undefined,
            fileCount: 0,
            uploadMessages: [],
            uploadProgress: {
                value: 1,
                step: 1,
            },
            isPaused: false,
            previewError: "",
        });
        this.ossClientService.fetchStsToken(this.props.resModel).then(() => {
            const { allowUpload, multiUpload, acceptFileType } = this.ossClient;
            Object.assign(this.state, { allowUpload, multiUpload, acceptFileType });
        });
        this.ossUploadService = useService("galaxy_aliyun.oss_upload");
        if (this.props.dropzoneRef) {
            useDropzone(
                this.props.dropzoneRef,
                this.onDropFile.bind(this),
                "o-mail-Composer-dropzone",
                () => this.state.allowUpload
            );
        }
        onWillDestroy(() => {
            if (typeof (this.ossClient?.delete) === 'function') {
                this.ossClient?.delete();
            }
        });
    }
    get thread() {
        return this.ossClientService.thread;
    }
    get ossClient() {
        return this.ossClientService.ossClient;
    }
    onDropFile(ev) {
        if (isDragSourceExternalFile(ev.dataTransfer)) {
            //TODO: check file type
            this.onUploaded(ev.dataTransfer.files);
        }
    }
    async onUploaded(files) {
        const fileCount = files.length;
        if (fileCount < 1) {
            this.props.onOssUploaded({
                'result': 'err',
                'msg': '未选择要上传的文件！',
            });
        } else if (fileCount > this.ossClient.maxPerBatch && this.props.onOssUploaded) {
            this.props.onOssUploaded({
                'result': 'err',
                'msg': '最多只能选择' + this.ossClient.maxPerBatch + '个文件！',
            });
        } else {
            Object.assign(this.state, {
                filename: files[0].name,
                fileCount
            });

            this.state.isUploading = true;
            await this.ossUploadService.uploadFiles(this, files);
            this.state.isUploading = false;
        }
    }
}