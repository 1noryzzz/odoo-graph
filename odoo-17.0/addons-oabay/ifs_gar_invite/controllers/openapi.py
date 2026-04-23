# -*- coding: utf-8 -*-

import logging
from odoo.exceptions import AccessDenied, MissingError, UserError
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class OpenApiController(Controller):
    def _ok(self, data=None):
        payload = dict(data or {})
        payload.setdefault('error_msg', '')
        return payload

    def _err(self, message: str, data=None):
        payload = dict(data or {})
        payload['error_msg'] = message
        return payload

    def _resolve_supplier_factor(self, supplier_code: str, factor_code: str):
        """Resolve supplier/factor by seq_code and validate relationship.

        Keep logic local to controller to avoid impacting existing business flows.
        """
        if not supplier_code:
            raise UserError('supplier_code不能为空')
        if not factor_code:
            raise UserError('factor_code不能为空')

        supplier = (
            request
            .env['ifs.partner.supplier']
            .sudo()
            .search([('seq_code', '=', supplier_code)], limit=1)
        )
        if not supplier.exists():
            raise UserError('未找到对应的供应方，请检查supplier_code是否正确')

        factor = (
            request
            .env['ifs.partner.factor']
            .sudo()
            .search([('seq_code', '=', factor_code)], limit=1)
        )
        if not factor.exists():
            raise UserError('未找到对应的保理方，请检查factor_code是否正确')

        factor_supplier = (
            request
            .env['ifs.gar.partner.factor.supplier']
            .sudo()
            .search([('supplier_id', '=', supplier.id), ('factor_id', '=', factor.id)], limit=1)
        )

        if not factor_supplier.exists():
            raise UserError('当前供应方与保理方不存在合作关系')

        return supplier, factor

    @route(['/openapi/merchant/invite'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def merchant_invite(self, db):
        return {
            'code': 200,
            'message': 'OK',
            'db': db,
            'uid': request.uid,
            'company_id': request.env.company.id,
        }

    @route(
        ['/openapi/merchant/invite/init', '/openapi/miniapp/merchant/invite/init'],
        type='json',
        auth='openapi',
        methods=['POST'],
        cors='*',
    )
    def merchant_invite_init(
        self,
        supplier_code,
        factor_code,
        company_name,
        company_registry,
        business_address,
        email,
        phone,
        logo,
    ):
        """初始化采购方邀请：创建公司与邀请单，并返回根用户预填信息。
        Args:
            supplier_code (str): 供应方编码，对应 ``ifs.partner.supplier.seq_code``。
            factor_code (str): 保理方编码，对应 ``ifs.partner.factor.seq_code``。
            company_name (str): 采购方企业名称。
            company_registry (str): 统一社会信用代码。
            business_address (str): 营业地址。
            email (str): 采购方法人邮箱。
            phone (str): 采购方法人手机号。
            logo (str): 公司 Logo 的 base64 字符串。
        Returns:
            dict: 业务载荷（JSON-RPC 的 ``result``）。成功时包含：

            - ``invite_merchant_id`` (int): 邀请单 ``ifs.gar.invite.merchant`` 主键。
            - ``ifs_company_id`` (int): ``ifs.base.company`` 主键。
            - ``legal_user_info`` (dict): 预填法人/根用户信息，键为 ``name``、``login``、
              ``mobile_phone``、``work_email``；后两者无值时可能为 ``None``。
            - ``error_msg`` (str): 成功时为空字符串；失败时为错误说明。
        Note:
            ``AccessDenied`` / ``UserError`` 等异常在控制器内被捕获并转为 ``error_msg``，
            HTTP 仍可能返回 200 + JSON-RPC 包络，请同时检查 ``result.error_msg``。
        """
        try:
            supplier, factor = self._resolve_supplier_factor(supplier_code, factor_code)

            request.update_env(context={
                **request.env.context,
                'allowed_company_ids': [supplier.company_id.id],
                'force_company': supplier.company_id.id,
            })
            env = request.env
            wizard = (
                env['ifs.gar.invite.merchant.wizard']
                .sudo()
                .create({
                    'name': company_name,
                    'email': email,
                    'phone': phone,
                    'company_registry': company_registry,
                    'logo': logo,
                    'street': business_address,
                    'factor_id': factor.id,
                    'supplier_id': supplier.id,
                })
            )
            wizard.action_confirm()

            # Do NOT depend on wizard UI action return. Re-query deterministic business records.
            ifs_company = (
                env['ifs.base.company']
                .sudo()
                .search([('company_registry', '=', company_registry)], limit=1)
            )
            if not ifs_company.exists():
                # sync_business_registration may normalize/overwrite registry; fallback to name.
                ifs_company = (
                    env['ifs.base.company'].sudo().search([('name', '=', company_name)], limit=1)
                )
            if not ifs_company.exists():
                raise UserError('创建/同步公司信息失败：未找到对应ifs.base.company记录')

            invite = (
                env['ifs.gar.invite.merchant']
                .sudo()
                .search(
                    [('ifs_company_id', '=', ifs_company.id), ('supplier_id', '=', supplier.id)],
                    limit=1,
                )
            )
            if not invite.exists():
                raise UserError('创建邀请单失败：未找到ifs.gar.invite.merchant记录')
            if invite.factor_id.id != factor.id:
                raise UserError('已存在邀请单，但保理方不一致，请检查factor_code是否正确')

            legal_user_info = {
                'name': ifs_company.legal_name or '',
                # login uses invite seq_code per miniapp contract
                'login': invite.seq_code or '',
                'mobile_phone': ifs_company.legal_phone or None,
                'work_email': ifs_company.legal_email or None,
            }
            return self._ok({
                'invite_merchant_id': invite.id,
                'ifs_company_id': ifs_company.id,
                'legal_user_info': legal_user_info,
            })
        except AccessDenied as e:
            return self._err(str(e))
        except MissingError as e:
            return self._err(str(e))
        except UserError as e:
            return self._err(str(e))
        except Exception:
            _logger.exception('openapi merchant_invite_init failed')
            return self._err('系统异常，请稍后重试')

    @route(
        ['/openapi/merchant/invite/send', '/openapi/miniapp/merchant/invite/send'],
        type='json',
        auth='openapi',
        methods=['POST'],
        cors='*',
    )
    def merchant_invite_send(
        self,
        supplier_code,
        factor_code,
        invite_merchant_id,
        ifs_company_id,
        mobile_phone,
        work_email,
        notes=None,
    ):
        """发送/确认邀请：根据 init 返回的 ID 创建根用户向导并确认。
        Args:
            supplier_code (str): 供应方编码，``ifs.partner.supplier.seq_code``。
            factor_code (str): 保理方编码，``ifs.partner.factor.seq_code``。
            invite_merchant_id (int): 邀请单 ID，须与 init 返回一致。
            ifs_company_id (int): 公司 ID，须与 init 返回一致。
            mobile_phone (str): 根用户手机号。
            work_email (str): 根用户工作邮箱。
            notes (str | None): 备注，可选。
        Returns:
            dict: 业务载荷（``result``）。成功时包含：

            - ``invite_merchant_id`` (int): 邀请单主键。
            - ``state`` (str): 邀请单状态（如 ``draft`` / ``sended``，以模型定义为准）。
            - ``error_msg`` (str): 成功时为空字符串；失败时为错误说明。
        """
        try:
            supplier, factor = self._resolve_supplier_factor(supplier_code, factor_code)
            request.update_env(context={
                **request.env.context,
                'allowed_company_ids': [supplier.company_id.id],
                'force_company': supplier.company_id.id,
            })
            env = request.env

            invite = env['ifs.gar.invite.merchant'].sudo().browse(int(invite_merchant_id))
            if not invite.exists():
                raise UserError('未找到对应邀请单，请检查invite_merchant_id是否正确')
            if invite.supplier_id.id != supplier.id:
                raise UserError('邀请单与supplier_code不匹配')
            if invite.factor_id.id != factor.id:
                raise UserError('邀请单与factor_code不匹配')
            if int(ifs_company_id) != invite.ifs_company_id.id:
                raise UserError('邀请单与ifs_company_id不匹配')
            if invite.state not in ['draft', 'sended']:
                raise UserError('当前状态不允许发送/重发邀请')

            wizard_vals = {
                'ifs_company_id': invite.ifs_company_id.id,
                'mobile_phone': mobile_phone,
                'work_email': work_email,
                'notes': notes,
            }
            env['ifs.gar.invite.merchant.root.user.wizard'].sudo().create(
                wizard_vals
            ).action_confirm()

            return self._ok({
                'invite_merchant_id': invite.id,
                'state': invite.state,
            })
        except AccessDenied as e:
            return self._err(str(e))
        except MissingError as e:
            return self._err(str(e))
        except UserError as e:
            return self._err(str(e))
        except Exception:
            _logger.exception('openapi merchant_invite_send failed')
            return self._err('系统异常，请稍后重试')
