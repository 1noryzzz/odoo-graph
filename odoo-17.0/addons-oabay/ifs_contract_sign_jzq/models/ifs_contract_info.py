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

from dateutil.relativedelta import relativedelta
from odoo import _, fields, models, api
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


SERVICE_API = {
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
SIGN_STATUS = {0: "未签", 1: "已签", 2: "拒签", 3: "已保全"}
MAX_WAITING = 10


class InclusiveFinancingContractInformation(models.Model):
    _inherit = 'ifs.contract.info'

    # 这两个信息仅用于后继找回合同用
    full_name = fields.Char('甲方')
    identity_card = fields.Char('签约人证件号')
    # 1身份证, 2护照, 3台胞证, 4港澳居民来往内地通行证, 11营业执照, 12统一社会信用代码, 20子账号, 99其他
    identity_type = fields.Integer('证件类型')

    jzq_apply_no = fields.Char("签约合同编号")
    jzq_contract_view_url = fields.Char("签约合同查看地址")
    jzq_contract_dl_url = fields.Char("签约合同下载地址")
    jzq_state = fields.Selection([
        ('0', '未签'),
        ('1', '已签'),
        ('2', '拒签'),
        ('3', '已保全'),
    ], string="签约状态")

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

    def _gen_sign(self, app_key, app_secret):
        nonce = ''.join(random.sample(
            string.ascii_letters + string.digits, 32))
        ts = int(time.time())

        sign_str = ''.join([
            'nonce', nonce, 'ts', str(ts),
            'app_key', app_key, 'app_secret', app_secret
        ])
        return (nonce, ts, hashlib.sha1(sign_str.encode('utf-8')).hexdigest())

    def _request_jzq(self, service_url, app_key, app_secret, req_type, data, files=None):
        (nonce, ts, sign) = self._gen_sign(app_key, app_secret)
        data.update({
            'nonce': nonce
        })

        return requests.post(''.join([
            service_url,
            SERVICE_API.get(req_type),
            '?app_key=%s' % app_key,
            '&ts=%d' % ts,
            '&sign=%s' % sign,
            '&encry_method=sha1',
        ]), data=data, files=files).json()

    def _download_file(self, url, file_name):
        send_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8"}
        req = requests.get(url, headers=send_headers)  # 通过访问互联网得到文件内容
        if req.status_code == 200:
            bytes_io = io.BytesIO(req.content)  # 转换为字节流
            bytes_io.name = file_name
            return bytes_io
        else:
            return False

    def _gentleman_signing(self, signatories, contract_pdf, file_name, is_interactive=False, bus_num='', seq=1, total=1):
        signing_body = {
            'contractName': self.name, 
            'serverCa': 1, 
            'dealType': 17 if is_interactive else 1, 
            'qrCode':1,
            'fileType': 0, 
            'positionType': 0, 
            'signatories': signatories
        }
        if is_interactive:
            signing_body.update({
                'orderFlag': 1,
                'sequenceInfo': json.dumps({
                    'businessNo': bus_num,
                    'sequenceOrder': seq,
                    'totalNum': total
                })
            })
            signing_body['busNum'] = bus_num
        res_sign_data = self.env['galaxy.external.api'].invoke(
            "APPLY-SIGN",
            body=signing_body,
            files={'file': contract_pdf}).retrieve_response("APPLY-SIGN-RESULT", False).raw
        apply_no = res_sign_data.get('applyNo')
        _logger.info("合同编号：", apply_no)
        if not apply_no:
            raise UserError(f'签约失败{res_sign_data.get("msg")}')

        res_sign_status_data = self.env['galaxy.external.api'].invoke(
            "APP-SGIN-STATUS",
            body={'applyNo': apply_no,
                  'fullName': signatories[0].get('fullName'),
                  'identityCard': signatories[0].get('identityCard'),
                  'identityType': signatories[0].get('identityType')}
        ).retrieve_response("APP-SGIN-STATUS-RESULT", False).raw
        jzq_state = str(res_sign_status_data.get('data', ''))
        _logger.info("签约状态：", SIGN_STATUS.get(jzq_state))

        self.write({
            'state': 'committed',
            'full_name': signatories[0].get('fullName'),
            'identity_card': signatories[0].get('identityCard'),
            'identity_type': signatories[0].get('identityType'),
            'jzq_apply_no': apply_no,
            'jzq_state': jzq_state
        })
        cron = self.env['ir.cron'].sudo().env.ref(
            'ifs_contract_sign_jzq.refresh_commit_contract_cron')
        self.env['ir.cron.trigger'].sudo().create(
            {'cron_id': cron.id, 'call_at': fields.Datetime.now() +
                relativedelta(minutes=1)}
        )
        if is_interactive:
            self.env['ir.cron.trigger'].sudo().create(
                {'cron_id': cron.id, 'call_at': fields.Datetime.now() +
                    relativedelta(minutes=10)}
            )
            self.env['ir.cron.trigger'].sudo().create(
                {'cron_id': cron.id, 'call_at': fields.Datetime.now() +
                    relativedelta(minutes=20)}
            )
            self.env['ir.cron.trigger'].sudo().create(
                {'cron_id': cron.id, 'call_at': fields.Datetime.now() +
                    relativedelta(minutes=30)}
            )

    def _prepare_signatory(self, sign_partner, orderNum, signatories, is_interactive=False):
        chapteJson = json.loads(self.template_id.sign_position_params)[
            orderNum - 1]
        if chapteJson.get('chaptes', False):
            params = self.params and json.loads(self.params)
            if sign_partner._name == 'hr.employee':
                if not sign_partner.idcard_id.idcard_no:
                    raise UserError('%s 身份证号为空' % sign_partner.name)
                signatories.append({
                    "fullName": sign_partner.name,
                    "identityCard": sign_partner.idcard_id.idcard_no,
                    "identityType": 1,
                    "mobile": sign_partner.mobile_phone,
                    "orderNum": orderNum,
                    "signLevel": 3,
                    "chapteJson": [
                        chapteJson
                    ],
                })
                pass
            elif params and params.get('sign_partner') == orderNum:
                signatories.append({
                    "mobile": params.get('mobile'),
                    "fullName": params.get('user_name'),
                    "identityCard": params.get('card_no'),
                    "identityType": 1,
                    "orderNum": orderNum,
                    # "signLevel": 3,
                    "chapteJson": [
                        chapteJson
                    ],
                })
            else:
                signatorie = {
                    "email": sign_partner.jzq_account,
                    "fullName": sign_partner.company_id.name,
                    "identityCard": sign_partner.company_id.company_registry,
                    "identityType": 12,
                    "orderNum": orderNum,
                    "signLevel": 0,
                    "chapteJson": [
                        chapteJson
                    ],
                }
                if is_interactive:
                    signatorie.update({
                        "mobile": sign_partner.root_employee_id.mobile_phone,
                        'authLevel': json.dumps([12])
                    })
                signatories.append(signatorie)
        return signatories

    def _contract_sign(self, is_interactive=False, bus_num='', seq=1, total=1):
        signatories = []
        if self.partner_one:
            signatories = self._prepare_signatory(
                self.partner_one, 1, signatories, is_interactive)
        if self.partner_two:
            signatories = self._prepare_signatory(
                self.partner_two, 2, signatories, is_interactive)
        if self.partner_three:
            signatories = self._prepare_signatory(
                self.partner_three, 3, signatories, is_interactive)
        if self.partner_four:
            signatories = self._prepare_signatory(
                self.partner_four, 4, signatories, is_interactive)

        report = self.env['ir.actions.report']._get_report_from_name(
            "ifs_contract.print_contract")
        context = dict(self.env.context)
        data = {'context': context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, self.id, data=data)

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = ''.join([self.name, self.code, ".pdf"])
        # asyncio.run(self._gentleman_signing(
        #     signatories, contract_pdf, self.code))
        # return contract_pdf
        self._gentleman_signing(
            signatories, contract_pdf, self.code, is_interactive, bus_num, seq, total)
        return True

    def signature_all_by_interactive(self, business_type, sign_partner):
        seq = 1
        bus_num = '%s%s' % (
            business_type, self.env['ir.sequence'].next_by_code('ifs.contract.bus.code') or '')
        total = len(self)
        for contract in self:
            try:
                contract._contract_sign(is_interactive=True, bus_num=bus_num, seq=seq, total=total)
                seq += 1
            except UserError as e:
                contract.state = 'err'
                raise e

        res_sign_url = ''
        if sign_partner._name == 'ifs.gar.entry.merchant':
            res_sign_url = self.env['galaxy.external.api'].invoke(
                "JZQ_BATCHSIGNLINK", body={
                    'businessNo': bus_num,
                    'fullName': sign_partner.company_id.name,
                    'identityCard': sign_partner.company_id.company_registry,
                    'identityType': '12',
                }).retrieve_response("JZQ_BATCHSIGNLINK-RESULT", False).raw

        return res_sign_url.get('sign_url', None)

    def jzq_refresh(self):
        # (service_url, app_key, app_secret) = self._get_param_config()
        contract_infos = self.search([
            ('jzq_apply_no', '!=', False), '|', ('jzq_state',
                                                 'not in', ('2', '3')), ('contract', '=', False),
            # '|', ('jzq_state', 'not in', ('2', '3'))
        ])
        for contract_info in contract_infos:
            _logger.info('签约合同编号：%s' % contract_info.jzq_apply_no)
            jzq_state = contract_info.jzq_state
            res_contact_view_data = self.env['galaxy.external.api'].invoke(
                "APP-LINK-ANONY-DETAIL", body={'applyNo': contract_info.jzq_apply_no}).retrieve_response("APP-LINK-ANONY-DETAIL-RESULT", False).raw
            res_contact_download_data = self.env['galaxy.external.api'].invoke(
                "APP_DOWNLOADLINK", body={'applyNo': contract_info.jzq_apply_no}).retrieve_response("APP_DOWNLOADLINK-RESULT", False).raw
            res_sign_status_data = self.env['galaxy.external.api'].invoke(
                "APP-SGIN-STATUS",
                body={'applyNo': contract_info.jzq_apply_no,
                      'fullName': contract_info.full_name,
                      'identityCard': contract_info.identity_card,
                      'identityType': contract_info.identity_type}
            ).retrieve_response("APP-SGIN-STATUS-RESULT", False).raw
            app_link_anony = res_contact_view_data.get('data')
            app_download_link = res_contact_download_data.get('data')
            jzq_state = str(res_sign_status_data.get('data', ''))
            _logger.info('合同查看地址：%s' % app_link_anony)
            _logger.info('合同下载地址：%s' % app_download_link)
            
            if jzq_state:
                sign_file = self._download_file(
                    app_download_link, contract_info.name)
                if sign_file:
                    contract_info.write({
                        'contract': base64.b64encode(sign_file.getvalue()),
                        'jzq_contract_view_url': app_link_anony,
                        'jzq_contract_dl_url': app_download_link,
                        'jzq_state': str(jzq_state),
                        'state': 'signed'
                    })

    def jzq_refresh_commit_contract(self):
        contract_info_list = self.search([
            ('state', '=', 'committed'),
            ('jzq_apply_no', '!=', False),
        ])
        # contract_info_list = self.search([
        #     '|',
        #     ('state','=','committed'),
        #     '|',
        #     ('jzq_state','=','0'),
        #     '&',
        #     ('template_id.need_partner','=','one'),
        #     ('jzq_state','=','1')
        # ])
        for contract_info in contract_info_list:
            _logger.info('签约合同编号：%s' % contract_info.jzq_apply_no)
            res_sign_status_data = self.env['galaxy.external.api'].invoke(
                "APP-SGIN-STATUS",
                body={
                    'applyNo': contract_info.jzq_apply_no,
                    # 'fullName': contract_info.full_name,
                    # 'identityCard': contract_info.identity_card,
                    # 'identityType': contract_info.identity_type
                }
            ).retrieve_response("APP-SGIN-STATUS-RESULT", False).raw
            jzq_state = str(res_sign_status_data.get('data', ''))
            if jzq_state == contract_info.jzq_state:
                continue
            res_contact_view_data = self.env['galaxy.external.api'].invoke(
                "APP-LINK-ANONY-DETAIL", body={'applyNo': contract_info.jzq_apply_no}).retrieve_response("APP-LINK-ANONY-DETAIL-RESULT", False).raw
            res_contact_download_data = self.env['galaxy.external.api'].invoke(
                "APP_DOWNLOADLINK", body={'applyNo': contract_info.jzq_apply_no}).retrieve_response("APP_DOWNLOADLINK-RESULT", False).raw
            app_link_anony = res_contact_view_data.get('data')
            app_download_link = res_contact_download_data.get('data')
            sign_file = self._download_file(
                app_download_link, contract_info.name)
            if sign_file:
                contract_info.write({
                    'contract': base64.b64encode(sign_file.getvalue()),
                    'jzq_contract_view_url': app_link_anony,
                    'jzq_contract_dl_url': app_download_link,
                    'jzq_state': str(jzq_state),
                    'state': 'signed'
                })

    @api.model_callback
    def sign_sync(self, entry, message, callback_action, callback_log):
        _logger.info('签约回调：%s' % str(message))
        try:
            req_data_json = json.loads(message.get("data"))
            applyNo = req_data_json.get("applyNo")
            contract_info = self.search(
                [('jzq_apply_no', '=', applyNo)])
            res_contact_view_data = self.env['galaxy.external.api'].invoke(
                "APP-LINK-ANONY-DETAIL", body={'applyNo': applyNo}).retrieve_response("APP-LINK-ANONY-DETAIL-RESULT", False).raw
            res_contact_download_data = self.env['galaxy.external.api'].invoke(
                "APP_DOWNLOADLINK", body={'applyNo': applyNo}).retrieve_response("APP_DOWNLOADLINK-RESULT", False).raw
            app_link_anony = res_contact_view_data.get('data')
            app_download_link = res_contact_download_data.get('data')
            _logger.info('合同编号：%s' % applyNo)
            _logger.info('合同查看地址：%s' % app_link_anony)
            _logger.info('合同下载地址：%s' % app_download_link)
            sign_file = self._download_file(
                app_download_link, contract_info.name)
            if sign_file:
                contract_info.write({
                    'contract': base64.b64encode(sign_file.getvalue()),
                    'jzq_contract_view_url': app_link_anony,
                    'jzq_contract_dl_url': app_download_link,
                    'jzq_state': str(req_data_json.get("signStatus", "")),
                })
                return True
            else:
                return False
        except Exception:
            return False
