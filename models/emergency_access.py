# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaEmergencyContact(models.Model):
    _name = 'moneta.emergency.contact'
    _description = 'Moneta Emergency Access Contact (Digital Estate)'
    _order = 'name asc'

    name = fields.Char(string='Contact Name', required=True)
    email = fields.Char(string='Email Address', required=True)
    phone = fields.Char(string='Phone Number')
    relationship = fields.Selection([
        ('spouse', 'Spouse / Partner'),
        ('child', 'Child / Dependent'),
        ('parent', 'Parent / Guardian'),
        ('attorney', 'Attorney / Legal Counsel'),
        ('executor', 'Estate Executor'),
        ('advisor', 'Financial Advisor / Trustee'),
        ('other', 'Other Trusted Contact'),
    ], string='Relationship', required=True, default='spouse')

    user_id = fields.Many2one('res.users', string='Account Owner', default=lambda self: self.env.user, required=True, index=True)

    waiting_period_days = fields.Integer(
        string='Security Waiting Period (Days)', default=30, required=True,
        help='The number of days the account owner has to decline an emergency claim before access is granted.',
    )

    status = fields.Selection([
        ('active', 'Designated (Standby)'),
        ('pending_claim', 'Access Claimed (Pending Period)'),
        ('approved', 'Emergency Access Granted'),
        ('revoked', 'Revoked'),
    ], string='Status', default='active', required=True)

    claim_request_date = fields.Datetime(string='Claim Requested On', readonly=True)
    access_granted_date = fields.Datetime(string='Access Granted On', readonly=True)

    notes = fields.Text(
        string='Estate & Vault Notes / Instructions',
        help='Secure notes for this contact regarding wills, physical keys, or institution details.',
    )

    def action_initiate_claim(self):
        self.ensure_one()
        self.write({
            'status': 'pending_claim',
            'claim_request_date': fields.Datetime.now(),
        })

    def action_approve_access(self):
        self.ensure_one()
        self.write({
            'status': 'approved',
            'access_granted_date': fields.Datetime.now(),
        })

    def action_revoke_access(self):
        self.ensure_one()
        self.write({
            'status': 'revoked',
        })
