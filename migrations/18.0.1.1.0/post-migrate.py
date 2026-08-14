# -*- coding: utf-8 -*-
"""18.0.1.1.0 post-migration.

Upgrading databases: the Phase 0 categories predate is_system, so flag the
module's own seeded categories (identified by their xmlids) as the protected
template set that per-user seeding copies from -- and restore the income flag
for the default income categories, whose category_type values were dropped by
the field replacement in Phase 1 (only recoverable by xmlid here; fresh
installs get everything from data/default_categories.xml).
"""

_INCOME_CATEGORY_XMLIDS = (
    'cat_salary',
    'cat_freelance',
    'cat_investment_income',
    'cat_other_income',
)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE moneta_category c SET is_system = TRUE
        FROM ir_model_data d
        WHERE d.module = 'moneta_finance' AND d.model = 'moneta.category'
          AND d.res_id = c.id
        """
    )
    cr.execute(
        """
        UPDATE moneta_category c SET is_income = TRUE
        FROM ir_model_data d
        WHERE d.module = 'moneta_finance' AND d.model = 'moneta.category'
          AND d.name IN %s AND d.res_id = c.id
        """,
        (_INCOME_CATEGORY_XMLIDS,),
    )