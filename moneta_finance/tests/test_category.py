# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestCategory(MonetaTestBase):

    def test_child_inherits_is_income_from_parent(self):
        parent = self.env['moneta.category'].create({'name': 'Inc Parent', 'is_income': True})
        child = self.env['moneta.category'].create({'name': 'Inc Child', 'parent_id': parent.id})
        self.assertTrue(child.is_income, "child must inherit is_income from parent on create")
        expense_parent = self.env['moneta.category'].create({'name': 'Exp Parent', 'is_income': False})
        expense_child = self.env['moneta.category'].create({
            'name': 'Exp Child', 'parent_id': expense_parent.id, 'is_income': True,
        })
        # Parent wins over an explicit value supplied alongside it.
        self.assertFalse(expense_child.is_income)

    def test_is_income_cascades_to_descendants(self):
        root = self.env['moneta.category'].create({'name': 'Root', 'is_income': False})
        child = self.env['moneta.category'].create({'name': 'Child', 'parent_id': root.id})
        grandchild = self.env['moneta.category'].create({'name': 'GC', 'parent_id': child.id})
        root.write({'is_income': True})
        # Re-browse to avoid any stale cache from the create path.
        self.assertTrue(self.env['moneta.category'].browse(child.id).is_income)
        self.assertTrue(self.env['moneta.category'].browse(grandchild.id).is_income)

    def test_reparent_inherits_is_income_from_new_parent(self):
        expense = self.env['moneta.category'].create({'name': 'Exp', 'is_income': False})
        income = self.env['moneta.category'].create({'name': 'Inc', 'is_income': True})
        moving = self.env['moneta.category'].create({'name': 'Mover', 'parent_id': expense.id})
        self.assertFalse(moving.is_income)
        moving.write({'parent_id': income.id})
        self.assertTrue(self.env['moneta.category'].browse(moving.id).is_income)

    def test_is_system_protected_from_unlink(self):
        sys_cat = self.env['moneta.category'].create({'name': 'System Cat', 'is_system': True})
        with self.assertRaises(ValidationError):
            sys_cat.unlink()
        # A non-system category deletes normally.
        plain = self.env['moneta.category'].create({'name': 'Plain', 'is_system': False})
        plain.unlink()
        self.assertFalse(plain.exists())

    def test_seed_user_defaults_copies_templates_idempotently(self):
        # Templates are the install-time is_system set; ownership varies
        # (SUPERUSER on a CLI install, not the admin login), so no owner filter.
        template_count = self.env['moneta.category'].sudo().search_count([
            ('is_system', '=', True),
        ])
        self.assertGreater(template_count, 0, "install must seed the system template categories")
        user = self._make_user('Seeder', 'seeder')
        # _make_user uses moneta_no_seed, so the user starts empty.
        self.assertEqual(
            self.env['moneta.category'].search_count([('user_id', '=', user.id)]), 0
        )
        self.env['moneta.category'].sudo()._seed_user_defaults(user)
        seeded = self.env['moneta.category'].search_count([('user_id', '=', user.id)])
        self.assertEqual(seeded, template_count, "user gets one copy per template")
        # All seeded copies are deletable (is_system=False) and owned by the user.
        self.env['moneta.category'].sudo()._seed_user_defaults(user)
        self.assertEqual(
            self.env['moneta.category'].search_count([('user_id', '=', user.id)]), seeded
        )

    def test_category_icon_and_color_inheritance(self):
        parent = self.env['moneta.category'].create({
            'name': 'Food & Dining',
            'icon': '🍔',
            'color': '#FF5733',
        })
        child = self.env['moneta.category'].create({
            'name': 'Groceries',
            'parent_id': parent.id,
            'icon': '📁',
            'color': '#4A90E2',
        })
        # Child inherits icon and color from parent when unset/default
        self.assertEqual(child.effective_icon, '🍔')
        self.assertEqual(child.effective_color, '#FF5733')

        # If child sets its own custom icon/color, it overrides parent
        child.write({'icon': '🥦', 'color': '#28A745'})
        self.assertEqual(child.effective_icon, '🥦')
        self.assertEqual(child.effective_color, '#28A745')