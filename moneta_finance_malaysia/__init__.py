# -*- coding: utf-8 -*-
from . import models


def _pre_init_transfer_malaysia_data(env):
    """Transfer XML ID ownership of Malaysia master data from moneta_finance to moneta_finance_malaysia."""
    env.cr.execute("""
        UPDATE ir_model_data
        SET module = 'moneta_finance_malaysia'
        WHERE module = 'moneta_finance'
          AND (name LIKE 'inst_my_%' OR name LIKE 'payee_my_%')
    """)
