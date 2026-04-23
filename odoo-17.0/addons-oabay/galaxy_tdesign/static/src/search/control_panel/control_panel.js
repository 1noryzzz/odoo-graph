/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { FlatSearchBar } from '@galaxy_tdesign/search/search_bar/search_bar';

export class FlatControlPanel extends ControlPanel {}

FlatControlPanel.components = {
    ...ControlPanel.components,
    FlatSearchBar,
};
FlatControlPanel.template = "Flat.ControlPanel";