/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';

export class IfsPartnerCreateListController extends ListController {
  onClickCreate() {
    this.model.action.doAction({
      name: '创建合作伙伴向导',
      type: 'ir.actions.act_window',
      res_model: this.model.root.resModel + '.wizard',
      res_id: undefined,
      target: 'new',
      // views: data.views || (data.resId ? [[false, 'form']] : [[false, 'list'], [false, 'form']]),
      views: [[false, 'form']],
    });
  }

  async onClickOrder() {
    const resIds = await this.getSelectedResIds();
    const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
      context: this.props.context,
    });
    if (action) {
      await this.actionService.doAction(action);
    }
    return this.actionService.doAction('stock.action_replenishment', {
      stackPosition: 'replaceCurrentAction',
    });
  }

  async onClickSnooze() {
    const resIds = await this.getSelectedResIds();
    this.actionService.doAction('stock.action_orderpoint_snooze', {
      additionalContext: { default_orderpoint_ids: resIds },
      onClose: () => {
        this.actionService.doAction('stock.action_replenishment', {
          stackPosition: 'replaceCurrentAction',
        });
      }
    });
  }

  get createButtonText() {
    let currentModel = this.model.root.resModel
    if (currentModel === 'ifs.partner.factor') {
      return '创建保理方'
    } else if(currentModel === 'ifs.partner.supplier') {
      return '创建供应方'
    } else if(currentModel === 'ifs.partner.merchant') {
      return '创建采购方'
    } else if(currentModel === 'ifs.partner.funder') {
      return '创建资金方'
    } else if(currentModel === 'ifs.partner.franchisee') {
      return '创建合伙人'
    } else if(currentModel === 'ifs.partner.lawfirm') {
      return '创建律师事务所'
    } else if(currentModel === 'ifs.partner.insurance') {
      return '创建保险公司'
    } else if(currentModel === 'ifs.partner.insurant') {
      return '创建投保人'
    } else if(currentModel === 'ifs.partner.insured') {
      return '创建被保人'
    } else if(currentModel === 'ifs.partner.channelsp') {
      return '创建服务商'
    } else {
      return '创建合作伙伴'
    }
  }

}

IfsPartnerCreateListController.template = `ifs_partner.ListView`;
