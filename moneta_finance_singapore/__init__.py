# -*- coding: utf-8 -*-
from . import models


def _pre_init_transfer_singapore_data(env):
    """Transfer XML ID ownership of Singapore master data from moneta_finance to moneta_finance_singapore."""
    env.cr.execute("""
        UPDATE ir_model_data
        SET module = 'moneta_finance_singapore'
        WHERE module = 'moneta_finance'
          AND (
              name IN (
                  'inst_dbs_posb', 'inst_ocbc', 'inst_uob', 'inst_sc_sg', 'inst_hsbc_sg',
                  'inst_citi_sg', 'inst_maribank', 'inst_gxs_bank', 'inst_trust_bank',
                  'inst_cpf_board', 'inst_iras', 'inst_hdb', 'inst_endowus', 'inst_syfe',
                  'inst_stashaway', 'inst_moomoo', 'inst_tiger', 'inst_ibkr_sg', 'inst_poems',
                  'inst_fsmone', 'inst_maybank', 'inst_cimb',
                  'payee_fairprice', 'payee_sheng_siong', 'payee_cold_storage', 'payee_don_don_donki',
                  'payee_grab', 'payee_gojek', 'payee_cdg_zig', 'payee_simplygo', 'payee_singtel',
                  'payee_starhub', 'payee_m1', 'payee_sp_group', 'payee_iras', 'payee_cpf_board',
                  'payee_shopee', 'payee_lazada', 'payee_foodpanda', 'payee_guardian', 'payee_watsons',
                  'cat_cpf_contributions', 'cat_cpf_housing_grant', 'cat_town_council_scc',
                  'cat_sp_services_util', 'cat_lta_erp_simplygo', 'cat_iras_tax_payment'
              )
          )
    """)
