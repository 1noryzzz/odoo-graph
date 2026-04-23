/** @odoo-module */

import { listView } from '@web/views/list/list_view';
import { registry } from "@web/core/registry";
import { IfsPartnerCreateListController as Controller } from './ifs_partner_create_list_controller';

export const IfsPartnerCreateListView = {
    ...listView,
    Controller,
};

registry.category("views").add("ifs_partner_create_list", IfsPartnerCreateListView);
