# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MonetaCategory(models.Model):
    _name = 'moneta.category'
    _description = 'Moneta Spending & Income Category'
    _rec_name = 'display_name'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    is_income = fields.Boolean(
        string='Is Income', default=False,
        help='Checked if this category represents an income source (salary, dividends, etc.). Unchecked for expenses.',
    )
    category_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
    ], string='Type', compute='_compute_category_type', inverse='_inverse_category_type', store=True)

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

    @api.depends('is_income')
    def _compute_category_type(self):
        for rec in self:
            rec.category_type = 'income' if rec.is_income else 'expense'

    def _inverse_category_type(self):
        for rec in self:
            is_inc = (rec.category_type == 'income')
            if rec.is_income != is_inc:
                rec.is_income = is_inc

    @api.depends('name', 'parent_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.name:
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'category_type' not in vals:
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
            cat_ids = (cat | cat._get_descendants()).ids
            in_use = Tx.search_count([('category_id', 'in', cat_ids)])
            if in_use:
                raise UserError(
                    f"Category '{cat.name}' is in use by {in_use} transaction(s). "
                    "Reassign or remove those transactions before deleting this category."
                )
        return super().unlink()
