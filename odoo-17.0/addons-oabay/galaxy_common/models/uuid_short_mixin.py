# -*- coding: utf-8 -*-

import uuid
from odoo import models, _

ARR = [
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"
]


class UUIDShortMixin(models.AbstractModel):
    _name = "uuid.short.mixin"
    _description = "生成简短的不重复编码"

    def short_uuid4(self, length=8):
        id = str(uuid.uuid4()).replace("-", '')
        multi = length / 8
        while multi > 1:
            id += str(uuid.uuid4()).replace("-", '')
            multi -= 1
        buffer = []
        for i in range(0, length):
            start = i * 4
            end = i * 4 + 4
            val = int(id[start:end], 16)
            buffer.append(ARR[val % 62])
        return "".join(buffer)
