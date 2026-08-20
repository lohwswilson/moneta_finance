# -*- coding: utf-8 -*-
import math
import random
from odoo import models, fields, api


class MonetaMonteCarlo(models.Model):
    _name = 'moneta.monte.carlo'
    _description = 'Moneta Monte Carlo Wealth & Retirement Simulator'
    _order = 'name asc'

    name = fields.Char(string='Plan Name', required=True, default='My Retirement Plan')
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    # Initial Assumptions
    starting_portfolio_value = fields.Monetary(string='Current Portfolio Value', required=True, default=250000.0)
    annual_savings_contribution = fields.Monetary(string='Annual Savings / Contribution', default=20000.0)
    years_to_retirement = fields.Integer(string='Years to Retirement', default=15, required=True)
    years_in_retirement = fields.Integer(string='Years in Retirement', default=30, required=True)
    annual_retirement_spend = fields.Monetary(string='Annual Retirement Spending (Today $)', default=75000.0, required=True)

    # Asset Allocation & Market Assumptions
    equity_allocation_pct = fields.Float(string='Equities / Stock Allocation (%)', default=75.0)
    bond_allocation_pct = fields.Float(string='Bonds / Fixed Income (%)', default=25.0)
    inflation_rate_pct = fields.Float(string='Expected Inflation Rate (%)', default=2.5)

    # Simulation Outputs
    simulations_count = fields.Integer(string='Simulations Run', default=1000, readonly=True)
    success_probability_pct = fields.Float(string='Success Probability (%)', digits=(5, 1), readonly=True)
    median_wealth_at_retirement = fields.Monetary(string='Median Wealth at Retirement (P50)', readonly=True)
    p10_ending_wealth = fields.Monetary(string='Conservative Ending Wealth (P10)', readonly=True)
    p50_ending_wealth = fields.Monetary(string='Median Ending Wealth (P50)', readonly=True)
    p90_ending_wealth = fields.Monetary(string='Optimistic Ending Wealth (P90)', readonly=True)

    path_ids = fields.One2many('moneta.monte.carlo.path', 'simulation_id', string='Projected Trajectory')

    @api.onchange('equity_allocation_pct')
    def _onchange_equity_allocation(self):
        self.bond_allocation_pct = max(100.0 - (self.equity_allocation_pct or 0.0), 0.0)

    def action_run_simulation(self):
        """Execute 1,000 Monte Carlo stochastic geometric paths."""
        self.ensure_one()
        self.path_ids.unlink()

        W0 = float(self.starting_portfolio_value or 0.0)
        annual_save = float(self.annual_savings_contribution or 0.0)
        y_accum = int(self.years_to_retirement or 15)
        y_retire = int(self.years_in_retirement or 30)
        total_years = y_accum + y_retire
        annual_spend = float(self.annual_retirement_spend or 0.0)

        eq_w = (float(self.equity_allocation_pct or 75.0)) / 100.0
        bd_w = (float(self.bond_allocation_pct or 25.0)) / 100.0
        inf = (float(self.inflation_rate_pct or 2.5)) / 100.0

        # Asset Class Expected Real Returns and Volatility
        # Equities: Mean = 9.5% nominal, Vol = 16.0%
        # Bonds: Mean = 4.5% nominal, Vol = 6.0%
        eq_mu, eq_sigma = 0.095, 0.160
        bd_mu, bd_sigma = 0.045, 0.060

        port_mu = (eq_w * eq_mu) + (bd_w * bd_mu)
        port_sigma = math.sqrt((eq_w * eq_sigma)**2 + (bd_w * bd_sigma)**2 + 2 * eq_w * bd_w * 0.2 * eq_sigma * bd_sigma)

        num_sims = 1000
        yearly_wealth = [[] for _ in range(total_years + 1)]
        for sim in range(num_sims):
            yearly_wealth[0].append(W0)

        success_count = 0
        retirement_wealths = []
        ending_wealths = []

        for sim in range(num_sims):
            w = W0
            survived = True
            for yr in range(1, total_years + 1):
                # Sample annual log-return from normal distribution
                ret = random.gauss(port_mu - 0.5 * port_sigma**2, port_sigma)
                growth_factor = math.exp(ret)

                if yr <= y_accum:
                    # Accumulation phase: grow portfolio + add savings
                    w = (w + annual_save) * growth_factor
                else:
                    # Distribution / Retirement phase: spend adjusted for inflation
                    inflated_spend = annual_spend * ((1.0 + inf) ** (yr - 1))
                    w = (w - inflated_spend) * growth_factor

                if w <= 0.0:
                    w = 0.0
                    survived = False

                yearly_wealth[yr].append(w)
                if yr == y_accum:
                    retirement_wealths.append(w)

            ending_wealths.append(w)
            if survived and w > 0:
                success_count += 1

        # Calculate percentiles per year
        paths = []
        for yr in range(0, total_years + 1):
            vals = sorted(yearly_wealth[yr])
            p10 = vals[int(0.10 * num_sims)]
            p50 = vals[int(0.50 * num_sims)]
            p90 = vals[int(0.90 * num_sims)]
            paths.append({
                'simulation_id': self.id,
                'year_number': yr,
                'phase': 'Accumulation' if yr <= y_accum else 'Retirement',
                'p10_conservative': round(p10, 4),
                'p50_median': round(p50, 4),
                'p90_optimistic': round(p90, 4),
                'currency_id': self.currency_id.id,
            })

        self.env['moneta.monte.carlo.path'].create(paths)

        ret_sorted = sorted(retirement_wealths)
        end_sorted = sorted(ending_wealths)

        self.write({
            'simulations_count': num_sims,
            'success_probability_pct': round((success_count / num_sims) * 100.0, 1),
            'median_wealth_at_retirement': round(ret_sorted[int(0.50 * len(ret_sorted))], 4) if ret_sorted else 0.0,
            'p10_ending_wealth': round(end_sorted[int(0.10 * len(end_sorted))], 4) if end_sorted else 0.0,
            'p50_ending_wealth': round(end_sorted[int(0.50 * len(end_sorted))], 4) if end_sorted else 0.0,
            'p90_ending_wealth': round(end_sorted[int(0.90 * len(end_sorted))], 4) if end_sorted else 0.0,
        })
        return True


class MonetaMonteCarloPath(models.Model):
    _name = 'moneta.monte.carlo.path'
    _description = 'Moneta Monte Carlo Trajectory Point'
    _order = 'year_number asc'

    simulation_id = fields.Many2one('moneta.monte.carlo', string='Simulation', ondelete='cascade', required=True)
    currency_id = fields.Many2one('res.currency', related='simulation_id.currency_id', store=True, readonly=True)
    user_id = fields.Many2one('res.users', related='simulation_id.user_id', store=True, index=True)

    year_number = fields.Integer(string='Year', required=True)
    phase = fields.Selection([('Accumulation', 'Accumulation'), ('Retirement', 'Retirement')], string='Phase')
    p10_conservative = fields.Monetary(string='10th %ile (Conservative)')
    p50_median = fields.Monetary(string='50th %ile (Median)')
    p90_optimistic = fields.Monetary(string='90th %ile (Optimistic)')
