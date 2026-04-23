/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { onChange } from "@mail/utils/common/misc";
import { assignDefined } from "@mail/utils/common/misc";

import { deserializeDateTime } from "@web/core/l10n/dates";

export const getOssClientNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();
/**
 * @typedef Data
 * @property {string} activity_category
 * @property {[number, string]} activity_type_id
 * @property {string|false} activity_decoration
 * @property {boolean} can_write
 * @property {'suggest'|'trigger'} chaining_type
 * @property {string} create_date
 * @property {[number, string]} create_uid
 * @property {string} date_deadline
 * @property {string} date_done
 * @property {string} display_name
 * @property {boolean} has_recommended_activities
 * @property {string} icon
 * @property {number} id
 * @property {Object[]} mail_template_ids
 * @property {string} note
 * @property {number|false} previous_activity_type_id
 * @property {number|false} recommended_activity_type_id
 * @property {string} res_model
 * @property {[number, string]} res_model_id
 * @property {number} res_id
 * @property {string} res_name
 * @property {number|false} request_partner_id
 * @property {'overdue'|'planned'|'today'} state
 * @property {string} summary
 * @property {[number, string]} user_id
 * @property {string} write_date
 * @property {[number, string]} write_uid
 */
export class OssClient extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").OssClient>} */
    static records = {};
    /** @returns {import("models").OssClient} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").OssClient|import("models").OssClient[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new(data) {
        /** @type {import("models").OssClient} */
        const ossClient = super.new(data);
        // onChange(attachment, ["extension", "name"], () => {
        //     if (!attachment.extension && attachment.name) {
        //         attachment.extension = attachment.name.split(".").pop();
        //     }
        // });
        return ossClient;
    }

    /** @type {number} */
    id;
    originThread = Record.one("Thread");
    ossFiles = Record.many("OssFile");
    /** @type {string} */
    resModel;
    /** @type {boolean} */
    allowUpload = true;
    /** @type {string} */
    acceptFileType = "*";
    /** @type {boolean} */
    multiUpload = true;
    /** @type {number} */
    maxPerBatch = 100;
    /** @type {string} */
    defaultFolder = 'tmp/';
    /** @type {string} */
    bucket;
    /** @type {string} */
    region;
    /** @type {string} */
    endpoint;
    /** @type {string} */
    accessKeyId;
    /** @type {string} */
    accessKeySecret;
    /** @type {string} */
    securityToken;
    /** @type {[number, string]} */
    expiration;
    refreshStsToken;

    get aliOssClient() {
        if (this.accessKeyId && this.securityToken) {
            return new OSS({
                region: this.region,
                bucket: this.bucket,
                accessKeyId: this.accessKeyId,
                accessKeySecret: this.accessKeySecret,
                stsToken: this.securityToken,
                refreshSTSToken: () => this.refreshStsToken(this.resModel),
                refreshSTSTokenInterval: 300000,
            });
        }
    }
}

OssClient.register();
