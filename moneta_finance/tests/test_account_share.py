# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from .common import MonetaTestBase


class TestAccountShare(MonetaTestBase):
    """Test account sharing and joint accounts access grants (v1.14.0)."""

    def setUp(self):
        super().setUp()
        self.user_owner = self._make_user('Owner User', 'owner_user')
        self.user_grantee = self._make_user('Grantee User', 'grantee_user')
        self.user_outsider = self._make_user('Outsider User', 'outsider_user')

        self.account = self._make_account(user=self.user_owner, name='Joint Household Checking')

    def test_account_share_creation_and_visibility(self):
        """Sharing an account makes it visible to grantee via record rules."""
        # Before sharing, grantee cannot see the owner's account
        visible_before = self.env['moneta.account'].with_user(self.user_grantee).search([
            ('id', '=', self.account.id)
        ])
        self.assertEqual(len(visible_before), 0)

        # Create share grant
        share = self.env['moneta.account.share'].create({
            'account_id': self.account.id,
            'user_id': self.user_grantee.id,
            'permission': 'write',
            'is_joint': True,
        })
        self.account.invalidate_recordset(['shared_user_ids', 'is_shared'])

        # Now grantee can see the account
        visible_after = self.env['moneta.account'].with_user(self.user_grantee).search([
            ('id', '=', self.account.id)
        ])
        self.assertEqual(len(visible_after), 1)

        # Outsider still cannot see it
        outsider_visible = self.env['moneta.account'].with_user(self.user_outsider).search([
            ('id', '=', self.account.id)
        ])
        self.assertEqual(len(outsider_visible), 0)

    def test_prevent_self_share(self):
        """Sharing an account with its own owner raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['moneta.account.share'].create({
                'account_id': self.account.id,
                'user_id': self.user_owner.id,
                'permission': 'read',
            })
