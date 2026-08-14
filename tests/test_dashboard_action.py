# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDashboardAction(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.ActionModel = self.env['moneta.dashboard.action']

    def test_seed_default_actions(self):
        """Test seeding default dashboard shortcuts."""
        self.ActionModel.search([('user_id', '=', self.user.id)]).unlink()
        self.ActionModel.seed_user_default_actions(self.user)
        actions = self.ActionModel.search([('user_id', '=', self.user.id)])
        self.assertTrue(len(actions) >= 10)

    def test_action_execute(self):
        """Test dispatching an action from the launcher."""
        action_rec = self.ActionModel.create({
            'name': 'My Checkbook',
            'action_type': 'register',
            'icon': 'fa-book',
            'color_class': 'primary',
            'user_id': self.user.id,
        })
        res = action_rec.action_execute()
        self.assertEqual(res.get('res_model'), 'moneta.transaction')

    def test_dashboard_launchpad_linkage(self):
        """Test dashboard computing dynamic launchpad actions."""
        dash = self.env['moneta.dashboard'].create({'name': 'Test Dashboard'})
        dash._compute_launchpad_actions()
        self.assertTrue(len(dash.action_launchpad_ids) > 0)
