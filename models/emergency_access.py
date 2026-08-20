# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


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
        string='Security Waiting Period (Days)', default=14, required=True,
        help='The number of days the account owner has to decline an emergency claim before access is granted (e.g. 7, 14, or 30 days).',
    )

    status = fields.Selection([
        ('active', 'Designated (Standby)'),
        ('pending_claim', 'Access Claimed (Pending Period)'),
        ('approved', 'Emergency Access Granted'),
        ('declined', 'Claim Declined by Owner'),
        ('revoked', 'Revoked'),
    ], string='Status', default='active', required=True)

    claim_request_date = fields.Datetime(string='Claim Requested On', readonly=True)
    unlock_date = fields.Datetime(string='Unlock Date', compute='_compute_unlock_date', store=True)
    days_remaining = fields.Integer(string='Days Remaining', compute='_compute_days_remaining')
    access_granted_date = fields.Datetime(string='Access Granted On', readonly=True)

    notes = fields.Text(
        string='Estate & Vault Notes / Instructions',
        help='Secure notes for this contact regarding wills, physical keys, or institution details.',
    )

    @api.depends('claim_request_date', 'waiting_period_days', 'status')
    def _compute_unlock_date(self):
        for rec in self:
            if rec.status == 'pending_claim' and rec.claim_request_date:
                rec.unlock_date = rec.claim_request_date + timedelta(days=rec.waiting_period_days or 14)
            else:
                rec.unlock_date = False

    @api.depends('unlock_date', 'status')
    def _compute_days_remaining(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.status == 'pending_claim' and rec.unlock_date:
                diff = rec.unlock_date - now
                rec.days_remaining = max(diff.days, 0)
            else:
                rec.days_remaining = 0

    def action_initiate_claim(self):
        """Initiates the time-delayed emergency access claim and starts the grace period."""
        self.ensure_one()
        now = fields.Datetime.now()
        self.write({
            'status': 'pending_claim',
            'claim_request_date': now,
        })
        # Notify owner immediately
        self._notify_owner_of_claim()

    def action_decline_claim(self):
        """Account owner declines an unauthorized or accidental emergency claim."""
        self.ensure_one()
        self.write({
            'status': 'declined',
            'claim_request_date': False,
        })

    def action_approve_access(self):
        """Grants emergency read-only access to all accounts owned by the user."""
        self.ensure_one()
        now = fields.Datetime.now()
        self.write({
            'status': 'approved',
            'access_granted_date': now,
        })
        self._provision_read_only_access()

    def action_revoke_access(self):
        """Revokes emergency access and detaches permissions."""
        self.ensure_one()
        self.write({
            'status': 'revoked',
        })
        self._deprovision_access()

    def _notify_owner_of_claim(self):
        """Send urgent notification to the account owner about the pending claim."""
        for rec in self:
            owner = rec.user_id
            subject = f"⚠️ URGENT: Emergency Access Claimed by {rec.name}"
            body = (
                f"<p>An emergency access claim has been initiated for your Moneta Finance vault by <strong>{rec.name}</strong> ({rec.email}).</p>"
                f"<p>You have <strong>{rec.waiting_period_days} days</strong> (until {rec.unlock_date or 'the waiting period expires'}) to review and decline this request.</p>"
                f"<p>If this is unauthorized, please log in to Moneta Finance and click <strong>Decline Claim</strong>.</p>"
            )
            owner.partner_id.message_post(
                subject=subject,
                body=body,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

    def _provision_read_only_access(self):
        """Provisions read-only account sharing for the emergency contact user if registered."""
        for rec in self:
            contact_user = self.env['res.users'].search([('email', '=ilike', rec.email.strip())], limit=1)
            if contact_user:
                accounts = self.env['moneta.account'].search([('user_id', '=', rec.user_id.id)])
                for acc in accounts:
                    existing = self.env['moneta.account.share'].search([
                        ('account_id', '=', acc.id),
                        ('shared_with_user_id', '=', contact_user.id),
                    ], limit=1)
                    if existing:
                        existing.write({'permission': 'read'})
                    else:
                        self.env['moneta.account.share'].create({
                            'account_id': acc.id,
                            'shared_with_user_id': contact_user.id,
                            'permission': 'read',
                        })

    def _deprovision_access(self):
        """Removes shared account access when emergency access is revoked."""
        for rec in self:
            contact_user = self.env['res.users'].search([('email', '=ilike', rec.email.strip())], limit=1)
            if contact_user:
                shares = self.env['moneta.account.share'].search([
                    ('account_id.user_id', '=', rec.user_id.id),
                    ('shared_with_user_id', '=', contact_user.id),
                ])
                shares.unlink()

    @api.model
    def _cron_check_emergency_access(self):
        """Daily Cron: checks pending emergency claims and unlocks expired waiting periods."""
        now = fields.Datetime.now()
        pending = self.search([('status', '=', 'pending_claim')])
        for rec in pending:
            if not rec.claim_request_date:
                continue
            unlock_time = rec.claim_request_date + timedelta(days=rec.waiting_period_days or 14)
            if now >= unlock_time:
                # Waiting period has expired without owner decline: grant access!
                rec.action_approve_access()
            else:
                # Still pending: send daily reminder warning to owner
                rec._notify_owner_of_claim()

