# -*- coding: utf-8 -*-
import base64
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaTaxScheduleWizard(models.TransientModel):
    _name = 'moneta.tax.schedule.wizard'
    _description = 'Tax Schedule Summary & TurboTax TXF Exporter'

    tax_year = fields.Selection([
        (str(y), str(y)) for y in range(2020, 2031)
    ], string='Tax Year', default=lambda self: str(fields.Date.today().year), required=True)

    user_id = fields.Many2one('res.users', string='Taxpayer', default=lambda self: self.env.user, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    # Form 8949 / Schedule D: Capital Gains
    short_term_proceeds = fields.Monetary(string='Short-Term Gross Proceeds', readonly=True)
    short_term_cost_basis = fields.Monetary(string='Short-Term Cost Basis', readonly=True)
    short_term_gain = fields.Monetary(string='Net Short-Term Capital Gain / Loss', readonly=True)

    long_term_proceeds = fields.Monetary(string='Long-Term Gross Proceeds', readonly=True)
    long_term_cost_basis = fields.Monetary(string='Long-Term Cost Basis', readonly=True)
    long_term_gain = fields.Monetary(string='Net Long-Term Capital Gain / Loss', readonly=True)

    total_capital_gain = fields.Monetary(string='Total Net Capital Gain / Loss', readonly=True)

    # 1099-DIV & 1099-INT: Dividends & Interest
    total_dividend_income = fields.Monetary(string='Total Ordinary Dividends (1099-DIV)', readonly=True)
    total_interest_income = fields.Monetary(string='Total Taxable Interest (1099-INT)', readonly=True)

    # Schedule E: Rental Real Estate
    total_rental_income = fields.Monetary(string='Gross Rents Received (Schedule E)', readonly=True)
    total_rental_expenses = fields.Monetary(string='Total Rental Expenses', readonly=True)
    net_rental_income = fields.Monetary(string='Net Rental Real Estate Income', readonly=True)

    # Exported TXF File
    txf_filename = fields.Char(string='File Name')
    txf_file = fields.Binary(string='TurboTax TXF File', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
    ], string='State', default='draft')

    @api.onchange('tax_year')
    def _onchange_tax_year(self):
        if self.tax_year:
            self.action_calculate_tax_schedule()

    def action_calculate_tax_schedule(self):
        """Aggregates annual capital gains, dividends, interest, and rental income for the selected tax year."""
        self.ensure_one()
        year = int(self.tax_year or fields.Date.today().year)
        start_d = date(year, 1, 1)
        end_d = date(year, 12, 31)

        # 1. Capital Gains & Disposals
        disposals = self.env['moneta.security.lot.disposal'].search([
            ('disposal_date', '>=', start_d),
            ('disposal_date', '<=', end_d),
            ('lot_id.user_id', '=', self.user_id.id),
        ])

        st_disposals = disposals.filtered(lambda d: d.term_type == 'short_term')
        lt_disposals = disposals.filtered(lambda d: d.term_type == 'long_term')

        st_proc = sum(d.proceeds for d in st_disposals)
        st_cost = sum(d.cost_basis_sold for d in st_disposals)
        st_gain = st_proc - st_cost

        lt_proc = sum(d.proceeds for d in lt_disposals)
        lt_cost = sum(d.cost_basis_sold for d in lt_disposals)
        lt_gain = lt_proc - lt_cost

        # 2. Dividends & Interest
        div_txs = self.env['moneta.investment.transaction'].search([
            ('action', '=', 'dividend'),
            ('trade_date', '>=', start_d),
            ('trade_date', '<=', end_d),
            ('state', '!=', 'void'),
            ('user_id', '=', self.user_id.id),
        ])
        tot_div = sum(t.total_amount for t in div_txs if t.total_amount)

        int_txs = self.env['moneta.investment.transaction'].search([
            ('action', '=', 'interest'),
            ('trade_date', '>=', start_d),
            ('trade_date', '<=', end_d),
            ('state', '!=', 'void'),
            ('user_id', '=', self.user_id.id),
        ])
        tot_int = sum(t.total_amount for t in int_txs if t.total_amount)

        # Also check interest in bank transaction registers
        bank_int_txs = self.env['moneta.transaction'].search([
            ('transaction_date', '>=', start_d),
            ('transaction_date', '<=', end_d),
            ('amount', '>', 0),
            ('state', '!=', 'void'),
            ('user_id', '=', self.user_id.id),
            ('category_id.name', 'ilike', 'interest'),
        ])
        tot_int += sum(t.amount for t in bank_int_txs)

        # 3. Schedule E Rental Real Estate
        rent_payments = self.env['moneta.property.rent.payment'].search([
            ('due_date', '>=', start_d),
            ('due_date', '<=', end_d),
            ('payment_status', '=', 'paid'),
            ('property_id.user_id', '=', self.user_id.id),
        ])
        tot_rent_inc = sum(p.amount_paid for p in rent_payments)

        properties = self.env['moneta.property'].search([
            ('asset_category', '=', 'real_estate'),
            ('user_id', '=', self.user_id.id),
        ])
        tot_rent_exp = sum(
            (float(p.monthly_property_tax or 0.0) +
             float(p.monthly_insurance or 0.0) +
             float(p.monthly_hoa_maintenance or 0.0)) * 12.0
            for p in properties
        )

        self.write({
            'short_term_proceeds': round(st_proc, 2),
            'short_term_cost_basis': round(st_cost, 2),
            'short_term_gain': round(st_gain, 2),
            'long_term_proceeds': round(lt_proc, 2),
            'long_term_cost_basis': round(lt_cost, 2),
            'long_term_gain': round(lt_gain, 2),
            'total_capital_gain': round(st_gain + lt_gain, 2),
            'total_dividend_income': round(tot_div, 2),
            'total_interest_income': round(tot_int, 2),
            'total_rental_income': round(tot_rent_inc, 2),
            'total_rental_expenses': round(tot_rent_exp, 2),
            'net_rental_income': round(tot_rent_inc - tot_rent_exp, 2),
            'state': 'calculated',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.tax.schedule.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_export_txf(self):
        """Generates standard TurboTax / TaxSlayer Tax Exchange Format (.txf) file."""
        self.ensure_one()
        self.action_calculate_tax_schedule()

        year = int(self.tax_year)
        start_d = date(year, 1, 1)
        end_d = date(year, 12, 31)

        lines = [
            "V042",
            "A Moneta Personal Finance",
            f"D {fields.Date.today().strftime('%m/%d/%Y')}",
            "^",
        ]

        # 1. Export Capital Gains (Schedule D / Form 8949)
        disposals = self.env['moneta.security.lot.disposal'].search([
            ('disposal_date', '>=', start_d),
            ('disposal_date', '<=', end_d),
            ('lot_id.user_id', '=', self.user_id.id),
        ], order='disposal_date asc')

        for d in disposals:
            code = "714" if d.term_type == 'long_term' else "712"
            lot = d.lot_id
            sec_name = lot.security_id.symbol or lot.security_id.name or 'Security'
            desc = f"{d.quantity_sold:,.2f} shs {sec_name}"

            lines.extend([
                "TD",
                f"N{code}",
                "C1",
                "L1",
                f"P{desc}",
                f"D{lot.purchase_date.strftime('%m/%d/%Y') if lot.purchase_date else ''}",
                f"D{d.disposal_date.strftime('%m/%d/%Y')}",
                f"${d.cost_basis_sold:.2f}",
                f"${d.proceeds:.2f}",
                "^",
            ])

        # 2. Export 1099-DIV (Dividend Income - Code 291)
        if self.total_dividend_income > 0:
            lines.extend([
                "TD",
                "N291",
                "C1",
                "L1",
                "PTotal Ordinary Dividends",
                f"${self.total_dividend_income:.2f}",
                "^",
            ])

        # 3. Export 1099-INT (Interest Income - Code 289)
        if self.total_interest_income > 0:
            lines.extend([
                "TD",
                "N289",
                "C1",
                "L1",
                "PTaxable Interest Income",
                f"${self.total_interest_income:.2f}",
                "^",
            ])

        # 4. Export Schedule E (Rental Real Estate - Code 268)
        if self.total_rental_income > 0:
            lines.extend([
                "TD",
                "N268",
                "C1",
                "L1",
                "PGross Rents Received",
                f"${self.total_rental_income:.2f}",
                "^",
            ])

        txf_content = "\r\n".join(lines) + "\r\n"
        encoded = base64.b64encode(txf_content.encode('utf-8'))
        fname = f"moneta_tax_schedule_{self.tax_year}.txf"

        self.write({
            'txf_file': encoded,
            'txf_filename': fname,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.tax.schedule.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
