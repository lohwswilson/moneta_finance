# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestEmergencyAccess(MonetaTestBase):

    def test_emergency_contact_claim_and_decline(self):
        """Test initiating a claim and owner declining it."""
        owner = self._make_user('Owner User', 'owner_user')
        contact = self.env['moneta.emergency.contact'].with_user(owner).create({
            'name': 'Trusted Spouse',
            'email': 'spouse@example.com',
            'relationship': 'spouse',
            'waiting_period_days': 14,
        })
        self.assertEqual(contact.status, 'active')

        # Initiate claim
        contact.action_initiate_claim()
        self.assertEqual(contact.status, 'pending_claim')
        self.assertTrue(contact.claim_request_date)
        self.assertTrue(contact.unlock_date)
        self.assertGreaterEqual(contact.days_remaining, 13)

        # Owner declines claim
        contact.action_decline_claim()
        self.assertEqual(contact.status, 'declined')
        self.assertFalse(contact.claim_request_date)

    def test_emergency_access_cron_and_account_share(self):
        """Test cron automatically unlocking access upon waiting period expiration."""
        owner = self._make_user('Vault Owner', 'vault_owner')
        contact_user = self._make_user('Executor User', 'executor_user', email='executor@example.com')

        # Owner creates checking account
        acc = self.env['moneta.account'].with_user(owner).create({
            'name': 'Family Checking',
            'account_type': 'checking',
            'opening_balance': 10000.0,
        })

        # Designate emergency contact with 7-day waiting period
        contact = self.env['moneta.emergency.contact'].with_user(owner).create({
            'name': 'Executor User',
            'email': 'executor@example.com',
            'relationship': 'executor',
            'waiting_period_days': 7,
        })
        contact.action_initiate_claim()

        # Simulate time passing (8 days ago)
        past_date = fields.Datetime.now() - timedelta(days=8)
        contact.write({'claim_request_date': past_date})

        # Run daily cron
        self.env['moneta.emergency.contact']._cron_check_emergency_access()

        contact.invalidate_recordset()
        self.assertEqual(contact.status, 'approved')
        self.assertTrue(contact.access_granted_date)

        # Verify read-only account share was provisioned
        share = self.env['moneta.account.share'].search([
            ('account_id', '=', acc.id),
            ('shared_with_user_id', '=', contact_user.id),
        ])
        self.assertTrue(share)
        self.assertEqual(share.permission, 'read')

        # Revoke access and verify deprovisioning
        contact.action_revoke_access()
        self.assertEqual(contact.status, 'revoked')
        shares_after = self.env['moneta.account.share'].search([
            ('account_id', '=', acc.id),
            ('shared_with_user_id', '=', contact_user.id),
        ])
        self.assertFalse(shares_after, "Shares must be unlinked upon revocation")
