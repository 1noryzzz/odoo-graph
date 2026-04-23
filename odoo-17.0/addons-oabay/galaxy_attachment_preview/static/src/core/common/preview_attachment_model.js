/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { onChange } from "@mail/utils/common/misc";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { FileModelMixin } from "@web/core/file_viewer/file_model";

export class PreviewAttachment extends FileModelMixin(Record) {
    static id = "id";
    /** @type {Object.<number, import("models").PreviewAttachment>} */
    static rid = "rid";
    static records = {};
    /** @returns {import("models").PreviewAttachment} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").PreviewAttachment|import("models").PreviewAttachment[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new(data) {
        /** @type {import("models").PreviewAttachment} */
        const attachment = super.new(data);
        onChange(attachment, ["extension", "name"], () => {
            if (!attachment.extension && attachment.name) {
                attachment.extension = attachment.name.split(".").pop();
            }
        });
        return attachment;
    }

    get defaultSource() {
        if (this.urlRoute.startsWith("data:") || this.isPdf) {
            return this.urlRoute;
        } else {
            return super.defaultSource;
        }
    }

    /**
         * @returns {string}
         */
    get urlRoute() {
        if (this.uploading && this.tmpUrl) {
            return this.tmpUrl;
        }
        if (!this.id) {
            return this.url;
        }
        return this.isImage ? `/web/image/${this.originThread.model}/${this.rid}/${this.name}` : `/web/content/${this.originThread.model}/${this.rid}/${this.name}`;
    }

    update(data) {
        super.update(data);
        this.originThread?.previewAttachments.sort((a1, a2) => (a1.id < a2.id ? 1 : -1));
    }

    originThread = Record.one("Thread", { inverse: "previewAttachments" });
    /** @type {string} */
    create_date;

    get isDeletable() {
        return true;
    }

    get monthYear() {
        if (!this.create_date) {
            return undefined;
        }
        const datetime = deserializeDateTime(this.create_date);
        return `${datetime.monthLong}, ${datetime.year}`;
    }
}

PreviewAttachment.register();
