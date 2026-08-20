# -*- coding: utf-8 -*-
from datetime import date, timedelta
from calendar import monthrange
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaGemStrategy(models.Model):
    _name = 'moneta.gem.strategy'
    _description = 'Moneta GEM (Global Equities Momentum) Strategy'
    _order = 'name'

    name = fields.Char(string='Strategy Name', required=True)
    cadence = fields.Selection([
        ('monthly', 'Monthly (1st of month)'),
        ('quarterly', 'Quarterly (1st of Jan/Apr/Jul/Oct)'),
    ], string='Cadence', default='monthly', required=True)
    lookback_months = fields.Integer(string='Lookback Window (Months)', default=12, required=True)

    account_ids = fields.Many2many(
        'moneta.account',
        'moneta_gem_strategy_account_rel',
        'strategy_id',
        'account_id',
        string='Assigned Brokerage Accounts',
    )

    # Role mappings
    us_equity_security_id = fields.Many2one(
        'moneta.security', string='US Equity Role (e.g. VTI/SPY)', required=True
    )
    world_equity_security_id = fields.Many2one(
        'moneta.security', string='World / Ex-US Equity Role (e.g. VEU/VXUS)'
    )
    emerging_equity_security_id = fields.Many2one(
        'moneta.security', string='Emerging Markets Role (e.g. VWO/EEM)'
    )
    safe_asset_security_id = fields.Many2one(
        'moneta.security', string='Safe Asset Role (e.g. BND/AGG)', required=True
    )
    risk_free_security_id = fields.Many2one(
        'moneta.security',
        string='Risk-Free Benchmark Role (e.g. BIL/SHY)',
        help='Yardstick for absolute momentum. If unset, Safe Asset is used.',
    )

    estimated_tax_rate = fields.Float(string='Estimated Tax Rate (%)', default=0.0)
    commission = fields.Monetary(string='Estimated Commission', default=0.0)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Signal Evaluation
    current_signal = fields.Selection([
        ('risk_on_us', 'Risk-On: US Equity'),
        ('risk_on_world', 'Risk-On: World / Ex-US Equity'),
        ('risk_on_emerging', 'Risk-On: Emerging Markets'),
        ('risk_off_safe', 'Risk-Off: Safe Asset (Bonds/Cash)'),
        ('no_signal', 'No Signal / Incomplete Price Data'),
    ], string='Current Allocation Signal', default='no_signal')

    target_security_id = fields.Many2one('moneta.security', string='Target Security to Hold')
    signal_reasoning = fields.Text(string='Momentum Reasoning')
    last_evaluated_date = fields.Date(string='Last Evaluated Date')

    signal_ids = fields.One2many('moneta.gem.signal', 'strategy_id', string='Historical Signals')

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    # ------------------------------------------------------------------
    # Momentum Calculation Helpers
    # ------------------------------------------------------------------

    def _get_trailing_return(self, security, as_of_date, lookback_months):
        """Calculate trailing simple return over lookback_months ending on as_of_date."""
        if not security:
            return None

        # End price: nearest price on or before as_of_date
        end_price_rec = self.env['moneta.security.price'].search([
            ('security_id', '=', security.id),
            ('price_date', '<=', as_of_date),
        ], order='price_date desc', limit=1)

        if not end_price_rec or end_price_rec.price_close <= 0:
            return None

        # Start date: as_of_date minus lookback_months
        idx = as_of_date.month - 1 - lookback_months
        start_year = as_of_date.year + idx // 12
        start_month = idx % 12 + 1
        start_day = min(as_of_date.day, monthrange(start_year, start_month)[1])
        start_target_date = date(start_year, start_month, start_day)

        # Start price: nearest price on or after start_target_date, but before end_price date
        start_price_rec = self.env['moneta.security.price'].search([
            ('security_id', '=', security.id),
            ('price_date', '>=', start_target_date),
            ('price_date', '<=', end_price_rec.price_date),
        ], order='price_date asc', limit=1)

        if not start_price_rec or start_price_rec.price_close <= 0 or start_price_rec.id == end_price_rec.id:
            # Fallback: nearest price before start_target_date
            start_price_rec = self.env['moneta.security.price'].search([
                ('security_id', '=', security.id),
                ('price_date', '<=', start_target_date),
            ], order='price_date desc', limit=1)

        if not start_price_rec or start_price_rec.price_close <= 0 or start_price_rec.id == end_price_rec.id:
            return None

        ret = (end_price_rec.price_close - start_price_rec.price_close) / start_price_rec.price_close
        return ret

    def action_evaluate_signal(self):
        """Evaluate dual momentum rules against prices up to today."""
        today = fields.Date.context_today(self)
        for strategy in self:
            strategy._evaluate_for_date(today)
        return True

    def _evaluate_for_date(self, as_of_date):
        self.ensure_one()

        rf_sec = self.risk_free_security_id or self.safe_asset_security_id
        us_ret = self._get_trailing_return(self.us_equity_security_id, as_of_date, self.lookback_months)
        world_ret = self._get_trailing_return(self.world_equity_security_id, as_of_date, self.lookback_months)
        em_ret = self._get_trailing_return(self.emerging_equity_security_id, as_of_date, self.lookback_months)
        safe_ret = self._get_trailing_return(self.safe_asset_security_id, as_of_date, self.lookback_months)
        rf_ret = self._get_trailing_return(rf_sec, as_of_date, self.lookback_months)

        # If US equity return or risk-free return is missing, we cannot evaluate
        if us_ret is None or rf_ret is None:
            self.write({
                'current_signal': 'no_signal',
                'target_security_id': False,
                'signal_reasoning': 'Incomplete price history for US Equity or Risk-Free yardstick. Cannot evaluate momentum.',
                'last_evaluated_date': as_of_date,
            })
            return

        # 1. Absolute Momentum: US Equity vs Risk-Free
        is_risk_on = us_ret > rf_ret

        reasoning_lines = [
            f"Evaluated as of {as_of_date} over {self.lookback_months}M lookback:",
            f"• US Equity ({self.us_equity_security_id.symbol}): {us_ret * 100:.2f}%",
        ]
        if self.world_equity_security_id and world_ret is not None:
            reasoning_lines.append(f"• World/Ex-US Equity ({self.world_equity_security_id.symbol}): {world_ret * 100:.2f}%")
        if self.emerging_equity_security_id and em_ret is not None:
            reasoning_lines.append(f"• Emerging Markets ({self.emerging_equity_security_id.symbol}): {em_ret * 100:.2f}%")
        if safe_ret is not None:
            reasoning_lines.append(f"• Safe Asset ({self.safe_asset_security_id.symbol}): {safe_ret * 100:.2f}%")
        if rf_sec != self.safe_asset_security_id and rf_ret is not None:
            reasoning_lines.append(f"• Risk-Free Yardstick ({rf_sec.symbol}): {rf_ret * 100:.2f}%")

        if is_risk_on:
            # 2. Relative Momentum: Find highest equity return
            candidates = [(self.us_equity_security_id, us_ret, 'risk_on_us')]
            if self.world_equity_security_id and world_ret is not None:
                candidates.append((self.world_equity_security_id, world_ret, 'risk_on_world'))
            if self.emerging_equity_security_id and em_ret is not None:
                candidates.append((self.emerging_equity_security_id, em_ret, 'risk_on_emerging'))

            # Best return wins
            winner_sec, winner_ret, winner_signal = max(candidates, key=lambda x: x[1])

            reasoning_lines.append(
                f"\nOutcome: RISK-ON. US Equity ({us_ret * 100:.2f}%) beat Risk-Free ({rf_ret * 100:.2f}%).\n"
                f"Top Equity: {winner_sec.name} ({winner_sec.symbol}) with {winner_ret * 100:.2f}% trailing return."
            )

            signal_val = winner_signal
            target_sec = winner_sec
        else:
            reasoning_lines.append(
                f"\nOutcome: RISK-OFF. US Equity ({us_ret * 100:.2f}%) did not beat Risk-Free ({rf_ret * 100:.2f}%).\n"
                f"Allocating 100% to Safe Asset: {self.safe_asset_security_id.name} ({self.safe_asset_security_id.symbol})."
            )
            signal_val = 'risk_off_safe'
            target_sec = self.safe_asset_security_id

        self.write({
            'current_signal': signal_val,
            'target_security_id': target_sec.id if target_sec else False,
            'signal_reasoning': '\n'.join(reasoning_lines),
            'last_evaluated_date': as_of_date,
        })

        # Record historical signal
        self.env['moneta.gem.signal'].create({
            'strategy_id': self.id,
            'period_date': as_of_date,
            'signal_type': signal_val,
            'target_security_id': target_sec.id if target_sec else False,
            'us_equity_return': us_ret or 0.0,
            'world_equity_return': world_ret or 0.0,
            'emerging_equity_return': em_ret or 0.0,
            'safe_asset_return': safe_ret or 0.0,
            'risk_free_return': rf_ret or 0.0,
        })


