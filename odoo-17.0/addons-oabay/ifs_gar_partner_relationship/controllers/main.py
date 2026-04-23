# -*- coding: utf-8 -*-

from odoo import _, http, fields
from odoo.http import request
from PIL import Image

import io
import base64


class InclusiveFinancingContract(http.Controller):

    @http.route('/partner/factor/sign', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_sign_factor_page(self, token, **kwargs):
        partner_factor = request.env['ifs.partner.factor'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_factor:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign', {
                    'partner_factor': partner_factor,
                })
        else:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    @http.route('/partner/factor/signature', type='json', auth="public", website=True)
    def contract_factor_signature(self, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        token = access_token or request.httprequest.args.get(
            'token')

        if not signature:
            return {'error': _('未收到签名信息')}

        partner_factor = request.env['ifs.partner.factor'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_factor:
            im = Image.open(io.BytesIO(base64.b64decode(signature)))
            if im.width < im.height:
                im = im.rotate(90, expand=True)
                b = io.BytesIO()
                im.save(b, format="PNG")
                signature = base64.b64encode(b.getvalue())

            target = partner_factor.write_uid.partner_id
            request.env['bus.bus']._sendone(target, 'ifs_contract_signed', '')

            partner_factor.write({
                'signature': signature,
            })
            # 这里需要触发ifs.base.company的修改，否则相应的图片会有缓存
            partner_factor.ifs_company_id.write({
                'version': partner_factor.ifs_company_id.version + 1
            })

            return {
                'force_refresh': True,
                'redirect_url': '/partner/factor/sign_finish?token=' + token
            }
        else:
            return {'error': _('TOKEN 无效')}

    @http.route('/partner/factor/sign_finish', type='http', methods=['GET'], auth="public", website=True)
    def contract_factor_signed(self, token, **kw):
        partner_factor = request.env['ifs.partner.factor'].sudo().sign_with_token(
            token, check_validity=True)
        partner_factor.sudo().write({
            'token': False,
            'expiration': False,
        })
        return request.render('ifs_gar_partner_relationship.factor_signed', {
            'partner_factor': partner_factor,
        })

    @http.route('/partner/funder/sign', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_funder_sign_page(self, token, **kwargs):
        partner_funder = request.env['ifs.partner.funder'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_funder:
            return request.render(
                'ifs_gar_partner_relationship.funder_sign', {
                    'partner_funder': partner_funder,
                })
        else:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    @http.route('/partner/funder/signature', type='json', auth="public", website=True)
    def contract_funder_signature(self, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        token = access_token or request.httprequest.args.get(
            'token')

        if not signature:
            return {'error': _('未收到签名信息')}

        partner_funder = request.env['ifs.partner.funder'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_funder:
            im = Image.open(io.BytesIO(base64.b64decode(signature)))
            if im.width < im.height:
                im = im.rotate(90, expand=True)
                b = io.BytesIO()
                im.save(b, format="PNG")
                signature = base64.b64encode(b.getvalue())

            target = partner_funder.write_uid.partner_id
            request.env['bus.bus']._sendone(target, 'ifs_contract_signed', '')

            partner_funder.write({
                'signature': signature,
            })
            # 这里需要触发ifs.base.company的修改，否则相应的图片会有缓存
            partner_funder.ifs_company_id.write({
                'version': partner_funder.ifs_company_id.version + 1
            })

            return {
                'force_refresh': True,
                'redirect_url': '/partner/funder/sign_finish?token=' + token
            }
        else:
            return {'error': _('TOKEN 无效')}

    @http.route('/partner/funder/sign_finish', type='http', methods=['GET'], auth="public", website=True)
    def contract_funder_signed(self, token, **kw):
        partner_funder = request.env['ifs.partner.funder'].sudo().sign_with_token(
            token, check_validity=True)
        if not partner_funder:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })
        partner_funder.sudo().write({
            'token': False,
            'expiration': False,
        })
        return request.render('ifs_gar_partner_relationship.funder_signed', {
            'partner_funder': partner_funder,
        })

    @http.route('/partner/supplier/sign', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_supplier_sign_page(self, token, **kwargs):
        partner_supplier = request.env['ifs.partner.supplier'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_supplier:
            return request.render(
                'ifs_gar_partner_relationship.supplier_sign', {
                    'partner_supplier': partner_supplier,
                })
        else:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    @http.route('/partner/supplier/signature', type='json', auth="public", website=True)
    def contract_supplier_signature(self, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        token = access_token or request.httprequest.args.get(
            'token')

        if not signature:
            return {'error': _('未收到签名信息')}

        partner_supplier = request.env['ifs.partner.supplier'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_supplier:
            im = Image.open(io.BytesIO(base64.b64decode(signature)))
            if im.width < im.height:
                im = im.rotate(90, expand=True)
                b = io.BytesIO()
                im.save(b, format="PNG")
                signature = base64.b64encode(b.getvalue())

            target = partner_supplier.write_uid.partner_id
            request.env['bus.bus']._sendone(target, 'ifs_contract_signed', '')

            partner_supplier.write({
                'signature': signature,
            })
            # 这里需要触发ifs.base.company的修改，否则相应的图片会有缓存
            partner_supplier.ifs_company_id.write({
                'version': partner_supplier.ifs_company_id.version + 1
            })

            return {
                'force_refresh': True,
                'redirect_url': '/partner/supplier/sign_finish?token=' + token
            }
        else:
            return {'error': _('TOKEN 无效')}

    @http.route('/partner/supplier/sign_finish', type='http', methods=['GET'], auth="public", website=True)
    def contract_supplier_signed(self, token, **kw):
        partner_supplier = request.env['ifs.partner.supplier'].sudo().sign_with_token(
            token, check_validity=True)
        if not partner_supplier:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })
        partner_supplier.sudo().write({
            'token': False,
            'expiration': False,
        })
        return request.render('ifs_gar_partner_relationship.supplier_signed', {
            'partner_supplier': partner_supplier,
        })

    @http.route('/partner/merchant/sign', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_merchant_sign_page(self, token, **kwargs):
        partner_merchant = request.env['ifs.partner.merchant'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_merchant:
            return request.render(
                'ifs_gar_partner_relationship.merchant_sign', {
                    'partner_merchant': partner_merchant,
                })
        else:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    @http.route('/partner/merchant/signature', type='json', auth="public", website=True)
    def contract_merchant_signature(self, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        token = access_token or request.httprequest.args.get(
            'token')

        if not signature:
            return {'error': _('未收到签名信息')}

        partner_merchant = request.env['ifs.partner.merchant'].sudo().sign_with_token(
            token, check_validity=True)
        if partner_merchant:
            im = Image.open(io.BytesIO(base64.b64decode(signature)))
            if im.width < im.height:
                im = im.rotate(90, expand=True)
                b = io.BytesIO()
                im.save(b, format="PNG")
                signature = base64.b64encode(b.getvalue())

            target = partner_merchant.write_uid.partner_id
            request.env['bus.bus']._sendone(target, 'ifs_contract_signed', '')

            partner_merchant.write({
                'signature': signature,
            })
            # 这里需要触发ifs.base.company的修改，否则相应的图片会有缓存
            partner_merchant.ifs_company_id.write({
                'version': partner_merchant.ifs_company_id.version + 1
            })

            return {
                'force_refresh': True,
                'redirect_url': '/partner/merchant/sign_finish?token=' + token
            }
        else:
            return {'error': _('TOKEN 无效')}

    @http.route('/partner/merchant/sign_finish', type='http', methods=['GET'], auth="public", website=True)
    def contract_merchant_signed(self, token, **kw):
        partner_merchant = request.env['ifs.partner.merchant'].sudo().sign_with_token(
            token, check_validity=True)
        if not partner_merchant:
            return request.render(
                'ifs_gar_partner_relationship.factor_sign_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })
        partner_merchant.sudo().write({
            'token': False,
            'expiration': False,
        })
        return request.render('ifs_gar_partner_relationship.merchant_signed', {
            'partner_merchant': partner_merchant,
        })
