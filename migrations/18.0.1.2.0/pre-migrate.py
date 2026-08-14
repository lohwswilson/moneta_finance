# -*- coding: utf-8 -*-
"""18.0.1.2.0 pre-migration.

Phase 2 restructured moneta.holding: the total cost_basis column was replaced
by the per-unit average_cost (derived from investment transactions). Convert
existing rows before Odoo drops the old column so pre-Phase-2 holdings keep
their cost data: average_cost = cost_basis / quantity.
"""


def migrate(cr, version):
    cr.execute("SELECT to_regclass('public.moneta_holding')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'moneta_holding' AND column_name = 'cost_basis'"
    )
    if not cr.fetchone():
        return
    cr.execute(
        "ALTER TABLE moneta_holding ADD COLUMN IF NOT EXISTS average_cost numeric"
    )
    cr.execute(
        "UPDATE moneta_holding SET average_cost = ROUND(cost_basis / quantity, 8) "
        "WHERE quantity > 0 AND cost_basis IS NOT NULL"
    )