/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { OssUploadProgress } from "../../oss_upload_progress";
import { OssUploadingBlockUI } from "../../oss_uploading_block_ui";

const mainComponentRegistry = registry.category("main_components");

export class OssUploadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.notificationService = services["notification"];
        this.orm = services.orm;

        this.uploadedFiles = [];
    }

    async uploadFiles(hooker, files) {
        const options = {
            parallel: 4,
            partSize: 1024 * 1024,
        };
        const blockComponent = {
            class: OssUploadProgress,
            props: {
                stopUpload: () => hooker.state.isUploading = false,
                totalSteps: hooker.state.fileCount,
                uploadProgress: hooker.state.uploadProgress,
            },
        };
        this.block(_t("Uploading..."), blockComponent);

        let step = 1;
        for (const file of files) {
            try {
                hooker.state.filename = file.name;
                const objName = hooker.ossClient.defaultFolder + new Date().getTime() + '.' + file.name;
                await hooker.ossClient.aliOssClient.multipartUpload(objName, file, {
                    ...options,
                    mime: file.type,
                    progress: (p, cpt, res) => {
                        Object.assign(hooker.state.uploadProgress, {
                            value: (p * 100).toFixed(2),
                            step: step,
                        });
                    },
                });

                //单个文件上传阿里云完成后，调用后端保存
                const record = await this.orm.silent.call(hooker.ossClient.resModel, "create_with_oss", [[{
                    file_name: file.name,
                    oss_key: objName
                }]]);

                if (record.result === 1) {
                    this.uploadedFiles.push({
                        res_id: record.ids[0],
                        file_name: file.name,
                        oss_key: objName,
                    });
                }

                if (!hooker.state.isUploading) break;
                step++;
            } catch (e) {
                this.unblock();
                Object.assign(hooker.state, {
                    previewError: e.message,
                });
                hooker.props.onOssUploaded({
                    'result': 'err',
                    'msg': '网络异常，请重试！'
                });
                break;
            }
        }

        const res_ids = this.uploadedFiles.reduce((prev, curr) => [...prev, curr.res_id], []);
        const res = await this.orm.silent.call(hooker.ossClient.resModel, "betch_update_finish", [[res_ids]]);

        this.unblock();
        hooker.props.onOssUploaded(res);
    }

    /**
     * A custom BlockUI is required to add the progress bar or text when blocking
     * the UI, without modifying the core ui service to handle a generic use case
     */
    block(message, blockComponent) {
        mainComponentRegistry.add(
            "OssUploadingBlockUI",
            {
                Component: OssUploadingBlockUI,
                props: {
                    blockComponent,
                    message,
                },
            },
            { force: true }
        );
    }

    unblock() {
        mainComponentRegistry.remove("OssUploadingBlockUI");
    }
}

export const ossUploadService = {
    dependencies: ["notification", "orm"],
    start(env, services) {
        return new OssUploadService(env, services);
    },
};

registry.category("services").add("galaxy_aliyun.oss_upload", ossUploadService);
