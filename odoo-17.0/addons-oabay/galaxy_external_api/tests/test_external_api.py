# -*- coding: utf-8 -*-

import logging

from odoo import api
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

#./odoo-bin --test-enable --log-level=error -c ../conf.d/odoo.conf -d for_test --without-demo=all --stop-after-init -u galaxy_external_api
class TestStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):

        super().setUpClass()

    def test_save_point(self):
        t0_pt = self.env['res.partner'].create({'name': 'test0'})

        
        with self.env.registry.cursor() as cr:
            self.env.flush_all()
            Partner = self.env['res.partner'].with_env(self.env(cr=cr))
            t1_pt = Partner.create({
                'name': 'test1',
            })

        _logger.exception(t1_pt.id)
        t1_pt = self.env['res.partner'].browse(t1_pt.id)
        _logger.exception(t1_pt.name)
        # t0_pt.write({
        #     'title': t1_pt.name,
        # })

    def _simulate_invoke(self, callback):
        with self.env.registry.cursor() as cr:
            cr._cnx.autocommit = True
            env = api.Environment(cr, self.uid, {})
            t_pt = env['res.partner'].create({'name': 'test'})

            callback(env, t_pt)

    # def test_invoke(self):
    #     car_infos = self.env['galaxy.external.api'].invoke('TSLCLLB').retrieve_response('CAR_INFO')
    #     for car_info in car_infos:
    #         print(car_info.raw)
