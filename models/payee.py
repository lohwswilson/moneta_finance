# -*- coding: utf-8 -*-
import unicodedata
from odoo import models, fields, api


# Business / legal-entity suffixes stripped during payee-name normalization.
# Compared against upper-cased, punctuation-free tokens.
_BUSINESS_SUFFIXES = frozenset({
    "SP", "ZOO", "OO", "SA", "SAS", "GMBH", "INC", "LLC", "LTD", "LTDA", "BV",
    "AG", "SARL", "PLC", "OY", "AB", "KG", "CO", "CORP", "NV", "OOO", "SRL",
    "SPA", "PTY", "PTE", "AS", "ASA", "KFT", "DOO", "EOOD", "OOD", "GES", "MBH",
})

# Latin letters whose diacritic is an integral stroke / ligature that Unicode
# NFD does NOT decompose into a base + combining mark. Mapped to ASCII bases so
# the diacritic strip does not turn them into a word break (e.g. L-stroke -> L).
_NON_DECOMPOSING = {
    "Ł": "L", "ł": "L", "Ø": "O", "ø": "O", "Đ": "D", "đ": "D", "Ð": "D", "ð": "D",
    "Þ": "TH", "þ": "TH", "ẞ": "SS", "ß": "SS", "Æ": "AE", "æ": "AE", "Œ": "OE",
    "œ": "OE", "Ĳ": "IJ", "ĳ": "IJ", "Ħ": "H", "ħ": "H", "Ŧ": "T", "ŧ": "T",
    "Ŀ": "L", "ŀ": "L", "Ŋ": "NG", "ŋ": "NG",
}


