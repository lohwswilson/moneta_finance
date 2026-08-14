# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestInstitution(MonetaTestBase):

    def test_different_users_can_share_a_name(self):
        # unique(user_id, name) is per-owner, so two users may each have a "TD".
        user_a = self._make_user('Inst A', 'inst_a')
        user_b = self._make_user('Inst B', 'inst_b')
        a = self.env['moneta.institution'].with_user(user_a).create({'name': 'TD Bank'})
        b = self.env['moneta.institution'].with_user(user_b).create({'name': 'TD Bank'})
        self.assertEqual(a.name, b.name)
        self.assertNotEqual(a.user_id, b.user_id)

    def test_isolation_user_cannot_read_others_institution(self):
        owner = self._make_user('Inst Owner', 'inst_owner')
        other = self._make_user('Inst Other', 'inst_other')
        self.env['moneta.institution'].with_user(owner).create({'name': 'RBC'})
        # The other user sees zero institutions (record rule on user_id).
        seen = self.env['moneta.institution'].with_user(other).search([])
        self.assertFalse(seen)
        # A manager sees all.
        mgr = self._make_user('Inst Mgr', 'inst_mgr', group=self.group_manager)
        mgr_seen = self.env['moneta.institution'].with_user(mgr).search([])
        self.assertTrue(any(i.name == 'RBC' for i in mgr_seen))