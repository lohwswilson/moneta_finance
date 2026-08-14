# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaCategory(models.Model):
    _name = 'moneta.category'
    _description = 'Moneta Transaction Category'
    _order = 'parent_id, name'
    # Self-referential parent; child_of/parent_of domain operators resolve
    # through this field.
    _parent_name = 'parent_id'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')

    category_type = fields.Selection([
        ('expense', 'Expense'),
        ('income', 'Income'),
    ], string='Category Type', compute='_compute_category_type', inverse='_inverse_category_type', store=True, default='expense', required=True)

    # Moneta uses a boolean is_income (not an enum type); a transfer has no
    # category at all, so there is no 'transfer' type to carry over.
    is_income = fields.Boolean(string='Is Income', default=False)
    # System categories are protected from deletion (archive instead). The
    # install-time default set is marked is_system=True so it is a stable
    # template for per-user seeding; user copies are is_system=False.
    is_system = fields.Boolean(string='System Category', default=False)

    parent_id = fields.Many2one('moneta.category', string='Parent Category', ondelete='cascade')
    child_ids = fields.One2many('moneta.category', 'parent_id', string='Subcategories')

    # Reverse links used as compute dependencies (budget actuals, dashboards):
    # they let stored computes declare "recompute when a transaction on this
    # category changes" through the relation chain.
    transaction_ids = fields.One2many('moneta.transaction', 'category_id', string='Transactions')
    split_ids = fields.One2many('moneta.transaction.split', 'category_id', string='Split Lines')
    color = fields.Char(string='Color Code', default='#3498db')
    icon = fields.Char(string='Icon/Emoji', default='')

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
            rec.is_income = (rec.category_type == 'income')

    # display_name is a built-in computed field; override its compute to show
    # "Parent / Child" instead of declaring a stored Char that would shadow it.
    @api.depends('name', 'parent_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.name:
                rec.display_name = f"{rec.parent_id.name} / {rec.name or ''}"
            else:
                rec.display_name = rec.name or ''

    # ------------------------------------------------------------------
    # is_income inheritance from parent (faithful to Moneta categories.service:
    # create -> isIncome = parent.isIncome; update -> cascade to descendants).
    # ------------------------------------------------------------------

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        # Convenience in the form: picking a parent flips is_income, category_type, icon and color to match.
        if self.parent_id:
            self.category_type = self.parent_id.category_type
            self.is_income = self.parent_id.is_income
            if not self.icon:
                self.icon = self.parent_id.icon
            if not self.color or self.color == '#3498db':
                self.color = self.parent_id.color

    @api.model_create_multi
    def create(self, vals_list):
        # A child inherits is_income / category_type from its parent; the parent wins over any
        # explicit value supplied alongside it (matches Moneta's create path).
        for vals in vals_list:
            if 'category_type' in vals and 'is_income' not in vals:
                vals['is_income'] = (vals['category_type'] == 'income')
            elif 'is_income' in vals and 'category_type' not in vals:
                vals['category_type'] = 'income' if vals['is_income'] else 'expense'
            parent_id = vals.get('parent_id')
            if parent_id:
                parent = self.browse(parent_id).exists()
                if parent:
                    vals['is_income'] = parent.is_income
                    vals['category_type'] = parent.category_type
                    if not vals.get('icon'):
                        vals['icon'] = parent.icon
                    if not vals.get('color') or vals.get('color') == '#3498db':
                        vals['color'] = parent.color
        return super().create(vals_list)

    def write(self, vals):
        if 'category_type' in vals and 'is_income' not in vals:
            vals['is_income'] = (vals['category_type'] == 'income')
        elif 'is_income' in vals and 'category_type' not in vals:
            vals['category_type'] = 'income' if vals['is_income'] else 'expense'
        # Re-parenting onto a new parent re-inherits is_income / category_type from it.
        if 'parent_id' in vals:
            new_parent_id = vals.get('parent_id')
            if new_parent_id:
                new_parent = self.browse(new_parent_id).exists()
                if new_parent:
                    vals['is_income'] = new_parent.is_income
                    vals['category_type'] = new_parent.category_type
        res = super().write(vals)
        # When is_income changes, cascade to every descendant (Moneta's
        # updateDescendantTypes). super().write on the descendant set avoids
        # re-entering this override and re-cascading.
        if 'is_income' in vals:
            for rec in self:
                descendants = rec._get_descendants()
                if descendants:
                    super(MonetaCategory, descendants).write({
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
            current = current.mapped('child_ids')
        return descendants

    def unlink(self):
        # Rejection before write (the project contract), faithful to Moneta's
        # categories.service.remove: is_system categories are archived (never
        # deleted); a category with subcategories, referencing transactions,
        # split lines, or scheduled transactions must be reassigned/cleared
        # first. Without these guards parent_id ondelete='cascade' would delete
        # subcategories, category_id ondelete='set null' would silently detach
        # referencing transactions/scheduled rows, and split.category_id's
        # ondelete='restrict' would surface a raw DB IntegrityError instead of a
        # user-facing message.
        Transaction = self.env['moneta.transaction']
        Split = self.env['moneta.transaction.split']
        Recurring = self.env['moneta.recurring.transaction']
        for rec in self:
            if rec.is_system:
                raise ValidationError(
                    "System categories cannot be deleted; archive them instead."
                )
            if rec.child_ids:
                raise ValidationError(
                    "Cannot delete category with subcategories. "
                    "Delete or reassign subcategories first."
                )
            tx_count = Transaction.search_count([('category_id', '=', rec.id)])
            if tx_count:
                raise ValidationError(
                    f"Cannot delete category with {tx_count} referencing "
                    "transaction(s). Reassign transactions first."
                )
            split_count = Split.search_count([('category_id', '=', rec.id)])
            if split_count:
                raise ValidationError(
                    f"Cannot delete category with {split_count} referencing "
                    "split line(s). Reassign transactions first."
                )
            scheduled = Recurring.search_count([('category_id', '=', rec.id)])
            if scheduled:
                raise ValidationError(
                    f"Cannot delete category with {scheduled} scheduled "
                    "transaction(s). Reassign them first."
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Per-user default category seeding
    # ------------------------------------------------------------------

    @api.model
    def _seed_user_defaults(self, user):
        """Idempotently seed the default category tree for a user.

        Copies the install-time system template set (data/default_categories.xml,
        owned by whoever installed the module -- typically the SUPERUSER, not
        the admin login) into per-user, deletable (is_system=False) copies owned
        by ``user``. Skips when the user already owns any category. Runs under
        sudo so record rules cannot hide the templates; the user_id is set
        explicitly on every copy so ownership is correct.
        """
        if not user or not user.id:
            return
        Category = self.env['moneta.category']
        if Category.search_count([('user_id', '=', user.id)]):
            return
        # Templates: top-level system categories. Owner is deliberately not
        # filtered -- user copies are is_system=False, so is_system=True rows
        # are exactly the install-time template set.
        templates = Category.sudo().search([
            ('is_system', '=', True),
            ('parent_id', '=', False),
        ], order='id')
        if not templates:
            return
        parent_map = {}  # template id -> new copy id

        def copy_tree(template_records):
            for tmpl in template_records:
                copy = Category.sudo().create({
                    'name': tmpl.name,
                    'description': tmpl.description,
                    'is_income': tmpl.is_income,
                    'category_type': tmpl.category_type or ('income' if tmpl.is_income else 'expense'),
                    'is_system': False,  # user copies are deletable
                    'icon': tmpl.icon,
                    'color': tmpl.color,
                    'parent_id': parent_map.get(tmpl.parent_id.id, False),
                    'user_id': user.id,
                })
                parent_map[tmpl.id] = copy.id
                children = Category.sudo().search([
                    ('parent_id', '=', tmpl.id),
                    ('is_system', '=', True),
                ], order='id')
                if children:
                    copy_tree(children)

        copy_tree(templates)
