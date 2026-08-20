# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaProperty(models.Model):
    _name = 'moneta.property'
    _description = 'Moneta Real Estate, Vehicles, Antiques & Tangible Assets'
    _order = 'asset_category asc, name asc'

    name = fields.Char(string='Asset / Item Name', required=True)
    asset_category = fields.Selection([
        ('real_estate', 'Real Estate & Properties'),
        ('vehicle', 'Vehicles & Automobiles'),
        ('antiques', 'Antiques & Fine Art'),
        ('jewelry', 'Jewelry, Watches & Valuables'),
        ('collectibles', 'Collectibles, Coins & Bullion'),
        ('other', 'Other Tangible Assets'),
    ], string='Category', default='real_estate', required=True)

    property_type = fields.Selection([
        # Real Estate
        ('primary_residence', 'Primary Residence'),
        ('rental_property', 'Rental Property'),
        ('commercial', 'Commercial Real Estate'),
        ('land', 'Vacant Land / Plot'),
        # Vehicles
        ('automobile', 'Car / Automobile'),
        ('motorcycle', 'Motorcycle / Powersport'),
        ('boat', 'Boat / Yacht'),
        ('aircraft', 'Aircraft / Other Vehicle'),
        # Antiques & Collectibles
        ('antique_furniture', 'Antique Furniture'),
        ('fine_art', 'Fine Art & Paintings'),
        ('luxury_watch', 'Luxury Watch (Rolex, Patek, etc.)'),
        ('jewelry_gems', 'Jewelry & Precious Gems'),
        ('coins_bullion', 'Gold, Silver & Rare Coins'),
        ('wine_spirits', 'Fine Wine & Spirits Collection'),
        ('memorabilia', 'Sports & Historical Memorabilia'),
        ('electronics', 'High-End Audio / Electronics'),
        ('other', 'Other Valuable Asset'),
    ], string='Asset Sub-Type', default='primary_residence', required=True)

    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    # Photo & Media
    image_1920 = fields.Binary(string='Asset Photo', attachment=True)
    image_128 = fields.Binary(string='Thumbnail', related='image_1920', store=True)

    # Valuation & Purchase
    purchase_date = fields.Date(string='Purchase / Acquisition Date')
    purchase_price = fields.Monetary(string='Acquisition Cost', default=0.0)
    current_market_value = fields.Monetary(string='Current Market / Appraised Value', required=True, default=10000.0)
    appraisal_date = fields.Date(string='Last Appraisal Date')
    appraiser_name = fields.Char(string='Appraiser / Source')

    # Debt & Loan Linkage
    mortgage_account_id = fields.Many2one(
        'moneta.account', string='Linked Loan / Mortgage / Financing',
        domain="[('account_type', 'in', ('mortgage', 'loan', 'loc'))]",
    )
    mortgage_balance = fields.Monetary(string='Outstanding Debt', compute='_compute_equity', store=True)
    equity_value = fields.Monetary(string='Net Asset Equity ($)', compute='_compute_equity', store=True)
    loan_to_value_ratio = fields.Float(string='Loan-to-Value (LTV %)', compute='_compute_equity', store=True, digits=(5, 1))

    # --- Vehicle Specific Fields ---
    vehicle_make = fields.Char(string='Make / Manufacturer')
    vehicle_model = fields.Char(string='Model')
    vehicle_year = fields.Integer(string='Model Year', default=2024)
    vehicle_vin = fields.Char(string='VIN / Chassis #')
    vehicle_license_plate = fields.Char(string='License Plate')
    vehicle_mileage = fields.Integer(string='Current Mileage (Odometer)')
    annual_depreciation_rate = fields.Float(string='Annual Depreciation Rate (%)', default=15.0, digits=(5, 2))

    # --- Antiques, Collectibles & Valuables Fields ---
    antique_era = fields.Char(string='Period / Era / Year Made')
    maker_artist = fields.Char(string='Artist / Maker / Brand')
    condition_grade = fields.Selection([
        ('mint', 'Mint / Brand New'),
        ('near_mint', 'Near Mint / Like New'),
        ('excellent', 'Excellent / Restored'),
        ('good', 'Good / Original Patina'),
        ('fair', 'Fair / Needs Restoration'),
    ], string='Condition Grade', default='excellent')
    authenticity_cert_number = fields.Char(string='Certificate of Authenticity # / Serial #')
    storage_location = fields.Char(string='Storage Location / Safe Box')
    insured_value = fields.Monetary(string='Insured Value')
    insurance_policy_number = fields.Char(string='Insurance Policy # / Carrier')

    # --- Real Estate & Cash Flow Fields ---
    monthly_rental_income = fields.Monetary(string='Monthly Rental / Lease Income', default=0.0)
    monthly_property_tax = fields.Monetary(string='Monthly Property Tax', default=0.0)
    monthly_insurance = fields.Monetary(string='Monthly Insurance Premium', default=0.0)
    monthly_hoa_maintenance = fields.Monetary(string='Monthly Maintenance / HOA', default=0.0)
    net_monthly_cashflow = fields.Monetary(string='Net Monthly Cash Flow', compute='_compute_cashflow', store=True)

    # Historical Valuation Log
    valuation_line_ids = fields.One2many('moneta.property.valuation', 'property_id', string='Valuation History')

    # --- Landlord & Tenant Management (Track 4.3 Quicken Parity) ---
    tenant_ids = fields.One2many('moneta.property.tenant', 'property_id', string='Tenants & Leases')
    tenant_count = fields.Integer(string='Active Tenants', compute='_compute_rental_metrics', store=True)
    gross_annual_rental_income = fields.Monetary(string='Gross Annual Rent', compute='_compute_rental_metrics', store=True)
    gross_rental_yield_pct = fields.Float(string='Gross Rental Yield (%)', compute='_compute_rental_metrics', store=True, digits=(5, 2))
    net_operating_income = fields.Monetary(string='Annual Net Operating Income (NOI)', compute='_compute_rental_metrics', store=True)
    occupancy_rate_pct = fields.Float(string='Occupancy Rate (%)', compute='_compute_rental_metrics', store=True, digits=(5, 1))

    notes = fields.Text(string='Description, Provenance & Notes')

    @api.onchange('asset_category')
    def _onchange_asset_category(self):
        if self.asset_category == 'vehicle':
            self.property_type = 'automobile'
        elif self.asset_category == 'antiques':
            self.property_type = 'antique_furniture'
        elif self.asset_category == 'jewelry':
            self.property_type = 'luxury_watch'
        elif self.asset_category == 'collectibles':
            self.property_type = 'coins_bullion'
        elif self.asset_category == 'real_estate':
            self.property_type = 'primary_residence'

    @api.depends('current_market_value', 'currency_id', 'mortgage_account_id', 'mortgage_account_id.current_balance', 'mortgage_account_id.opening_balance', 'mortgage_account_id.currency_id')
    def _compute_equity(self):
        for prop in self:
            val = float(prop.current_market_value or 0.0)
            debt = 0.0
            if prop.mortgage_account_id:
                acc = prop.mortgage_account_id
                acc_bal = float(acc.current_balance or acc.opening_balance or 0.0)
                raw_debt = abs(acc_bal)
                if acc.currency_id and prop.currency_id and acc.currency_id != prop.currency_id:
                    debt = acc.currency_id._convert(raw_debt, prop.currency_id, self.env.company, fields.Date.context_today(self))
                else:
                    debt = raw_debt
            prop.mortgage_balance = round(debt, 4)
            prop.equity_value = round(val - debt, 4)
            if val > 0:
                prop.loan_to_value_ratio = round((debt / val) * 100.0, 1)
            else:
                prop.loan_to_value_ratio = 0.0

    @api.depends('monthly_rental_income', 'monthly_property_tax', 'monthly_insurance', 'monthly_hoa_maintenance')
    def _compute_cashflow(self):
        for prop in self:
            inc = float(prop.monthly_rental_income or 0.0)
            tax = float(prop.monthly_property_tax or 0.0)
            ins = float(prop.monthly_insurance or 0.0)
            hoa = float(prop.monthly_hoa_maintenance or 0.0)
            prop.net_monthly_cashflow = round(inc - (tax + ins + hoa), 4)

    @api.depends('tenant_ids.lease_status', 'tenant_ids.monthly_rent_amount', 'current_market_value', 'monthly_property_tax', 'monthly_insurance', 'monthly_hoa_maintenance')
    def _compute_rental_metrics(self):
        for prop in self:
            active_tenants = prop.tenant_ids.filtered(lambda t: t.lease_status == 'active')
            prop.tenant_count = len(active_tenants)
            
            # Monthly rent from active leases (or manual monthly_rental_income fallback)
            lease_rent = sum(t.monthly_rent_amount for t in active_tenants)
            effective_monthly_rent = lease_rent if lease_rent > 0 else (prop.monthly_rental_income or 0.0)
            annual_rent = effective_monthly_rent * 12.0
            prop.gross_annual_rental_income = round(annual_rent, 2)

            # Annual operating expenses
            annual_expenses = (float(prop.monthly_property_tax or 0.0) +
                               float(prop.monthly_insurance or 0.0) +
                               float(prop.monthly_hoa_maintenance or 0.0)) * 12.0
            prop.net_operating_income = round(annual_rent - annual_expenses, 2)

            # Yield
            mkt_val = float(prop.current_market_value or 0.0)
            if mkt_val > 0:
                prop.gross_rental_yield_pct = round((annual_rent / mkt_val) * 100.0, 2)
            else:
                prop.gross_rental_yield_pct = 0.0

            prop.occupancy_rate_pct = 100.0 if active_tenants else 0.0