class MonetaPayee(models.Model):
    _name = 'moneta.payee'
    _description = 'Moneta Payee'
    _order = 'name'

    name = fields.Char(string='Payee Name', required=True)
    default_category_id = fields.Many2one('moneta.category', string='Default Category')
    notes = fields.Text(string='Notes')
    website = fields.Char(string='Website')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    alias_ids = fields.One2many('moneta.payee.alias', 'payee_id', string='Payee Match Rules')
    active = fields.Boolean(default=True)
    transaction_count = fields.Integer(compute='_compute_transaction_count', string='Transactions')

    # v1.14.0 Analytics & Cadence Detection
    spent_this_year = fields.Monetary(string='Spent This Year', compute='_compute_payee_analytics')
    spent_prior_year = fields.Monetary(string='Spent Prior Year', compute='_compute_payee_analytics')
    spent_yoy_diff = fields.Monetary(string='YoY Spending Change', compute='_compute_payee_analytics')
    avg_transaction_amount = fields.Monetary(string='Average Transaction', compute='_compute_payee_analytics')
    last_transaction_date = fields.Date(string='Last Transaction Date', compute='_compute_payee_analytics')
    detected_cadence = fields.Selection([
        ('none', 'None / Irregular'),
        ('weekly', 'Weekly (~7 days)'),
        ('biweekly', 'Biweekly (~14 days)'),
        ('monthly', 'Monthly (~30 days)'),
        ('quarterly', 'Quarterly (~90 days)'),
        ('yearly', 'Yearly (~365 days)'),
    ], string='Detected Cadence', compute='_compute_payee_analytics')
    suggested_category_id = fields.Many2one(
        'moneta.category', string='Suggested Category',
        compute='_compute_payee_analytics',
    )

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    _sql_constraints = [
        # Faithful to Moneta's @Unique(["userId", "name"]).
        ('unique_user_name', 'unique(user_id, name)',
         'A payee with this name already exists for this user.'),
    ]

    def _compute_transaction_count(self):
        for rec in self:
            rec.transaction_count = self.env['moneta.transaction'].search_count(
                [('payee_id', '=', rec.id)]
            )

    def _compute_payee_analytics(self):
        today = fields.Date.context_today(self)
        this_year_start = today.replace(month=1, day=1)
        prior_year_start = today.replace(year=today.year - 1, month=1, day=1)
        prior_year_end = today.replace(year=today.year - 1, month=12, day=31)

        for rec in self:
            txs = self.env['moneta.transaction'].search([
                ('payee_id', '=', rec.id),
                ('state', '!=', 'void'),
            ], order='transaction_date asc')

            rec.currency_id = rec.env.company.currency_id

            if not txs:
                rec.spent_this_year = 0.0
                rec.spent_prior_year = 0.0
                rec.spent_yoy_diff = 0.0
                rec.avg_transaction_amount = 0.0
                rec.last_transaction_date = False
                rec.detected_cadence = 'none'
                rec.suggested_category_id = False
                continue

            # Spending calculations (expenses are negative)
            this_year_expenses = [abs(t.amount) for t in txs if t.amount < 0 and t.transaction_date >= this_year_start]
            prior_year_expenses = [abs(t.amount) for t in txs if t.amount < 0 and prior_year_start <= t.transaction_date <= prior_year_end]

            rec.spent_this_year = sum(this_year_expenses)
            rec.spent_prior_year = sum(prior_year_expenses)
            rec.spent_yoy_diff = rec.spent_this_year - rec.spent_prior_year

            all_amounts = [abs(t.amount) for t in txs]
            rec.avg_transaction_amount = (sum(all_amounts) / len(all_amounts)) if all_amounts else 0.0
            rec.last_transaction_date = txs[-1].transaction_date

            # Suggested category by majority count
            cat_counts = {}
            for t in txs:
                if t.category_id:
                    cat_counts[t.category_id.id] = cat_counts.get(t.category_id.id, 0) + 1
            if cat_counts:
                best_cat_id = max(cat_counts, key=cat_counts.get)
                rec.suggested_category_id = best_cat_id
            else:
                rec.suggested_category_id = False

            # Cadence detection (if at least 3 transactions exist)
            if len(txs) >= 3:
                dates = [t.transaction_date for t in txs]
                intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
                intervals.sort()
                median_days = intervals[len(intervals) // 2]
                if 5 <= median_days <= 9:
                    rec.detected_cadence = 'weekly'
                elif 10 <= median_days <= 18:
                    rec.detected_cadence = 'biweekly'
                elif 25 <= median_days <= 35:
                    rec.detected_cadence = 'monthly'
                elif 75 <= median_days <= 105:
                    rec.detected_cadence = 'quarterly'
                elif 330 <= median_days <= 400:
                    rec.detected_cadence = 'yearly'
                else:
                    rec.detected_cadence = 'none'
            else:
                rec.detected_cadence = 'none'

    # ------------------------------------------------------------------
    # Tiered payee resolution (faithful to Moneta payees.service.resolveByName):
    #   1. exact (case-insensitive) name
    #   2. wildcard alias -- iterative glob, ReDoS-safe (no regex)
    #   3. normalized form (diacritics stripped, business suffixes dropped)
    # Record rules scope every search to the current user, so resolution is
    # inherently per-owner. Full auto-merge / clustering / Levenshtein parity is
    # a documented follow-up.
    # ------------------------------------------------------------------

    @api.model
    def _resolve_by_name(self, name):
        if not name:
            return self.env['moneta.payee']
        clean = name.strip()
        # 1. Exact (case-insensitive) name.
        payee = self.search([('name', '=ilike', clean)], limit=1)
        if payee:
            return payee
        # 2. Wildcard alias match (ReDoS-safe iterative glob).
        for alias in self.env['moneta.payee.alias'].search([]):
            if self._matches_alias_pattern(clean, alias.pattern):
                return alias.payee_id
        # 3. Normalized-form match.
        norm = self._normalize_name(clean)
        if norm:
            for candidate in self.search([]):
                if self._normalize_name(candidate.name) == norm:
                    return candidate
        return self.env['moneta.payee']

    @staticmethod
    def _matches_alias_pattern(name, pattern):
        """Iterative glob match (case-insensitive, no regex) -- ReDoS-safe, the
        same algorithm as Moneta's matchesAliasPattern. ``*`` is the only
        wildcard; runs of ``*`` collapse to one."""
        if not pattern or not name:
            return False
        if len(pattern) > 500 or len(name) > 500:
            return False
        collapsed = []
        prev_star = False
        for ch in pattern.lower():
            if ch == '*':
                if not prev_star:
                    collapsed.append('*')
                prev_star = True
            else:
                collapsed.append(ch)
                prev_star = False
        pat = ''.join(collapsed)
        text = name.lower()
        parts = pat.split('*')
        if len(parts) == 1:
            return text == pat
        if not text.startswith(parts[0]):
            return False
        if not text.endswith(parts[-1]):
            return False
        pos = len(parts[0])
        for i in range(1, len(parts) - 1):
            idx = text.find(parts[i], pos)
            if idx == -1:
                return False
            pos = idx + len(parts[i])
        if len(parts) > 2:
            suffix_start = len(text) - len(parts[-1])
            if pos > suffix_start:
                return False
        return True

    @staticmethod
    def _normalize_name(name):
        """Canonical comparison form: transliterate non-decomposing letters,
        strip diacritics (NFD), upper-case, drop punctuation, and drop
        single-char / pure-digit / business-suffix tokens. Mirrors Moneta's
        normalizePayeeName."""
        if not name:
            return ''
        s = ''.join(_NON_DECOMPOSING.get(ch, ch) for ch in name)
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        s = s.upper()
        tokens = []
        for tok in ''.join(c if c.isalnum() else ' ' for c in s).split():
            if len(tok) < 2:
                continue
            if tok.isdigit():
                continue
            if tok in _BUSINESS_SUFFIXES:
                continue
            tokens.append(tok)
        return ' '.join(tokens)


class MonetaPayeeAlias(models.Model):
    _name = 'moneta.payee.alias'
    _description = 'Moneta Payee Matching Rule/Alias'

    payee_id = fields.Many2one('moneta.payee', string='Payee', required=True, ondelete='cascade')
    pattern = fields.Char(string='Match String / Pattern', required=True,
                          help='Wildcard pattern (* matches anything) used to match imported payee names')
    # Stored related owner so the per-user record rule resolves to the payee owner.
    user_id = fields.Many2one('res.users', related='payee_id.user_id', store=True, index=True)