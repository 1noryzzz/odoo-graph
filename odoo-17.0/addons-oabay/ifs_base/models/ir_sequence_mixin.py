# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingIrSequenceMixin(models.AbstractModel):
    _name = 'ifs.ir.sequence.mixin'
    _description = '序号生成模型'

    seq_code = fields.Char(
        '序号', index=True, required=True, readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('seq_code'):
                vals['seq_code'] = self.env['ir.sequence'].next_by_code(
                    self._name)

        return super().create(vals_list)
