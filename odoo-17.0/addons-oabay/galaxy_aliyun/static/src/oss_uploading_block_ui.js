/** @odoo-module **/

import { Component } from "@odoo/owl";

export class OssUploadingBlockUI extends Component {
    static props = {
        message: { type: String, optional: true },
        blockComponent: { type: Object, optional: true },
    };
    static template = "galaxy_aliyun.OssBlockUI";
}
