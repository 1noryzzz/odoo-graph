# -*- coding: utf-8 -*-

import base64
import hashlib
import io
import json
import logging
import random
import requests
import string
import time


from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

paths = {
    'PING': '/v2/ping',
    'APPLY_SIGN': '/v2/sign/applySign',  # 签约后缀
    'APP_SGIN_LINK': '/v2/sign/link',  # 获取签约连接地址后缀
    'APP_SGIN_STATUS': '/v2/sign/status',  # 获取签约状态
    'APP_LINK_ANONY_DETAIL': '/v2/sign/linkAnonyDetail',  # 获取查看合同连接
    'APP_DOWNLOADLINK': '/v2/sign/linkFile',  # 获取签约最新文件下载链接
    'AUTHENTI_CATIONREAL_NAME': '/v2/user/organizationCreate',  # 企业实名认证信息提交审核
    'ORG_REAPPLY': '/v2/user/organizationReapply',  # 企业实名认证重传
    'ORG_ANIZATION_STATUS': "/v2/user/organizationAuditStatus",  # 企业实名认证状态查询
}


class InclusiveFinancingBaseCompanyMixin(models.AbstractModel):
    _inherit = 'ifs.base.company'

    jzq_account = fields.Char('君子签账号', help='君子签平台账号')

    def certificate_company(self):
        super(InclusiveFinancingBaseCompanyMixin, self).certificate_company()

        if not self.jzq_account:
            seq = self.env['ir.sequence'].next_by_code('ifs.base.company.jzq_acc')
            self.jzq_account = (seq or '') + (self.seq_code or '') + ('@oabay.com')

        auth_res_json = self.env['galaxy.external.api'].invoke(
            "AUTHENTI-CATIONREAL-NAME",
            body={
                'name': self.company_id.name,
                'emailOrMobile': self.jzq_account,
                'organizationType': 0,
                'identificationType': 1,
                'organizationRegNo': self.raw.get('credit_no'),
                'legalName': self.legal_id.name,
            },
            files={
                'organizationRegImg': self.business_license
            }).retrieve_response("AUTHENTI-CATIONREAL-NAME-RESULT", True).raw

        # (SERVICE_URL, APP_KEY, APP_SECRET) = self._get_param_config()
        # business = self.business_id
        # principal = self.principal_id
        # auth_data = {
        #     "name": business.name,               # 公司名称（注：企业名称如含括号请传中文的括号）
        #     'emailOrMobile': principal.email,   # 邮箱(不填入时系统生成)
        #     'organizationType': 0,               # 组织类型 0企业,1事业单位
        #     'identificationType': 1,             # 证件类型：0多证,1多证合一
        #     'organizationRegNo': self.credit_no,  # 营业执照号或事业单位事证号或统一社会信用代码
        #     'legalName': business.legal_person,  # 法人姓名
        # }
        # files = {
        #     "organizationRegImg": io.BytesIO(base64.b64decode(self.business_license)),
        # }

        # (nonce, ts, sign) = self._gen_sign(APP_KEY, APP_SECRET)
        # auth_data["nonce"] = nonce
        # auth_res = requests.post(''.join([
        #     SERVICE_URL,
        #     paths.get('AUTHENTI_CATIONREAL_NAME'),
        #     '?',
        #     'app_key=%s' % APP_KEY,
        #     '&ts=%d' % ts,
        #     '&sign=%s' % sign,
        #     # '&nonce=%s' % nonce,
        #     '&encry_method=sha1',
        # ]), data=auth_data, files=files).text
        # auth_res_json = json.loads(auth_res)

        # TODO: 如果企业认证成功，则改变状态； 不成功则抛出异常
        if auth_res_json['success']:
            return
        else:
            raise ValidationError(
                ' '.join(['认证失败,', auth_res_json.get('msg')]))

    def _gen_sign(self, APP_KEY, APP_SECRET):
        nonce = ''.join(random.sample(
            string.ascii_letters + string.digits, 32))
        ts = int(time.time())

        sign_str = ''.join([
            'nonce', nonce, 'ts', str(ts),
            'app_key', APP_KEY, 'app_secret', APP_SECRET
        ])
        return (nonce, ts, hashlib.sha1(sign_str.encode('utf-8')).hexdigest())

    def _get_param_config(self):
        cfg = self.env['ir.config_parameter'].sudo()
        test_env = cfg.get_param('ifs.contract.sign.jzq.test.env', False)
        if test_env:
            serviceUrl = cfg.get_param(
                'ifs.contract.sign.jzq.service.url.test', False)
            appKey = cfg.get_param('ifs.contract.sign.jzq.app.key.test', False)
            appSecret = cfg.get_param(
                'ifs.contract.sign.jzq.app.secret.test', False)
        else:
            serviceUrl = cfg.get_param(
                'ifs.contract.sign.jzq.service.url', False)
            appKey = cfg.get_param('ifs.contract.sign.jzq.app.key', False)
            appSecret = cfg.get_param(
                'ifs.contract.sign.jzq.app.secret', False)
        return (serviceUrl, appKey, appSecret)

    @api.model_callback
    def organization_sync(self, entry, message, callback_action, callback_log):
        _logger.info('企业实名认证回调：%s' % str(message))
        try:
            req_data_json = json.loads(message.get("data"))
            registration = self.env['res.company.business.registration'].search(
                [('credit_no', '=', req_data_json.get("organizationRegNo"))])
            res_company = registration.company_id
            partner = {
                "factor": "ifs.partner.factor",
                "franchisee": "ifs.partner.factor",
                "funder": "ifs.partner.factor",
                "merchant": "ifs.partner.factor",
                "supplier": "ifs.partner.factor",
            }
            table_name = partner.get(res_company.ifs_partner, False)
            if table_name:
                company = self.env[table_name].search(
                    [('credit_no', '=', message.get("organizationRegNo"))])
                if req_data_json.get("status") == 1:
                    company.write({
                        'org_auth_state': 'certified'
                    })
        except Exception:
            return False
        return True