class MonetaGemSignal(models.Model):
    _name = 'moneta.gem.signal'
    _description = 'Moneta GEM Strategy Historical Signal'
    _order = 'period_date desc, id desc'

    strategy_id = fields.Many2one('moneta.gem.strategy', string='Strategy', required=True, ondelete='cascade')
    period_date = fields.Date(string='Signal Date', required=True, default=fields.Date.context_today)

    signal_type = fields.Selection([
        ('risk_on_us', 'Risk-On: US Equity'),
        ('risk_on_world', 'Risk-On: World / Ex-US Equity'),
        ('risk_on_emerging', 'Risk-On: Emerging Markets'),
        ('risk_off_safe', 'Risk-Off: Safe Asset (Bonds/Cash)'),
        ('no_signal', 'No Signal / Incomplete Data'),
    ], string='Signal', required=True)

    target_security_id = fields.Many2one('moneta.security', string='Target Security')

    us_equity_return = fields.Float(string='US Equity Return', digits=(6, 4))
    world_equity_return = fields.Float(string='World Equity Return', digits=(6, 4))
    emerging_equity_return = fields.Float(string='Emerging Equity Return', digits=(6, 4))
    safe_asset_return = fields.Float(string='Safe Asset Return', digits=(6, 4))
    risk_free_return = fields.Float(string='Risk-Free Return', digits=(6, 4))

    is_executed = fields.Boolean(string='Executed / Rebalanced', default=False)
    user_id = fields.Many2one('res.users', related='strategy_id.user_id', store=True, index=True)
