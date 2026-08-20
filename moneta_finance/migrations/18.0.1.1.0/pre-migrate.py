# -*- coding: utf-8 -*-
"""18.0.1.1.0 pre-migration.

Phase 1 replaced the skeleton's category_type enum ('income'/'expense'/'transfer')
with the is_income boolean. For databases upgrading from 18.0.1.0.0, convert the
existing rows BEFORE Odoo's schema sync drops the old column, so the
income/expense split survives. Fresh installs have no table yet at this point
and skip the whole block (pre_init_hook covers them).

Note: pre/post_init hooks only run on fresh installs in Odoo 18 -- versioned
migration scripts are the upgrade path.
"""


def migrate(cr, version):
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