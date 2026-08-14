# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND


class MonetaCategory(models.Model):
    _name = 'moneta.category'
    _description = 'Moneta Spending & Income Category'
    _rec_name = 'display_name'
    _order = 'is_transfer asc, name asc'

    name = fields.Char(string='Category Name', required=True, index=True)
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True, index=True
    )
    icon = fields.Char(string='Icon', default='📁', help='Emoji icon (e.g. 📁, 🔁, 🍔, 🏠, 🚗, 💰)')
    color = fields.Char(string='Color', default='#4A90E2')
    description = fields.Text(string='Description / Notes')
    is_system = fields.Boolean(string='System Default Template', default=False)

    is_income = fields.Boolean(
        string='Is Income', default=False,
        help='Checked if this category represents an income source (salary, dividends, etc.). Unchecked for expenses.',
    )
    category_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Account Transfer'),
    ], string='Type', compute='_compute_category_type', inverse='_inverse_category_type', store=True)

    transfer_account_id = fields.Many2one(
        'moneta.account', string='Linked Transfer Account',
        ondelete='cascade', index=True,
        help='If set, selecting this category will automatically treat the transaction as a transfer to/from this account.'
    )
    is_transfer = fields.Boolean(
        string='Is Transfer', compute='_compute_is_transfer', store=True, index=True
    )

    parent_id = fields.Many2one(
        'moneta.category', string='Parent Category',
        ondelete='cascade', index=True,
    )
    child_ids = fields.One2many(
        'moneta.category', 'parent_id', string='Subcategories',
    )
    transaction_ids = fields.One2many(
        'moneta.transaction', 'category_id', string='Transactions',
    )
    split_ids = fields.One2many(
        'moneta.transaction.split', 'category_id', string='Transaction Splits',
    )

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    transaction_count = fields.Integer(string='Transactions Count', compute='_compute_transaction_stats')
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id', compute='_compute_transaction_stats')

    def _compute_transaction_stats(self):
        for rec in self:
            rec_id = rec._origin.id if hasattr(rec, '_origin') and rec._origin.id else rec.id
            if not rec_id or not isinstance(rec_id, int):
                rec.transaction_count = 0
                rec.total_amount = 0.0
                continue
            cat_ids = self.search([('id', 'child_of', rec_id)]).ids
            txs = self.env['moneta.transaction'].search([('category_id', 'in', cat_ids), ('state', '!=', 'void')])
            rec.transaction_count = len(txs)
            rec.total_amount = sum(txs.mapped('amount'))

    def action_view_transactions(self):
        self.ensure_one()
        cat_ids = self.search([('id', 'child_of', self.id)]).ids
        return {
            'name': f'Transactions - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.transaction',
            'view_mode': 'list,form',
            'domain': [('category_id', 'in', cat_ids)],
            'context': {'default_category_id': self.id},
        }

    @api.depends('transfer_account_id')
    def _compute_is_transfer(self):
        for rec in self:
            rec.is_transfer = bool(rec.transfer_account_id)

    @api.depends('is_income', 'is_transfer', 'transfer_account_id')
    def _compute_category_type(self):
        for rec in self:
            if rec.transfer_account_id or rec.is_transfer:
                rec.category_type = 'transfer'
            else:
                rec.category_type = 'income' if rec.is_income else 'expense'

    def _inverse_category_type(self):
        for rec in self:
            if rec.category_type == 'transfer':
                rec.is_income = False
            else:
                is_inc = (rec.category_type == 'income')
                if rec.is_income != is_inc:
                    rec.is_income = is_inc

    @api.depends('name', 'icon', 'parent_id.name', 'transfer_account_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.transfer_account_id:
                rec.display_name = f"[{rec.transfer_account_id.name}]"
            elif rec.parent_id and rec.parent_id.name:
                rec.display_name = f"{rec.parent_id.name} / {rec.name or ''}"
            else:
                rec.display_name = rec.name or ''

    _sql_constraints = [
        ('unique_user_parent_name', 'unique(user_id, parent_id, name)',
         'A category with this name already exists under the same parent for this user.'),
    ]

    @api.constrains('parent_id')
    def _check_recursion(self):
        if not self._check_recursion_parent():
            raise ValidationError("A category cannot be its own ancestor.")

    def _check_recursion_parent(self):
        seen = set()
        for rec in self:
            current = rec.parent_id
            while current:
                if current.id == rec.id or current.id in seen:
                    return False
                seen.add(current.id)
                current = current.parent_id
        return True

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = list(domain or [])
        if name:
            search_domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('display_name', operator, name),
                ('parent_id.name', operator, name),
                ('transfer_account_id.name', operator, name),
            ]
            domain = AND([domain, search_domain])
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        if name:
            name_domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('display_name', operator, name),
                ('parent_id.name', operator, name),
                ('transfer_account_id.name', operator, name),
            ]
            records = self.search(name_domain + args, limit=limit)
        else:
            records = self.search(args, limit=limit)
        return [(r.id, r.display_name) for r in records]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('transfer_account_id'):
                vals['category_type'] = 'transfer'
                vals['is_income'] = False
                if not vals.get('icon'):
                    vals['icon'] = '🔁'
            elif 'category_type' not in vals:
                vals['category_type'] = 'income' if vals.get('is_income') else 'expense'
            parent_id = vals.get('parent_id')
            if parent_id:
                parent = self.browse(parent_id).exists()
                if parent:
                    vals['is_income'] = parent.is_income
                    vals['category_type'] = 'income' if parent.is_income else 'expense'
        return super().create(vals_list)

    def write(self, vals):
        if 'parent_id' in vals:
            new_parent_id = vals.get('parent_id')
            if new_parent_id:
                new_parent = self.browse(new_parent_id).exists()
                if new_parent:
                    vals['is_income'] = new_parent.is_income
                    vals['category_type'] = 'income' if new_parent.is_income else 'expense'
        res = super().write(vals)
        if 'is_income' in vals and not self.env.context.get('skip_cascade'):
            for rec in self:
                descendants = rec._get_descendants()
                if descendants:
                    descendants.with_context(skip_cascade=True).write({
                        'is_income': vals['is_income'],
                        'category_type': 'income' if vals['is_income'] else 'expense',
                    })
        return res

    def _get_descendants(self):
        """All descendants (children, grandchildren, ...) of self, recursively."""
        descendants = self.env['moneta.category']
        current = self.child_ids
        while current:
            descendants |= current
            current = current.mapped('child_ids') - descendants
        return descendants

    def unlink(self):
        Tx = self.env['moneta.transaction']
        for cat in self:
            if cat.is_system:
                raise ValidationError(
                    f"Category '{cat.name}' is a system category and cannot be deleted."
                )
            if cat.child_ids:
                raise ValidationError(
                    f"Category '{cat.name}' has {len(cat.child_ids)} subcategor(ies). "
                    "Delete or reassign them before deleting this category."
                )
            cat_ids = (cat | cat._get_descendants()).ids
            in_use = Tx.search_count([('category_id', 'in', cat_ids)])
            if in_use:
                raise ValidationError(
                    f"Category '{cat.name}' is in use by {in_use} transaction(s). "
                    "Reassign or remove those transactions before deleting this category."
                )
            split_use = self.env['moneta.transaction.split'].search_count(
                [('category_id', 'in', cat_ids)]
            )
            if split_use:
                raise ValidationError(
                    f"Category '{cat.name}' is used by {split_use} split line(s). "
                    "Reassign or remove those split lines before deleting this category."
                )
            recurring_use = self.env['moneta.recurring.transaction'].search_count(
                [('category_id', 'in', cat_ids)]
            )
            if recurring_use:
                raise ValidationError(
                    f"Category '{cat.name}' is used by {recurring_use} scheduled "
                    "transaction(s). Reassign or remove them before deleting this category."
                )
        return super().unlink()

    @api.model
    def _seed_user_defaults(self, user):
        """Seed a standard set of categories for a new user if none exist.

        Copies the install-time is_system template set (one copy per template,
        preserving the parent/child structure) so every user starts from the
        same tree. Templates are owned by the installer (SUPERUSER on a CLI
        install), so the template search is not filtered by owner; the copies
        themselves are owned by ``user`` and are not system categories.
        """
        if self.search_count([('user_id', '=', user.id), ('is_transfer', '=', False)]) > 0:
            return
        templates = self.search([('is_system', '=', True)], order='id asc')
        parent_map = {}
        for tpl in templates:
            vals = {
                'name': tpl.name,
                'icon': tpl.icon,
                'color': tpl.color,
                'is_income': tpl.is_income,
                'user_id': user.id,
            }
            if tpl.parent_id:
                parent_id = parent_map.get(tpl.parent_id.id)
                if parent_id:
                    vals['parent_id'] = parent_id
            copy = self.create(vals)
            parent_map[tpl.id] = copy.id
