# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MonetaProperty(models.Model):
    """Real estate, vehicles, antiques, jewelry, and tangible physical asset tracking."""
    _name = 'moneta.property'
    _description = 'Property & Physical Asset'
    _order = 'current_market_value desc, name asc'

    name = fields.Char(string='Asset / Property Name', required=True)
    asset_category = fields.Selection([
        ('real_estate', 'Real Estate / Property'),
        ('vehicle', 'Automobile / Vehicle'),
        ('jewelry', 'Luxury Watch & Fine Jewelry'),
        ('antiques', 'Antiques & Fine Art / Collectibles'),
        ('other', 'Other Tangible Asset'),
    ], string='Category', default='real_estate', required=True)

    property_type = fields.Selection([
        ('primary_residence', 'Primary Residence'),
        ('vacation_home', 'Vacation / Secondary Home'),
        ('rental_property', 'Rental / Investment Property'),
        ('commercial', 'Commercial Real Estate'),
        ('land', 'Land / Plot'),
        ('automobile', 'Car / Automobile'),
        ('motorcycle', 'Motorcycle / Powersport'),
        ('luxury_watch', 'Luxury Watch'),
        ('fine_jewelry', 'Fine Jewelry & Precious Metals'),
        ('antique_furniture', 'Antique Furniture / Decor'),
        ('fine_art', 'Fine Art & Paintings'),
        ('collectible', 'Rare Collectibles'),
        ('other', 'Other Asset'),
    ], string='Asset Sub-Type', default='primary_residence', required=True)

    user_id = fields.Many2one(
        'res.users', string='Owner', required=True,
        default=lambda self: self.env.user,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id
    )

    purchase_date = fields.Date(string='Purchase Date')
    purchase_price = fields.Monetary(string='Purchase Price', currency_field='currency_id')
    current_market_value = fields.Monetary(string='Current Market Value', currency_field='currency_id', required=True)

    # Mortgage / Debt linkage
    mortgage_account_id = fields.Many2one(
        'moneta.account', string='Mortgage / Debt Account',
        domain="[('account_type', 'in', ('mortgage', 'loan'))]",
        help='Linked liability account tracking the remaining mortgage debt balance.'
    )
    mortgage_balance = fields.Monetary(
        string='Mortgage Debt', currency_field='currency_id',
        compute='_compute_equity', store=True,
        help='Current debt balance on the linked mortgage account (or 0 if fully paid).'
    )
    equity_value = fields.Monetary(
        string='Net Home / Asset Equity', currency_field='currency_id',
        compute='_compute_equity', store=True,
        help='Current market value minus remaining mortgage debt.'
    )
    loan_to_value_ratio = fields.Float(
        string='LTV %', compute='_compute_equity', store=True,
        help='Loan to Value ratio: (Mortgage Debt / Market Value) * 100.'
    )

    color = fields.Integer(string='Color Index')
    notes = fields.Text(string='Notes & Property Specs')
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(string='Asset Photo', max_width=1920, max_height=1920)

    # Vehicle specific
    vehicle_make = fields.Char(string='Make / Manufacturer')
    vehicle_model = fields.Char(string='Model')
    vehicle_year = fields.Integer(string='Model Year')
    vehicle_vin = fields.Char(string='VIN / Chassis #')
    vehicle_license_plate = fields.Char(string='License Plate')
    vehicle_mileage = fields.Integer(string='Current Mileage (km/mi)')

    # Antique / Valuables specific
    antique_era = fields.Char(string='Period / Era / Year of Origin')
    maker_artist = fields.Char(string='Maker / Artist / Brand')
    condition_grade = fields.Selection([
        ('mint', 'Mint / Unworn'),
        ('near_mint', 'Near Mint'),
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good / Restored'),
        ('fair', 'Fair / Antique Patina'),
    ], string='Condition Grade', default='excellent')
    authenticity_cert_number = fields.Char(string='Certificate / Serial #')
    storage_location = fields.Char(string='Storage / Safe Location')
    insured_value = fields.Monetary(string='Insured Value', currency_field='currency_id')
    insurance_policy_number = fields.Char(string='Insurance Policy #')

    valuation_line_ids = fields.One2many('moneta.property.valuation', 'property_id', string='Valuation History')

    @api.depends('current_market_value', 'mortgage_account_id', 'mortgage_account_id.current_balance')
    def _compute_equity(self):
        for prop in self:
            debt = 0.0
            if prop.mortgage_account_id:
                debt = abs(float(prop.mortgage_account_id.current_balance or 0.0))
            prop.mortgage_balance = debt
            mkt = float(prop.current_market_value or 0.0)
            prop.equity_value = max(mkt - debt, 0.0)
            prop.loan_to_value_ratio = round((debt / mkt * 100.0) if mkt > 0 else 0.0, 1)


class MonetaPropertyValuation(models.Model):
    """Historical appraisal log for real estate, cars, and antiques."""
    _name = 'moneta.property.valuation'
    _description = 'Property Valuation Entry'
    _order = 'valuation_date desc'

    property_id = fields.Many2one('moneta.property', string='Asset', required=True, ondelete='cascade')
    valuation_date = fields.Date(string='Valuation Date', required=True, default=fields.Date.context_today)
    appraised_value = fields.Monetary(string='Appraised Value', required=True)
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id', store=True)
    appraiser = fields.Char(string='Appraiser / Source')
    notes = fields.Char(string='Appraisal Notes')
