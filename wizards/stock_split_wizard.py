# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MonetaStockSplitWizard(models.TransientModel):
    _name = 'moneta.stock.split.wizard'
    _description = 'Corporate Action / Stock Split Wizard'

    security_id = fields.Many2one('moneta.security', string='Security / Ticker', required=True)
    split_date = fields.Date(string='Effective Split Date', default=fields.Date.context_today, required=True)
    split_ratio_type = fields.Selection([
        ('2_for_1', '2-for-1 Forward Split (x2)'),
        ('3_for_1', '3-for-1 Forward Split (x3)'),
        ('4_for_1', '4-for-1 Forward Split (x4)'),
        ('5_for_1', '5-for-1 Forward Split (x5)'),
        ('10_for_1', '10-for-1 Forward Split (x10)'),
        ('custom', 'Custom Split Ratio'),
    ], string='Split Ratio', default='2_for_1', required=True)

    custom_multiplier = fields.Float(string='Multiplier (e.g. 2 for 2:1 or 0.2 for 1:5 reverse)', default=2.0, digits=(10, 4))
    memo = fields.Char(string='Corporate Action Memo', default='Stock Split Adjustment')

    def action_apply_split(self):
        """Execute stock split across all holding accounts for this security."""
        self.ensure_one()
        ratio = 2.0
        if self.split_ratio_type == '2_for_1':
            ratio = 2.0
        elif self.split_ratio_type == '3_for_1':
            ratio = 3.0
        elif self.split_ratio_type == '4_for_1':
            ratio = 4.0
        elif self.split_ratio_type == '5_for_1':
            ratio = 5.0
        elif self.split_ratio_type == '10_for_1':
            ratio = 10.0
        elif self.split_ratio_type == 'custom':
            ratio = float(self.custom_multiplier or 1.0)

        if ratio <= 0:
            raise UserError(_("Split ratio multiplier must be strictly positive."))

        # Find all accounts holding this security
        holdings = self.env['moneta.holding'].search([('security_id', '=', self.security_id.id)])
        if not holdings:
            raise UserError(_("No active holdings found for security %s.") % self.security_id.symbol)

        for h in holdings:
            self.env['moneta.investment.transaction'].create({
                'action': 'split',
                'account_id': h.account_id.id,
                'security_id': self.security_id.id,
                'trade_date': self.split_date,
                'quantity': ratio,
                'memo': f"{self.memo} ({ratio:g}:1)",
            })

        action = self.env.ref('moneta_finance.action_moneta_holding').read()[0]
        return action
