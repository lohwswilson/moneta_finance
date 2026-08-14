# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaProperty(models.Model):
    _name = 'moneta.property'
    _description = 'Moneta Real Estate, Vehicles, Antiques & Tangible Assets'
    _order = 'asset_category asc, name asc'

    name = fields.Char(string='Asset / Item Name', required=True, placeholder='e.g. 1967 Shelby GT500 or 19th Century Antique Clock')
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
    vehicle_make = fields.Char(string='Make / Manufacturer', placeholder='e.g. Porsche, Tesla, BMW')
    vehicle_model = fields.Char(string='Model', placeholder='e.g. 911 Carrera, Model S')
    vehicle_year = fields.Integer(string='Model Year', default=2024)
    vehicle_vin = fields.Char(string='VIN / Chassis #')
    vehicle_license_plate = fields.Char(string='License Plate')
    vehicle_mileage = fields.Integer(string='Current Mileage (Odometer)')
    annual_depreciation_rate = fields.Float(string='Annual Depreciation Rate (%)', default=15.0, digits=(5, 2))

    # --- Antiques, Collectibles & Valuables Fields ---
    antique_era = fields.Char(string='Period / Era / Year Made', placeholder='e.g. Victorian 1880, Art Deco, Ming Dynasty')
    maker_artist = fields.Char(string='Artist / Maker / Brand', placeholder='e.g. Rolex, Cartier, Monet, Gibson')
    condition_grade = fields.Selection([
        ('mint', 'Mint / Brand New'),
        ('near_mint', 'Near Mint / Like New'),
        ('excellent', 'Excellent / Restored'),
        ('good', 'Good / Original Patina'),
        ('fair', 'Fair / Needs Restoration'),
    ], string='Condition Grade', default='excellent')
    authenticity_cert_number = fields.Char(string='Certificate of Authenticity # / Serial #')
    storage_location = fields.Char(string='Storage Location / Safe Box', placeholder='e.g. Home Safe, Vault #42, Climate-Controlled Storage')
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


class MonetaPropertyValuation(models.Model):
    _name = 'moneta.property.valuation'
    _description = 'Asset Appraisal & Valuation Log'
    _order = 'valuation_date desc, id desc'

    property_id = fields.Many2one('moneta.property', string='Asset', required=True, ondelete='cascade')
    valuation_date = fields.Date(string='Appraisal Date', default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id', readonly=True)
    appraised_value = fields.Monetary(string='Appraised Value', required=True)
    appraiser = fields.Char(string='Appraiser / Source', placeholder='e.g. Kelley Blue Book, Sotheby\'s, Christie\'s, Zillow')
    notes = fields.Char(string='Valuation Notes / Market Condition')
