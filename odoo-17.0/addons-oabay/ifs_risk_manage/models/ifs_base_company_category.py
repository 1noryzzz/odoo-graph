# -*- coding: utf-8 -*-

from odoo import _, models, fields


class InclusiveFinancingBaseCompanyCategory(models.Model):
    _name = 'ifs.base.company.category'
    _description = '企业架构图中间模型'

    code = fields.Char('code')
    name = fields.Char('类别')
    orient = fields.Char('方向')

    def getChildrens(self, model, model_id):
        print('model', model)
        print('model_id', model_id)
        if model and model_id:
            record = self.env[model].browse(model_id)
            if record:
                if self.code == 'stocks':
                    return [{
                        'id': shareholder.id,
                        'name': shareholder.name,
                    } for shareholder in record.shareholder_ids] if record.shareholder_ids else []
                elif self.code == 'employees':
                    return [{
                        'id': key_person.id,
                        'name': key_person.raw.get('name'),
                        'lineContent': key_person.raw.get('typeJoin')
                    } for key_person in record.key_person_ids] if record.key_person_ids else []
                elif self.code == 'historyStocks':
                    return [{
                        'id': history_stock.id,
                        'name': history_stock.raw.get('name'),
                    } for history_stock in record.history_stock_ids] if record.history_stock_ids else []
                elif self.code == 'branchs':
                    return [{
                        'id': branch.id,
                        'name': branch.name,
                    } for branch in record.branch_ids.filtered(lambda f: f.is_investment == False)] if record.branch_ids else []
                elif self.code == 'invests':
                    return [{
                        'id': branch.id,
                        'name': branch.name,
                    } for branch in record.branch_ids.filtered(lambda f: f.is_investment == True)] if record.branch_ids else []
                elif self.code == 'historyLegalPerson':
                    return [{
                        'id': history_legal_person.id,
                        'name': history_legal_person.raw.get('name'),
                    } for history_legal_person in record.history_legal_person_ids] if record.history_legal_person_ids else []
                elif self.code == 'legalPerson':
                    return [{
                        'id': record.legal_id.id,
                        'name': record.legal_id.name,
                    }]
                else:
                    return False
            else:
                return False
        else:
            return False
