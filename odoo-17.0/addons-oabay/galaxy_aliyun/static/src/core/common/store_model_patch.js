/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

patch(Store, {
    /** @type {typeof import("@galaxy_aliyun/core/common/oss_client_model").OssClient} */
    OssClient: undefined,
    /** @type {typeof import("@galaxy_aliyun/core/common/oss_file_model").OssFile} */
    OssFile: undefined,
});