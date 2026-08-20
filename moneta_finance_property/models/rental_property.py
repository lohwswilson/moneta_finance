# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class MonetaPropertyRental(models.Model):
    """Extends moneta.property with rental units, operating expenses, tenant roll, and landlord NOI metrics."""
    _inherit = 'moneta.property'

    monthly_rental_income = fields.Monetary(
        string='Monthly Rental Income (Base)', currency_field='currency_id',
        help='Base or estimated monthly rent if not using the detailed tenant roll.'
    )
    monthly_property_tax = fields.Monetary(
        string='Monthly Property Tax', currency_field='currency_id',
        help='Monthly property tax allocation.'
    )
    monthly_insurance = fields.Monetary(
        string='Monthly Property Insurance', currency_field='currency_id',
        help='Monthly hazard / landlord insurance premium.'
    )
    monthly_hoa_maintenance = fields.Monetary(
        string='Monthly HOA / Maintenance', currency_field='currency_id',
        help='Monthly condo HOA fees, management fees, or sinking fund maintenance.'
    )

    tenant_ids = fields.One2many('moneta.property.tenant', 'property_id', string='Tenants & Leases')
    tenant_count = fields.Integer(string='Active Tenants', compute='_compute_rental_metrics', store=True)
    gross_annual_rental_income = fields.Monetary(
        string='Gross Annual Rent', currency_field='currency_id',
        compute='_compute_rental_metrics', store=True,
        help='Annualized gross rental income from all active tenant leases.'
    )
    gross_rental_yield_pct = fields.Float(
        string='Gross Rental Yield (%)', compute='_compute_rental_metrics', store=True,
        help='Gross Annual Rent / Current Market Value * 100.'
    )
    net_operating_income = fields.Monetary(
        string='Net Operating Income (NOI)', currency_field='currency_id',
        compute='_compute_rental_metrics', store=True,
        help='Gross Annual Rent minus Annual Operating Expenses (Taxes, Insurance, HOA).'
    )
    net_monthly_cashflow = fields.Monetary(
        string='Net Monthly Cash Flow', currency_field='currency_id',
        compute='_compute_rental_metrics', store=True,
        help='Monthly Rent minus Operating Expenses minus Monthly Mortgage Payment.'
    )
    occupancy_rate_pct = fields.Float(
        string='Occupancy Rate (%)', compute='_compute_rental_metrics', store=True,
        help='100% if active lease exists, 0% if vacant.'
    )

    @api.depends(
        'current_market_value', 'monthly_rental_income', 'monthly_property_tax',
        'monthly_insurance', 'monthly_hoa_maintenance', 'tenant_ids',
        'tenant_ids.lease_status', 'tenant_ids.monthly_rent_amount', 'mortgage_account_id'
    )
    def _compute_rental_metrics(self):
        for prop in self:
            active_tenants = prop.tenant_ids.filtered(lambda t: t.lease_status == 'active')
            prop.tenant_count = len(active_tenants)
            prop.occupancy_rate_pct = 100.0 if active_tenants else 0.0

            if active_tenants:
                monthly_rent = sum(active_tenants.mapped('monthly_rent_amount'))
            else:
                monthly_rent = float(prop.monthly_rental_income or 0.0)

            annual_gross_rent = monthly_rent * 12.0
            prop.gross_annual_rental_income = annual_gross_rent

            mkt_val = float(prop.current_market_value or 0.0)
            prop.gross_rental_yield_pct = round((annual_gross_rent / mkt_val * 100.0) if mkt_val > 0 else 0.0, 2)

            monthly_opex = float(prop.monthly_property_tax or 0.0) + float(prop.monthly_insurance or 0.0) + float(prop.monthly_hoa_maintenance or 0.0)
            annual_opex = monthly_opex * 12.0
            prop.net_operating_income = annual_gross_rent - annual_opex

            mortgage_monthly = 0.0
            if prop.mortgage_account_id and hasattr(prop.mortgage_account_id, 'monthly_payment'):
                mortgage_monthly = float(prop.mortgage_account_id.monthly_payment or 0.0)

            prop.net_monthly_cashflow = monthly_rent - monthly_opex - mortgage_monthly


