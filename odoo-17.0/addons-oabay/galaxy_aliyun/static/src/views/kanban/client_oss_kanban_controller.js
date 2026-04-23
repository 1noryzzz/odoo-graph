/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { OssClient } from "@galaxy_aliyun/core/common/oss_client";

import { useRef } from "@odoo/owl";

export class ClientOssKanbanController extends KanbanController {
  static components = {
    ...KanbanController.components,
    OssClient,
  };

  setup() {
    super.setup();
    this.rootRef = useRef("root");
  }

  async onOssUploaded(res) {
    if (res.result !== 'err') {
      this.model.notification.add(_t("成功上传 " + res.result + " 个文件！"), {
        type: "success",
      });
      await this.model.root.load();
      this.render(true);
    } else {
      this.model.notification.add(res.msg, {
        type: "danger",
      });
    }

    if (res.next_action) {
      this.env.services.action.doAction(res.next_action, {
        onClose: async () => {
          await this.model.root.load();
          this.render(true);
        }
      });
    }
  }
}
