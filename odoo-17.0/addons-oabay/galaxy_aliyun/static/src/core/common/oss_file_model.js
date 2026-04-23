/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { onChange } from "@mail/utils/common/misc";
import { assignDefined } from "@mail/utils/common/misc";

import { FileModelMixin } from "@web/core/file_viewer/file_model";
import { deserializeDateTime } from "@web/core/l10n/dates";


export class OssFile extends FileModelMixin(Record) {
    static id = "id";
    /** @type {Object.<number, import("models").OssFile>} */
    static records = {};
    /** @returns {import("models").OssFile} */
    static get(data) {
        return super.get(data);
    }
    update(data) {
        super.update(data);
        this.ossClient?.ossFiles.sort((a1, a2) => (a1.id > a2.id ? 1 : -1));
    }

    ossClient = Record.one("OssClient", { inverse: "ossFiles" });
    /** @type {string} */
    resModel;
    /** @type {[number, string]} */
    resId;
    size;
    blob;
    /** @type {string} */
    state;
    /** @type {number} */
    progress;
}

OssFile.register();