class MonetaPropertyTenant(models.Model):
    """Tenant lease roll tracking with automated rent collection schedules."""
    _name = 'moneta.property.tenant'
    _description = 'Property Tenant & Lease Agreement'
    _order = 'lease_start_date desc, name asc'

    name = fields.Char(string='Tenant Full Name', required=True)
    property_id = fields.Many2one(
        'moneta.property', string='Rental Property',
        domain="[('asset_category', '=', 'real_estate')]",
        required=True, ondelete='cascade'
    )
    unit_number = fields.Char(string='Unit / Apt #')
    email = fields.Char(string='Tenant Email')
    phone = fields.Char(string='Tenant Phone')
    emergency_contact = fields.Char(string='Emergency Contact')

    user_id = fields.Many2one('res.users', related='property_id.user_id', store=True, index=True)
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id', store=True)

    lease_start_date = fields.Date(string='Lease Start Date', required=True, default=fields.Date.context_today)
    lease_end_date = fields.Date(string='Lease End Date', required=True)
    monthly_rent_amount = fields.Monetary(string='Monthly Rent', currency_field='currency_id', required=True)
    rent_due_day = fields.Integer(string='Rent Due Day of Month', default=1, required=True)

    security_deposit_held = fields.Monetary(string='Security Deposit Held', currency_field='currency_id')
    security_deposit_refunded = fields.Monetary(string='Deposit Refunded', currency_field='currency_id')
    deposit_status = fields.Selection([
        ('held', 'Held in Escrow'),
        ('partially_refunded', 'Partially Refunded'),
        ('refunded', 'Fully Refunded'),
        ('forfeited', 'Forfeited for Damages'),
    ], string='Deposit Status', default='held', required=True)

    lease_status = fields.Selection([
        ('upcoming', 'Upcoming Lease'),
        ('active', 'Active Lease'),
        ('expired', 'Expired'),
        ('terminated', 'Early Termination'),
    ], string='Lease Status', compute='_compute_lease_status', store=True)

    rent_payment_ids = fields.One2many(
        'moneta.property.rent.payment', 'tenant_id', string='Rent Roll Ledger'
    )
    total_rent_collected = fields.Monetary(
        string='Total Rent Collected', currency_field='currency_id',
        compute='_compute_rent_totals', store=True
    )
    total_rent_overdue = fields.Monetary(
        string='Total Overdue Rent', currency_field='currency_id',
        compute='_compute_rent_totals', store=True
    )
    notes = fields.Text(string='Lease Terms & Notes')

    @api.depends('lease_start_date', 'lease_end_date')
    def _compute_lease_status(self):
        today = fields.Date.context_today(self)
        for tenant in self:
            if not tenant.lease_start_date or not tenant.lease_end_date:
                tenant.lease_status = 'active'
            elif today < tenant.lease_start_date:
                tenant.lease_status = 'upcoming'
            elif today > tenant.lease_end_date:
                tenant.lease_status = 'expired'
            else:
                tenant.lease_status = 'active'

    @api.depends('rent_payment_ids', 'rent_payment_ids.payment_status', 'rent_payment_ids.amount_paid', 'rent_payment_ids.balance_due')
    def _compute_rent_totals(self):
        for tenant in self:
            tenant.total_rent_collected = sum(tenant.rent_payment_ids.mapped('amount_paid'))
            overdue_payments = tenant.rent_payment_ids.filtered(lambda p: p.payment_status == 'overdue')
            tenant.total_rent_overdue = sum(overdue_payments.mapped('balance_due'))

    def action_generate_rent_schedule(self):
        """Generates monthly rent payment records across the lease duration."""
        self.ensure_one()
        if not self.lease_start_date or not self.lease_end_date:
            raise UserError(_("Please specify both Lease Start and End dates before generating the rent schedule."))

        Payment = self.env['moneta.property.rent.payment']
        current_date = self.lease_start_date.replace(day=1)
        end_date = self.lease_end_date

        created_count = 0
        while current_date <= end_date:
            due_day = min(self.rent_due_day or 1, 28)
            due_d = current_date.replace(day=due_day)

            existing = Payment.search([
                ('tenant_id', '=', self.id),
                ('period_month', '=', current_date),
            ], limit=1)

            if not existing:
                Payment.create({
                    'tenant_id': self.id,
                    'period_month': current_date,
                    'due_date': due_d,
                    'amount_due': self.monthly_rent_amount,
                    'payment_status': 'pending',
                })
                created_count += 1

            current_date += relativedelta(months=1)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rent Schedule Generated"),
                'message': _("%s rent payment periods generated for tenant %s.", created_count, self.name),
                'type': 'success',
                'sticky': False,
            }
        }


class MonetaPropertyRentPayment(models.Model):
    """Individual monthly rent roll ledger payment record."""
    _name = 'moneta.property.rent.payment'
    _description = 'Property Rent Payment Record'
    _order = 'due_date desc'

    tenant_id = fields.Many2one('moneta.property.tenant', string='Tenant', required=True, ondelete='cascade')
    property_id = fields.Many2one('moneta.property', string='Property', related='tenant_id.property_id', store=True)
    user_id = fields.Many2one('res.users', related='tenant_id.user_id', store=True, index=True)
    currency_id = fields.Many2one('res.currency', related='tenant_id.currency_id', store=True)

    period_month = fields.Date(string='Rental Month', required=True, help='First day of rental month.')
    due_date = fields.Date(string='Due Date', required=True)
    amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id', required=True)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id', default=0.0)
    balance_due = fields.Monetary(
        string='Balance Due', currency_field='currency_id',
        compute='_compute_balance_due', store=True
    )
    paid_date = fields.Date(string='Date Paid')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid in Full'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived / Discounted'),
    ], string='Payment Status', default='pending', required=True)

    transaction_id = fields.Many2one('moneta.transaction', string='Linked Bank Transaction', help='Reconciled bank deposit transaction.')
    memo = fields.Char(string='Check # / Bank Ref')
    notes = fields.Char(string='Notes')

    @api.depends('amount_due', 'amount_paid')
    def _compute_balance_due(self):
        for rec in self:
            bal = max(float(rec.amount_due or 0.0) - float(rec.amount_paid or 0.0), 0.0)
            rec.balance_due = bal
            if rec.amount_paid >= rec.amount_due and rec.amount_due > 0:
                rec.payment_status = 'paid'
            elif rec.amount_paid > 0:
                rec.payment_status = 'partial'

    def action_mark_paid(self):
        """1-click action to mark rent payment as received today."""
        today = fields.Date.context_today(self)
        for rec in self:
            rec.write({
                'amount_paid': rec.amount_due,
                'paid_date': today,
                'payment_status': 'paid',
            })
