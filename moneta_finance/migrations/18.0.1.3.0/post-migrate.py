# -*- coding: utf-8 -*-
"""18.0.1.3.0 post-migration.

Backfill the monthly balance snapshots for every existing account so the
net-worth graph has data immediately after the upgrade (the rebuild-on-write
triggers only fire on new writes; the daily cron would eventually cover it).
"""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    monthly = env['moneta.account.balance.monthly'].sudo()
    for account in env['moneta.account'].sudo().search([]):
        monthly._rebuild_for_account(account)