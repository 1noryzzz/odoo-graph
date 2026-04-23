/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ClientOssListController } from './client_oss_list_controller'

export const clientOssListView = {
    ...listView,
    Controller: ClientOssListController,
    buttonTemplate: "galaxy_aliyun.ClientOssListView.Buttons",
};

export const clientOssListViewOnlyBatch = {
    ...listView,
    Controller: ClientOssListController,
    buttonTemplate: "galaxy_aliyun.ClientOssListView.Buttons.OnlyBatch",
};

registry.category("views").add("client_oss_list", clientOssListView);
registry.category("views").add("client_oss_list_batch", clientOssListViewOnlyBatch);
