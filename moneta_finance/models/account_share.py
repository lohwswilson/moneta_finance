# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaAccountShare(models.Model):
    _name = 'moneta.account.share'
    _description = 'Moneta Account Sharing & Joint Access Grant'
    _order = 'account_id, user_id'

    account_id = fields.Many2one(
        'moneta.account', string='Account', required=True, ondelete='cascade'
    )
    owner_id = fields.Many2one(
        'res.users', related='account_id.user_id', string='Account Owner', store=True, readonly=True
    )
    user_id = fields.Many2one(
        'res.users', string='Shared With User', required=True, index=True
    )
    permission = fields.Selection([
        ('read', 'Read-Only'),
        ('write', 'Read / Write (Can record transactions)'),
    ], string='Permission Level', default='read', required=True)

    is_joint = fields.Boolean(
        string='Joint Account', default=True,
        help='When enabled, account appears directly in grantee register and net worth.',
    )
    exclude_from_net_worth = fields.Boolean(
        string='Exclude From Grantee Net Worth', default=False,
        help='Grantee-specific preference to exclude this shared balance from their net worth calculations.',
    )

    _sql_constraints = [
        ('account_user_uniq', 'unique(account_id, user_id)', 'This account is already shared with this user!'),
    ]

    @api.constrains('account_id', 'user_id')
    def _check_not_self_share(self):
        for rec in self:
            if rec.account_id.user_id == rec.user_id:
                raise ValidationError('You cannot share an account with yourself (the owner).')