class MonetaPropertyTenant(models.Model):
    _name = 'moneta.property.tenant'
    _description = 'Rental Property Tenant & Lease Agreement'
    _order = 'lease_start_date desc, id desc'

    name = fields.Char(string='Tenant Full Name', required=True)
    property_id = fields.Many2one(
        'moneta.property', string='Rental Property',
        domain="[('asset_category', '=', 'real_estate')]", required=True, ondelete='cascade'
    )
    user_id = fields.Many2one('res.users', string='Owner', related='property_id.user_id', store=True, index=True)
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id', store=True, readonly=True)

    unit_number = fields.Char(string='Unit / Suite / Room #')
    email = fields.Char(string='Email Address')
    phone = fields.Char(string='Phone / Mobile')
    emergency_contact = fields.Char(string='Emergency Contact')

    # Lease Terms
    lease_start_date = fields.Date(string='Lease Start Date', required=True)
    lease_end_date = fields.Date(string='Lease End Date', required=True)
    monthly_rent_amount = fields.Monetary(string='Monthly Rent Amount', required=True, default=0.0)
    rent_due_day = fields.Integer(string='Rent Due Day of Month', default=1, required=True)

    # Security Deposit
    security_deposit_held = fields.Monetary(string='Security Deposit Held', default=0.0)
    security_deposit_refunded = fields.Monetary(string='Deposit Refunded', default=0.0)
    deposit_status = fields.Selection([
        ('held', 'Held in Escrow'),
        ('partially_refunded', 'Partially Refunded'),
        ('fully_refunded', 'Fully Refunded'),
        ('forfeited', 'Forfeited / Deducted for Repairs'),
    ], string='Deposit Status', default='held', required=True)

    lease_status = fields.Selection([
        ('upcoming', 'Upcoming Lease'),
        ('active', 'Active Lease'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated Early'),
    ], string='Lease Status', compute='_compute_lease_status', store=True)

    rent_payment_ids = fields.One2many(
        'moneta.property.rent.payment', 'tenant_id', string='Rent Roll Ledger'
    )
    total_rent_collected = fields.Monetary(string='Total Rent Collected', compute='_compute_payment_totals', store=True)
    total_rent_overdue = fields.Monetary(string='Total Rent Overdue', compute='_compute_payment_totals', store=True)
    notes = fields.Text(string='Lease Terms & Agreement Notes')

    @api.depends('lease_start_date', 'lease_end_date')
    def _compute_lease_status(self):
        today = fields.Date.today()
        for t in self:
            if not t.lease_start_date or not t.lease_end_date:
                t.lease_status = 'active'
            elif today < t.lease_start_date:
                t.lease_status = 'upcoming'
            elif today > t.lease_end_date:
                t.lease_status = 'expired'
            else:
                t.lease_status = 'active'

    @api.depends('rent_payment_ids.amount_paid', 'rent_payment_ids.balance_due', 'rent_payment_ids.payment_status')
    def _compute_payment_totals(self):
        for t in self:
            collected = sum(p.amount_paid for p in t.rent_payment_ids)
            overdue = sum(p.balance_due for p in t.rent_payment_ids if p.payment_status in ('late', 'overdue'))
            t.total_rent_collected = round(collected, 2)
            t.total_rent_overdue = round(overdue, 2)

    def action_generate_rent_schedule(self):
        """Generates monthly rent payment dues across the entire lease duration."""
        self.ensure_one()
        if not self.lease_start_date or not self.lease_end_date:
            return

        cur_date = self.lease_start_date
        Payment = self.env['moneta.property.rent.payment']

        while cur_date <= self.lease_end_date:
            due_d = cur_date.replace(day=min(self.rent_due_day or 1, 28))
            existing = Payment.search([
                ('tenant_id', '=', self.id),
                ('period_month', '=', cur_date.replace(day=1)),
            ], limit=1)

            if not existing:
                Payment.create({
                    'tenant_id': self.id,
                    'period_month': cur_date.replace(day=1),
                    'due_date': due_d,
                    'amount_due': self.monthly_rent_amount,
                })

            # Advance 1 month
            if cur_date.month == 12:
                cur_date = cur_date.replace(year=cur_date.year + 1, month=1)
            else:
                cur_date = cur_date.replace(month=cur_date.month + 1)


class MonetaPropertyRentPayment(models.Model):
    _name = 'moneta.property.rent.payment'
    _description = 'Rent Roll Payment Record'
    _order = 'due_date desc, id desc'

    tenant_id = fields.Many2one('moneta.property.tenant', string='Tenant', required=True, ondelete='cascade')
    property_id = fields.Many2one('moneta.property', string='Property', related='tenant_id.property_id', store=True)
    currency_id = fields.Many2one('res.currency', related='tenant_id.currency_id')

    period_month = fields.Date(string='Rental Month', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    paid_date = fields.Date(string='Paid Date')

    amount_due = fields.Monetary(string='Rent Due ($)', required=True)
    amount_paid = fields.Monetary(string='Rent Paid ($)', default=0.0)
    balance_due = fields.Monetary(string='Balance Due ($)', compute='_compute_payment_status', store=True)

    payment_status = fields.Selection([
        ('paid', 'Paid in Full'),
        ('partial', 'Partially Paid'),
        ('pending', 'Pending / Upcoming'),
        ('overdue', 'Overdue'),
    ], string='Payment Status', compute='_compute_payment_status', store=True)

    transaction_id = fields.Many2one('moneta.transaction', string='Linked Bank Entry')
    memo = fields.Char(string='Payment Note / Check #')

    @api.depends('amount_due', 'amount_paid', 'due_date', 'paid_date')
    def _compute_payment_status(self):
        today = fields.Date.today()
        for rec in self:
            due = rec.amount_due or 0.0
            paid = rec.amount_paid or 0.0
            bal = max(due - paid, 0.0)
            rec.balance_due = round(bal, 2)

            if bal <= 1e-4:
                rec.payment_status = 'paid'
            elif paid > 0 and bal > 0:
                rec.payment_status = 'partial'
            elif rec.due_date and today > rec.due_date:
                rec.payment_status = 'overdue'
            else:
                rec.payment_status = 'pending'

    def action_mark_paid(self):
        """1-Click button to record full rent payment as of today."""
        self.ensure_one()
        self.write({
            'amount_paid': self.amount_due,
            'paid_date': fields.Date.today(),
        })


class MonetaPropertyValuation(models.Model):
    _name = 'moneta.property.valuation'
    _description = 'Asset Appraisal & Valuation Log'
    _order = 'valuation_date desc, id desc'

    property_id = fields.Many2one('moneta.property', string='Asset', required=True, ondelete='cascade')
    valuation_date = fields.Date(string='Appraisal Date', default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', related='property_id.user_id', store=True, index=True)
    appraised_value = fields.Monetary(string='Appraised Value', required=True)
    appraiser = fields.Char(string='Appraiser / Source')
    notes = fields.Char(string='Valuation Notes / Market Condition')
