/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { getOssClientNextTemporaryId } from "@galaxy_aliyun/core/common/oss_client_model";

export class OssClientService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.rpc = services.rpc;
        this.notificationService = services.notification;
        this.router = services.router;
        this.ui = services.ui;
        this.user = services.user;

        this.thread = undefined;
        this.ossClient = undefined;
    }

    async _refreshStsToken(res_model) {
        return this.convertData(await this.orm.silent.call(res_model, "get_oss_sts", [[]]));
    }

    async fetchStsToken(res_model) {
        const stsDate = await this._refreshStsToken(res_model);
        if (!stsDate) {
            return;
        }
        this.thread = this.store.Thread.insert({ model: res_model, id: -1 });
        this.ossClient = this.store.OssClient.insert({
            ...stsDate,
            id: getOssClientNextTemporaryId(),
            resModel: res_model,
            originThread: this.thread,
            refreshStsToken: this._refreshStsToken.bind(this)
        });
    }

    convertData(data) {
        const data2 = {};
        if ('Endpoint' in data) {
            data2.endpoint = data.Endpoint;
        }
        if ('Bucket' in data) {
            data2.bucket = data.Bucket;
        }
        if ('Region' in data) {
            data2.region = data.Region;
        }
        if ('SecurityToken' in data) {
            data2.securityToken = data.SecurityToken;
        }
        if ('AccessKeyId' in data) {
            data2.accessKeyId = data.AccessKeyId;
        }
        if ('AccessKeySecret' in data) {
            data2.accessKeySecret = data.AccessKeySecret;
        }
        if ('Expiration' in data) {
            data2.expiration = data.Expiration;
        }
        if ('AcceptFileType' in data) {
            data2.acceptFileType = data.AcceptFileType;
        }
        if ('MaxPerBatch' in data) {
            data2.maxPerBatch = data.MaxPerBatch;
        }
        return data2;
    }
}

export const ossClientService = {
    dependencies: [
        "mail.store",
        "orm",
        "rpc",
        "notification",
        "router",
        "mail.message",
        "mail.persona",
        "mail.out_of_focus",
        "ui",
        "user",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new OssClientService(env, services);
    },
};

registry.category("services").add("galaxy_aliyun.oss_client", ossClientService);
