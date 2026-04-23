# -*- coding: utf-8 -*-

from datetime import datetime

import pytz

from odoo import fields
from odoo.tools import float_repr, float_round
from odoo.exceptions import ValidationError


def local_to_utc(record, naive_local_dt):
    """将用户时区的 naive 时间转为 naive UTC（用于存库、与 context_timestamp 反向）。
    若传入的已是带时区的 datetime，则先按该时区转成 UTC，再返回 naive UTC。

    :param record: 任意 recordset，用于取 context 或 env.user.tz
    :param datetime naive_local_dt: 用户认为的「本地时间」，可为 naive 或 aware
    :return: naive UTC datetime，可直接写入 Datetime 字段
    """
    if naive_local_dt.tzinfo is not None:
        utc_aware = naive_local_dt.astimezone(pytz.UTC)
        return utc_aware.replace(tzinfo=None)
    tz_name = record._context.get("tz") or record.env.user.tz or "UTC"
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC
    local_aware = tz.localize(naive_local_dt, is_dst=None)
    utc_aware = local_aware.astimezone(pytz.UTC)
    return utc_aware.replace(tzinfo=None)


class INet(fields.Char):
    type = "char"

    @property
    def column_type(self):
        return ("inet", "inet")


class MACAddress(fields.Char):
    type = "char"

    @property
    def column_type(self):
        return ("macaddr", "macaddr")


class BigInt(fields.Integer):
    column_cast_from = ("int4",)

    @property
    def column_type(self):
        return ("int8", "int8")

    def convert_to_read(self, value, record, use_name_get=True):
        return value


class Percent(fields.Float):
    """Basic percent field, can be length-limited, usually displayed as a
    percent."""

    type = "percent"
    _digits = None

    def convert_to_column(self, value, record, values=None, validate=True):
        result = float(value or 0.0)
        if result < 0 or result > 1:
            raise ValidationError("Percentage can be 0% to 100% only")
        digits = self.get_digits(record.env)
        if digits:
            precision, scale = digits
            result = float_repr(
                float_round(result, precision_digits=scale), precision_digits=scale
            )
        return result


if not hasattr(fields, "INet"):
    fields.INet = INet

if not hasattr(fields, "MACAddress"):
    fields.MACAddress = MACAddress

if not hasattr(fields, "BigInt"):
    fields.BigInt = BigInt

if not hasattr(fields, "Percent"):
    fields.Percent = Percent

fields.PropertiesDefinition.ALLOWED_KEYS = (
    *fields.PropertiesDefinition.ALLOWED_KEYS,
    "field",
)
