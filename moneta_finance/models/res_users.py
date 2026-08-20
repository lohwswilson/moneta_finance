# -*- coding: utf-8 -*-
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        # Seeding must never break user creation: a failure here is logged, not
        # raised, so a new user is always saved even if their default categories
        # could not be built.
        self._seed_moneta_defaults(users)
        return users

    def write(self, vals):
        res = super().write(vals)
        # Only the group-membership path is interesting; every other res.users
        # write (last login, preferences) skips this branch entirely.
        if 'groups_id' in vals:
            self._seed_moneta_defaults(self)
        return res

    def _seed_moneta_defaults(self, users):
        """Seed default categories for any user who is a Moneta user but owns
        none yet. Idempotent: ``moneta.category._seed_user_defaults`` skips users
        that already own categories, so re-runs and the post-install hook are
        safe. Failures are logged, not raised, so core user writes are never
        blocked by a seeding problem. ``moneta_no_seed`` in the context opts
        out (used by tests that want deterministic, empty per-user data)."""
        if self.env.context.get('moneta_no_seed'):
            return
        Category = self.env['moneta.category'].sudo()
        for user in users:
            try:
                if user.has_group('moneta_finance.group_moneta_user'):
                    Category._seed_user_defaults(user)
            except Exception as exc:  # noqa: BLE001 - seeding must not block writes
                _logger.exception("Failed seeding Moneta default categories for user %s: %s", user.id, exc)