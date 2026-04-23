# -*- coding: utf-8 -*-

import base64
import io
import logging
import re

from odoo import _, api, fields, models, tools
from odoo.modules.module import get_resource_path
from random import randrange
from PIL import Image

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('galaxy_common', 'static/img/yz.ico')
        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())
            # Modify the source image to add a colored bar on the bottom
            # This could seem overkill to modify the pixels 1 by 1, but
            # Pillow doesn't provide an easy way to do it, and this
            # is acceptable for a 16x16 image.
            color = (randrange(32, 224, 24), randrange(
                32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel(
                            (x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel(
                            (x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="ICO")
            return base64.b64encode(stream.getvalue())


class ResPartner(models.Model):
    """ 用来验证企业工商信息的扩展 """
    _inherit = 'res.partner'

    # 统一社会信用代码中不使用I,O,S,V,Z
    _string1 = '0123456789ABCDEFGHJKLMNPQRTUWXY'
    SOCIAL_CREDIT_CHECK_CODE_DICT = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'P': 23, 'Q': 24,
        'R': 25, 'T': 26, 'U': 27, 'W': 28, 'X': 29, 'Y': 30}
    # 第i位置上的加权因子
    _social_credit_weighting_factor = [
        1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]

    # GB11714-1997全国组织机构代码编制规则中代码字符集
    _string2 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    ORGANIZATION_CHECK_CODE_DICT = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 18,
        'J': 19, 'K': 20, 'L': 21, 'M': 22, 'N': 23, 'O': 24, 'P': 25, 'Q': 26,
        'R': 27, 'S': 28, 'T': 29, 'U': 30, 'V': 31, 'W': 32, 'X': 33, 'Y': 34, 'Z': 35}
    # 第i位置上的加权因子
    _organization_weighting_factor = [3, 7, 9, 10, 5, 8, 4, 2]

    def _gen_check_code(self, weighting_factor, ontology_code, modulus, check_code_dict):
        '''
        @param weighting_factor: 加权因子
        @param ontology_code:本体代码
        @param modulus:  模数(求余用)
        @param check_code_dict: 字符字典
        '''
        total = 0
        for i in range(len(ontology_code)):
            if ontology_code[i].isdigit():
                total += int(ontology_code[i]) * weighting_factor[i]
            else:
                num = check_code_dict.get(ontology_code[i], -1)
                if num < 0:
                    return -1
                total += num * weighting_factor[i]
        diff = modulus - total % modulus
        return diff

    def _check_social_credit_code(self, code):
        '''
        统一社会信用代码校验
        国家标准GB32100—2015：18位统一社会信用代码从2015年10月1日正式实行，
        标准规定统一社会信用代码用18位阿拉伯数字或大写英文字母（不使用I、O、Z、S、V）表示，
        分别是1位登记管理部门代码、1位机构类别代码、6位登记管理机关行政区划码、9位主体标识码（组织机构代码）、1位校验码


        税号 = 6位行政区划码 + 9位组织机构代码
        计算校验码公式:
            C18 = 31-mod(sum(Ci*Wi)，31)
        其中Ci为组织机构代码的第i位字符,Wi为第i位置的加权因子,C18为校验码
        c18=30, Y; c18=31, 0
        '''
        if type(code) != str:
            return False

        code = code.upper()
        # 1. 长度限制
        if len(code) != 18:
            _logger.warning('{} -- 统一社会信用代码长度不等18！'.format(code))
            return False

        # 2. 组成限制
        # 登记管理部门：1=机构编制; 5=民政; 9=工商; Y=其他
        # 机构类别代码:
        '''
        机构编制=1：1=机关 | 2=事业单位 | 3=中央编办直接管理机构编制的群众团体 | 9=其他
        民政=5：1=社会团体 | 2=民办非企业单位 | 3=基金会 | 9=其他
        工商=9：1=企业 | 2=个体工商户 | 3=农民专业合作社
        其他=Y：1=其他
        '''
        reg = r'^(11|12|13|19|51|52|53|59|91|92|93|Y1)\d{6}\w{9}\w$'
        if not re.match(reg, code):
            _logger.warning('{} -- 组成错误！'.format(code))
            return False

        # 3. 校验码验证
        # 本体代码
        ontology_code = code[:17]
        # 校验码
        check_code = code[17]
        # 计算校验码
        tmp_check_code = self._gen_check_code(
            self._social_credit_weighting_factor,
            ontology_code, 31, self.SOCIAL_CREDIT_CHECK_CODE_DICT)
        if tmp_check_code == -1:
            _logger.warning('{} -- 包含非组成字符！'.format(code))
            return False

        tmp_check_code = (0 if tmp_check_code == 31 else tmp_check_code)
        if self._string1[tmp_check_code] == check_code:
            _logger.info('{} -- 统一社会信用代码校验正确！'.format(code))
            return True
        else:
            _logger.warning('{} -- 统一社会信用代码校验错误！'.format(code))
            return False

    def _check_organization_code(self, code):
        '''
        组织机构代码校验
        该规则按照GB 11714编制：统一社会信用代码的第9~17位为主体标识码(组织机构代码)，共九位字符
        计算校验码公式:
            C9 = 11-mod(sum(Ci*Wi)，11)
        其中Ci为组织机构代码的第i位字符,Wi为第i位置的加权因子,C9为校验码
        C9=10, X; C9=11, 0
        @param  code: 统一社会信用代码 / 组织机构代码
        '''
        # 1. 长度限制
        if len(code) != 9:
            _logger.warning('{} -- 组织机构代码长度不等9！'.format(code))
            return False

        # 2. 组成限制
        reg = r'^\w{9}$'
        if not re.match(reg, code):
            _logger.warning('{} -- 组成错误！'.format(code))
            return False

        # 3. 校验码验证
        # 本体代码
        ontology_code = code[:8]
        # 校验码
        check_code = code[8]
        # 计算校验码
        tmp_check_code = self._gen_check_code(
            self.organization_weighting_factor, ontology_code,
            11, self.ORGANIZATION_CHECK_CODE_DICT)
        if tmp_check_code == -1:
            _logger.warning('{} -- 包含非组成字符！'.format(code))
            return False

        tmp_check_code = (
            0 if tmp_check_code == 11
            else (33 if tmp_check_code == 10 else tmp_check_code))
        if self._string2[tmp_check_code] == check_code:
            _logger.info('{} -- 组织机构代码校验正确！'.format(code))
            return True
        else:
            _logger.warning('{} -- 组织机构代码校验错误！'.format(code))
            return False

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # If a belgian company has a VAT number then it's company registry is it's VAT Number (without country code).
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'CN' and p.vat):
            if partner.is_company and self._check_social_credit_code(partner.vat):
                partner.company_registry = partner.vat
