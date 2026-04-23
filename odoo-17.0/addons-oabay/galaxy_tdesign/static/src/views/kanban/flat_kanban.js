/** @odoo-module alias=flat.kanban **/

import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { FlatControlPanel } from '@galaxy_tdesign/search/control_panel/control_panel';

export const FlatKanban = {
  ...kanbanView,
  ControlPanel: FlatControlPanel,
};

registry.category("views").add("flat_kanban", FlatKanban);