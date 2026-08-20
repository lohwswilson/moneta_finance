# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestSingaporeMasterData(MonetaTestBase):

    def test_singapore_institutions_seeded(self):
        """Test pre-loaded Singapore & SEA financial institutions."""
        dbs = self.env.ref('moneta_finance.inst_dbs_posb', raise_if_not_found=False)
        self.assertTrue(dbs)
        self.assertEqual(dbs.country, 'SG')
        self.assertEqual(dbs.bank_profile, 'dbs_posb')

        cpf = self.env.ref('moneta_finance.inst_cpf_board', raise_if_not_found=False)
        self.assertTrue(cpf)
        self.assertEqual(cpf.country, 'SG')

        endowus = self.env.ref('moneta_finance.inst_endowus', raise_if_not_found=False)
        self.assertTrue(endowus)

    def test_singapore_payees_and_categories(self):
        """Test pre-loaded Singapore common payees and categories."""
        fairprice = self.env.ref('moneta_finance.payee_fairprice', raise_if_not_found=False)
        self.assertTrue(fairprice)
        self.assertEqual(fairprice.website, 'fairprice.com.sg')

        grab = self.env.ref('moneta_finance.payee_grab', raise_if_not_found=False)
        self.assertTrue(grab)
        self.assertEqual(grab.website, 'grab.com')

        sp_group = self.env.ref('moneta_finance.payee_sp_group', raise_if_not_found=False)
        self.assertTrue(sp_group)

        simplygo = self.env.ref('moneta_finance.payee_simplygo', raise_if_not_found=False)
        self.assertTrue(simplygo)
