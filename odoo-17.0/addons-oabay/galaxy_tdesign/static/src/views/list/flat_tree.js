/** @odoo-module alias=flat.tree **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { FlatControlPanel } from '@galaxy_tdesign/search/control_panel/control_panel';

export const FlatTree = {
  ...listView,
  ControlPanel: FlatControlPanel,
};

registry.category("views").add("flat_tree", FlatTree);
