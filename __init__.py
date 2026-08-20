# -*- coding: utf-8 -*-
import logging
from . import models
from . import wizards
from . import controllers

_logger = logging.getLogger(__name__)


def _pre_init_migrate_category_type(env):
    """Fresh-install path: the skeleton's categories used a category_type enum
    ('income'/'expense'/'transfer'); Phase 1 replaced it with the is_income
    boolean. On a fresh install the table does not exist yet at this point, so
    the whole block is a no-op -- the conversion is real work only for
    databases upgrading from a pre-Phase-1 build, which run the versioned
    migration scripts instead (migrations/18.0.1.1.0). Odoo 18 calls hooks
    with the environment, not a cursor."""
    cr = env.cr
    cr.execute("SELECT to_regclass('public.moneta_category')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'moneta_category' AND column_name = 'category_type'"
    )
    if not cr.fetchone():
        return
    cr.execute(
        "ALTER TABLE moneta_category ADD COLUMN IF NOT EXISTS is_income boolean DEFAULT false"
    )
    cr.execute("UPDATE moneta_category SET is_income = TRUE WHERE category_type = 'income'")
    cr.execute("ALTER TABLE moneta_category DROP COLUMN IF EXISTS category_type")


def _post_init_seed_defaults(env):
    """After install, seed default categories for every user who is a Moneta
    user but owns none yet (idempotent). Covers DBs that already had Moneta
    users before this hook existed; fresh installs rely on the res.users hook
    for users created later. Seeding failures are logged, not raised, so a
    bad seed never blocks module install. Odoo 18 calls hooks with the
    environment, not a cursor."""
    user_group = env.ref('moneta_finance.group_moneta_user', raise_if_not_found=False)
    if not user_group:
        return
    # Upgrade path: the Phase 0 categories predate is_system, so flag the
    # module's own seeded categories (identified by their xmlids in
    # ir.model.data) as the protected template set. Fresh installs already got
    # is_system=True from data/default_categories.xml -- this is a no-op there.
    template_ids = env['ir.model.data'].search([
        ('module', '=', 'moneta_finance'),
        ('model', '=', 'moneta.category'),
    ]).mapped('res_id')
    if template_ids:
        env['moneta.category'].browse(template_ids).write({'is_system': True})
    Category = env['moneta.category'].sudo()
    for user in user_group.users:
        try:
            Category._seed_user_defaults(user)
        except Exception as exc:  # noqa: BLE001 - install must not abort on a seed error
            _logger.exception("post_init: failed seeding categories for user %s: %s", user.id, exc)

    # Backfill missing icons/colors on existing subcategories from their parents
    try:
        empty_icon_categories = Category.search([('icon', 'in', (False, '')), ('parent_id', '!=', False)])
        for cat in empty_icon_categories:
            if cat.parent_id.icon:
                cat.write({'icon': cat.parent_id.icon, 'color': cat.parent_id.color or '#3498db'})
    except Exception as exc:
        _logger.exception("post_init: failed backfilling category icons: %s", exc)