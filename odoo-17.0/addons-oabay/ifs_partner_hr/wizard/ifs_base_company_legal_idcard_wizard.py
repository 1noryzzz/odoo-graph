# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import UserError, RedirectWarning, MissingError


class InclusiveFinancingBaseCompanyLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.base.company.legal.idcard.wizard'
    _description = '公司根帐户身份证信息添加'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方')

    name = fields.Char('姓名')
    idcard_no = fields.Char(
        '身份证号', compute='_compute_idcard_info', store=True)
    nationality = fields.Char('民族', compute='_compute_idcard_info', store=True)
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '未知')
    ], string='性别', compute='_compute_idcard_info', store=True)
    birthday = fields.Date('出生日期', compute='_compute_idcard_info', store=True)
    address = fields.Char(
        '证件地址', compute='_compute_idcard_info', store=True, readonly=False)
    authority = fields.Char('签发机关', compute='_compute_idcard_info', store=True)
    start_date = fields.Date(
        '起始日期', compute='_compute_idcard_info', store=True)
    end_date = fields.Date('失效日期', compute='_compute_idcard_info', store=True)
    front_image = fields.Image('身份证人像面')
    back_image = fields.Image('身份证国徽面')
    current_step = fields.Integer(
        compute='_compute_current_step', string='current_step')

    @api.depends('front_image', 'back_image')
    def _compute_current_step(self):
        for record in self:
            if record.front_image and record.back_image:
                record.current_step = 3
            elif record.front_image:
                record.current_step = 2
            else:
                record.current_step = 1

    @api.depends('front_image', 'back_image')
    def _compute_idcard_info(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = self.env['galaxy.external.api']
        for record in self:
            try:
                if record.back_image:
                    back_resp = ExternalApi.invoke(ocr_api_code, body={
                        'image': record.back_image.decode('utf-8'),
                        'configure': {'side': 'back'}
                    }).retrieve_response('BACK')
                    record.update({
                        'authority': back_resp.raw.get('issue'),
                        'start_date': back_resp.raw.get('start_date'),
                        'end_date': back_resp.raw.get('end_date'),
                    })
                elif record.front_image:
                    face_resp = ExternalApi.invoke(ocr_api_code, body={
                        'image': record.front_image.decode('utf-8'),
                        'configure': {'side': 'face'}
                    }).retrieve_response('FACE')
                    check_resp = ExternalApi.invoke(check_api_code, body={
                        'id_number': face_resp.raw.get('num'),
                        'name': face_resp.raw.get('name'),
                    }).retrieve_response('CHECK')

                    if check_resp.raw.get('state'):
                        record.update({
                            'name': face_resp.raw.get('name'),
                            'idcard_no': face_resp.raw.get('num'),
                            'nationality': face_resp.raw.get('nationality'),
                            'gender': face_resp.raw.get('sex'),
                            'birthday': face_resp.raw.get('birth'),
                            'address': face_resp.raw.get('address'),
                        })
                    else:
                        raise UserError(_("身份信息认证失败！"))
            except UserError as e:
                self._re_upload(e.name)

    def _re_upload(self, message):
        raise RedirectWarning(
            message=message,
            button_text=_("重新上传"),
            action={
                'name': self._description,
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'views': [[False, 'form']],
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                }
            },
        )

    def action_confirm(self):
        user_info = self.read(
            ['name', 'idcard_no', 'nationality', 'gender', 'birthday', 'address', 'authority', 'start_date', 'end_date', 'front_image', 'back_image'])[0]
        user_info.pop('id')

        employee = self.ifs_company_id.sudo().root_employee_id
        if not employee.exists():
            raise MissingError(_('法人信息不存在！'))
        elif employee.name != user_info.get('name'):
            self._re_upload(_('法人姓名与身份证信息不一致！'))
        idcard = self.env['hr.employee.idcard'].sudo().search([
            ('idcard_no', '=', self.idcard_no)
        ])
        if idcard.exists() and idcard.employee_ids.filtered(
                lambda e: e.id != employee.id and e.company_id.id == self.ifs_company_id.company_id.id).exists():
            self._re_upload(_('身份证号码已存在，并已被其他用户绑定！'))

        if idcard.exists():
            idcard.write(user_info)
        else:
            idcard = self.env['hr.employee.idcard'].create(user_info)

        employee.write({
            'gender': self.gender,
            'birthday': self.birthday,
            'idcard_id': idcard.id,
        })

    def nosave_redo(self):
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
