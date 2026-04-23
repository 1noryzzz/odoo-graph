/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ClientOssKanbanController } from './client_oss_kanban_controller'

export const clientOssKanbanView = {
    ...kanbanView,
    Controller: ClientOssKanbanController,
    buttonTemplate: "galaxy_aliyun.ClientOssKanbanView.Buttons",
};

export const clientOssKanbanViewOnlyBatch = {
    ...kanbanView,
    Controller: ClientOssKanbanController,
    buttonTemplate: "galaxy_aliyun.ClientOssKanbanView.Buttons.OnlyBatch",
};

registry.category("views").add("client_oss_kanban", clientOssKanbanView);
registry.category("views").add("client_oss_kanban_batch", clientOssKanbanViewOnlyBatch);
