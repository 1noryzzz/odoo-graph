from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        return list(map(
            lambda x: self.env['galaxy.qq.user.keys'].browse(int(x.split(',')[1])) if isinstance(
                x, str) and x.startswith('galaxy.qq.user.keys') else x,
            super()._build_bus_channel_list(channels)))
