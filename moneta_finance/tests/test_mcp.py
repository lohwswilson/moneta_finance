# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MonetaTestBase
from ..controllers.mcp_controller import MonetaMCPController


@tagged('post_install', '-at_install')
class TestMCPController(MonetaTestBase):

    def setUp(self):
        super().setUp()
        self.controller = MonetaMCPController()

    def test_mcp_get_tools_list(self):
        """Verify MCP server exposes all 8 financial assistant tools."""
        res = self.controller.get_tools()
        self.assertIn('tools', res)
        tool_names = [t['name'] for t in res['tools']]
        self.assertIn('moneta_get_net_worth', tool_names)
        self.assertIn('moneta_list_accounts', tool_names)
        self.assertIn('moneta_get_transactions', tool_names)
        self.assertIn('moneta_create_transaction', tool_names)
        self.assertIn('moneta_get_budgets', tool_names)
        self.assertIn('moneta_get_upcoming_bills', tool_names)
        self.assertIn('moneta_simulate_loan_payoff', tool_names)
        self.assertIn('moneta_undo_last_action', tool_names)

    def test_mcp_loan_simulation(self):
        """Test loan payoff simulation endpoint calculation."""
        res = self.controller.call_tool(
            'moneta_simulate_loan_payoff',
            {
                'principal': 300000.0,
                'annual_rate': 6.0,
                'term_years': 30,
                'extra_monthly': 500.0,
            }
        )
        self.assertGreater(res['standard_monthly_payment'], 0)
        self.assertLess(res['accelerated_months'], 360)
        self.assertGreater(res['months_saved'], 0)
        self.assertGreater(res['years_saved'], 0)
