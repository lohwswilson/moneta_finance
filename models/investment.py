# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


def _field_is_null(env, model, rec_id, fname):
    """True when the field's DB value is NULL.

    Odoo coerces NULL numerics to 0.0 on read, so the ORM cannot distinguish
    'unknown' from 'zero' -- null propagation (unknown != 0) therefore checks
    the column directly. ``fname`` and the table name are compile-time
    constants, never user input; the id is parameterized.
    """
    env.cr.execute(
        "SELECT %s IS NULL FROM %s WHERE id = %%s" % (fname, model._table),
        (rec_id,),
    )
    row = env.cr.fetchone()
    return bool(row and row[0])


class MonetaSecurity(models.Model):
    _name = 'moneta.security'
    _description = 'Moneta Investment Security / Asset'
    _order = 'symbol, name'

    name = fields.Char(string='Security Name', required=True)
    symbol = fields.Char(string='Ticker Symbol', required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Quote Currency', default=lambda self: self.env.company.currency_id, required=True)

    asset_class = fields.Selection([
        ('stock', 'Stock / Equity'),
        ('etf', 'ETF'),
        ('mutual_fund', 'Mutual Fund'),
        ('bond', 'Bond / Fixed Income'),
        ('crypto', 'Cryptocurrency'),
        ('cash', 'Cash Equivalent'),
        ('real_estate', 'Real Estate / REIT'),
        ('commodities', 'Commodities / Gold'),
    ], string='Primary Asset Class', default='stock', required=True)

    exchange = fields.Char(string='Exchange', help='NYSE, NASDAQ, TSX, etc.')
    isin = fields.Char(string='ISIN / CUSIP')
    notes = fields.Text(string='Notes')

    website_url = fields.Char(string='Company Website')
    ir_url = fields.Char(string='Investor Relations Website')
    quote_timestamp = fields.Datetime(string='Quote Timestamp')
    is_market_open = fields.Boolean(string='Market Currently Open', default=False)

    # Multi-asset class weighting (v1.14.0 look-through allocation)
    allocation_ids = fields.One2many('moneta.security.allocation', 'security_id', string='Asset Allocations')
    total_allocation_weight = fields.Float(
        string='Total Allocated (%)',
        compute='_compute_total_allocation_weight',
    )

    # Documents & Factsheets
    document_ids = fields.Many2many(
        'ir.attachment',
        'moneta_security_attachment_rel',
        'security_id',
        'attachment_id',
        string='Documents & Factsheets',
    )

    # Null propagation: no price entry yet -> False (unknown), never 0.0.
    # Non-stored: computed on read, so a fresh price is always picked up
    # without relying on Odoo 18's cross-record trigger machinery.
    current_price = fields.Monetary(string='Latest Price', compute='_compute_current_price')
    price_ids = fields.One2many('moneta.security.price', 'security_id', string='Historical Prices')
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )

    @api.depends('allocation_ids.weight')
    def _compute_total_allocation_weight(self):
        for sec in self:
            sec.total_allocation_weight = sum(sec.allocation_ids.mapped('weight'))

    @api.constrains('allocation_ids')
    def _check_allocation_total(self):
        for sec in self:
            if sec.allocation_ids:
                total = sum(sec.allocation_ids.mapped('weight'))
                if total > 100.001:
                    raise ValidationError(
                        f"Total allocation weights for security '{sec.name}' cannot exceed 100% (currently {total:.2f}%)."
                    )

    @api.depends('price_ids', 'price_ids.price_close', 'price_ids.price_date')
    def _compute_current_price(self):
        for sec in self:
            latest = self.env['moneta.security.price'].search(
                [('security_id', '=', sec.id)], order='price_date desc', limit=1
            )
            # False writes NULL: no price means the price is unknown.
            sec.current_price = latest.price_close if latest else False


class MonetaSecurityAllocation(models.Model):
    _name = 'moneta.security.allocation'
    _description = 'Moneta Security Asset Class Weighting'
    _order = 'weight desc, asset_class'

    security_id = fields.Many2one('moneta.security', string='Security', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', related='security_id.user_id', store=True, index=True)
    asset_class = fields.Selection([
        ('stock', 'Stock / Equity'),
        ('etf', 'ETF'),
        ('mutual_fund', 'Mutual Fund'),
        ('bond', 'Bond / Fixed Income'),
        ('crypto', 'Cryptocurrency'),
        ('cash', 'Cash Equivalent'),
        ('real_estate', 'Real Estate / REIT'),
        ('commodities', 'Commodities / Gold'),
    ], string='Asset Class', required=True, default='stock')
    weight = fields.Float(string='Weight (%)', required=True, default=100.0, digits=(5, 2))
    country_code = fields.Char(string='Country Code', size=2, help='ISO 2-letter country code (e.g. US, CA, DE, GB, JP)')

    _sql_constraints = [
        ('security_asset_uniq', 'unique(security_id, asset_class, country_code)', 'Allocation entry already exists for this security and asset class!'),
    ]

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0.0 or rec.weight > 100.0:
                raise ValidationError('Weight must be between 0% and 100%.')


class MonetaSecurityPrice(models.Model):
    _name = 'moneta.security.price'
    _description = 'Moneta Daily Security Price Entry'
    _order = 'price_date desc, security_id'

    security_id = fields.Many2one('moneta.security', string='Security', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='security_id.currency_id', readonly=True)
    # Stored related owner so the per-user record rule resolves to the security owner.
    user_id = fields.Many2one('res.users', related='security_id.user_id', store=True, index=True)

    price_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, index=True)
    price_close = fields.Monetary(string='Closing Price', required=True, default=0.0)
    source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('yahoo', 'Yahoo Finance'),
        ('msn', 'MSN Money'),
        ('imported', 'Imported')
    ], string='Data Source', default='manual')

    _sql_constraints = [
        ('security_date_uniq', 'unique(security_id, price_date)', 'A price entry already exists for this security on this date!')
    ]

    def _rebuild_holding_accounts(self):
        """A price change alters the market value of every holding of the
        security, so the monthly snapshots of the holding accounts must be
        rebuilt (rebuild-on-write)."""
        accounts = self.env['moneta.holding'].search([
            ('security_id', '=', self.security_id.id),
        ]).mapped('account_id')
        for account in accounts:
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)

    @api.model_create_multi
    def create(self, vals_list):
        prices = super().create(vals_list)
        for price in prices:
            price._rebuild_holding_accounts()
        return prices

    def write(self, vals):
        res = super().write(vals)
        for price in self:
            price._rebuild_holding_accounts()
        return res

    def unlink(self):
        securities = self.mapped('security_id')
        res = super().unlink()
        for security in securities:
            accounts = self.env['moneta.holding'].search([
                ('security_id', '=', security.id),
            ]).mapped('account_id')
            for account in accounts:
                self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return res


class MonetaInvestmentTransaction(models.Model):
    _name = 'moneta.investment.transaction'
    _description = 'Moneta Investment Transaction'
    _order = 'trade_date desc, id desc'

    action = fields.Selection([
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('dividend', 'Dividend'),
        ('interest', 'Interest'),
        ('split', 'Split'),
    ], string='Action', required=True, default='buy')

    account_id = fields.Many2one(
        'moneta.account', string='Brokerage Account',
        domain="[('account_type', '=', 'brokerage')]",
        required=True, ondelete='cascade',
    )
    security_id = fields.Many2one('moneta.security', string='Security', required=True)
    trade_date = fields.Date(string='Trade Date', default=fields.Date.context_today, required=True)

    # Shares 8dp, prices 10dp (Moneta precision). price is NULLABLE: a null
    # price means the cost is unknown -- never defaulted to 0 to keep a
    # formula running (null propagation).
    quantity = fields.Float(string='Quantity', digits=(16, 8), default=0.0)
    price = fields.Float(string='Price', digits=(16, 10))
    commission = fields.Monetary(string='Commission', default=0.0)

    # buy: qty*price + commission; sell: qty*price - commission;
    # dividend/interest: (qty or 1) * price; split: 0. False when price
    # unknown. Non-stored: computed on read (no trigger machinery needed).
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount')

    # NULL until a sell/dividend/interest establishes it (set by the holding
    # rebuild). buy/sell cash impact is deferred from the MVP.
    realized_gain = fields.Monetary(string='Realized Gain / Loss')

    memo = fields.Char(string='Memo')
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', store=True, readonly=True)
    # Cash income transaction created for dividends/interest; removed together
    # with this record (ondelete set null so no cascade surprises).
    linked_transaction_id = fields.Many2one('moneta.transaction', string='Linked Cash Entry', ondelete='set null')

    # Stored related owner so the per-user record rule resolves to the account owner.
    user_id = fields.Many2one('res.users', related='account_id.user_id', store=True, index=True)

    _sql_constraints = [
        ('check_quantity_non_negative', 'CHECK (quantity >= 0)',
         'Quantity cannot be negative.'),
        ('check_price_non_negative', 'CHECK (price IS NULL OR price >= 0)',
         'Price cannot be negative.'),
        ('check_split_ratio_positive', 'CHECK (action <> \'split\' OR quantity > 0)',
         'A split ratio must be positive.'),
    ]

    @api.depends('action', 'quantity', 'price', 'commission')
    def _compute_total_amount(self):
        for tx in self:
            if tx.action == 'split':
                tx.total_amount = 0.0
                continue
            if _field_is_null(self.env, tx, tx.id, 'price'):
                # Unknown cost -> unknown total (never 0 to keep a formula running).
                tx.total_amount = False
                continue
            qty = tx.quantity or 0.0
            price = tx.price or 0.0
            commission = tx.commission or 0.0
            if tx.action in ('dividend', 'interest'):
                tx.total_amount = round((qty or 1.0) * price, 4)
            elif tx.action == 'buy':
                tx.total_amount = round(qty * price + commission, 4)
            else:  # sell
                tx.total_amount = round(qty * price - commission, 4)

    # ------------------------------------------------------------------
    # Validation (rejection before write)
    # ------------------------------------------------------------------

    def _projected_quantity(self, account, security_id, exclude_ids=(), extra_sell=0.0):
        """Held quantity computed from existing transactions, optionally
        excluding records being edited and adding a proposed sell."""
        qty = 0.0
        txs = self.search([
            ('account_id', '=', account.id),
            ('security_id', '=', security_id),
        ])
        for tx in txs:
            if tx.id in exclude_ids:
                continue
            if tx.action == 'buy':
                qty += tx.quantity or 0.0
            elif tx.action == 'sell':
                qty -= tx.quantity or 0.0
            elif tx.action == 'split':
                qty *= tx.quantity or 1.0
        return qty - extra_sell

    def _check_holding(self, account_id, security_id, exclude_ids=(), extra_sell=0.0):
        """Reject a sell that exceeds the held quantity and a non-brokerage
        account -- inside the same override as the mutation (rejection before
        write)."""
        account = self.env['moneta.account'].browse(account_id)
        if account.account_type != 'brokerage':
            raise ValidationError("Investment transactions require a brokerage account.")
        projected = self._projected_quantity(account, security_id, exclude_ids, extra_sell)
        if projected < -1e-8:
            raise ValidationError(
                "Cannot sell more than the held quantity (held: %s)." % round(max(projected + extra_sell, 0.0), 8)
            )

    # ------------------------------------------------------------------
    # ORM overrides (rebuild-on-write)
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('action') == 'sell':
                self._check_holding(
                    vals['account_id'], vals['security_id'],
                    extra_sell=vals.get('quantity') or 0.0,
                )
        txs = super().create(vals_list)
        for tx in txs:
            if tx.action in ('dividend', 'interest'):
                tx._create_cash_income_transaction()
        self._rebuild_holdings(txs)
        for account in txs.mapped('account_id'):
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return txs

    def write(self, vals):
        # The holding rebuild writes realized_gain back onto sell/dividend
        # records; that internal write must not re-enter this override.
        if vals.keys() <= {'realized_gain'}:
            return super().write(vals)
        for tx in self:
            if (tx.action == 'sell' and 'quantity' in vals) or vals.get('action') == 'sell':
                self._check_holding(
                    vals.get('account_id', tx.account_id.id),
                    vals.get('security_id', tx.security_id.id),
                    exclude_ids=self.ids,
                    extra_sell=vals.get('quantity', tx.quantity) or 0.0,
                )
        res = super().write(vals)
        self._rebuild_holdings(self)
        for account in self.mapped('account_id'):
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return res

    def unlink(self):
        # Remove the linked cash entry first so its balance delta reverses.
        cash = self.mapped('linked_transaction_id')
        if cash:
            cash.unlink()
        pairs = {(tx.account_id.id, tx.security_id.id) for tx in self}
        accounts = self.mapped('account_id')
        res = super().unlink()
        for account_id, security_id in pairs:
            self.env['moneta.holding']._rebuild(
                self.env['moneta.account'].browse(account_id),
                self.env['moneta.security'].browse(security_id),
            )
        for account in accounts:
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return res

    def _rebuild_holdings(self, txs):
        for tx in txs:
            self.env['moneta.holding']._rebuild(tx.account_id, tx.security_id)

    def _create_cash_income_transaction(self):
        """Dividends/interest post a cash income transaction in the brokerage
        account (Moneta: dividend -> cash income entry). The investment record
        itself carries no quantity change; its realized_gain is the amount.
        When the dividend's amount is unknown (no price), no cash entry is
        posted -- an unknown amount never posts as zero (null propagation).
        The unknown check reads the price column directly: total_amount reads
        0.0 either way (Odoo numeric coercion)."""
        self.ensure_one()
        if _field_is_null(self.env, self, self.id, 'price'):
            return
        amount = self.total_amount
        category = self.env['moneta.category'].search([
            ('name', '=', 'Investment Income'),
            ('user_id', '=', self.user_id.id),
        ], limit=1)
        cash_tx = self.env['moneta.transaction'].create({
            'account_id': self.account_id.id,
            'transaction_date': self.trade_date,
            'category_id': category.id if category else False,
            'amount': amount,
            'memo': self.memo or '%s on %s' % (self.action.title(), self.security_id.symbol),
            'state': 'cleared',
        })
        # Link without re-entering this override (super().write bypasses it).
        super(MonetaInvestmentTransaction, self).write(
            {'linked_transaction_id': cash_tx.id}
        )


class MonetaHolding(models.Model):
    _name = 'moneta.holding'
    _description = 'Moneta Portfolio Holding'
    _order = 'account_id, security_id'

    account_id = fields.Many2one('moneta.account', string='Investment Account', domain="[('account_type', '=', 'brokerage')]", required=True, ondelete='cascade')
    security_id = fields.Many2one('moneta.security', string='Security', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='security_id.currency_id', readonly=True)

    # Derived from investment transactions (average cost, commission in basis).
    # NULL average_cost = unknown cost basis (null propagation), never 0.
    quantity = fields.Float(string='Shares / Units', digits=(16, 8), default=0.0)
    average_cost = fields.Monetary(string='Average Cost / Unit')

    current_price = fields.Monetary(related='security_id.current_price', string='Current Price', readonly=True)
    # Odoo coerces every numeric assignment through float(value or 0.0), so a
    # Monetary field cannot itself express 'unknown' -- the null propagation
    # contract is carried by explicit known-flags (booleans never coerce).
    # Consumers treat the value as unknown when the flag is False.
    price_known = fields.Boolean(string='Price Known', compute='_compute_valuation')
    basis_known = fields.Boolean(string='Cost Basis Known', compute='_compute_valuation')
    market_value = fields.Monetary(string='Market Value', compute='_compute_valuation')
    cost_basis = fields.Monetary(string='Cost Basis', compute='_compute_valuation')
    unrealized_gain = fields.Monetary(string='Unrealized Gain / Loss', compute='_compute_valuation')
    unrealized_gain_percent = fields.Float(string='Gain / Loss (%)', compute='_compute_valuation', digits=(5, 2))
    asset_class = fields.Selection(related='security_id.asset_class', string='Asset Class', store=True)
    symbol = fields.Char(related='security_id.symbol', string='Symbol', store=True)

    # Stored related owner so the per-user record rule resolves to the account owner.
    user_id = fields.Many2one('res.users', related='account_id.user_id', store=True, index=True)

    @api.depends('quantity', 'average_cost', 'current_price')
    def _compute_valuation(self):
        for holding in self:
            price_known = self.env['moneta.security.price'].search_count([
                ('security_id', '=', holding.security_id.id),
            ]) > 0
            basis_known = not _field_is_null(self.env, self, holding.id, 'average_cost')
            holding.price_known = price_known
            holding.basis_known = basis_known
            qty = holding.quantity or 0.0
            price = holding.current_price or 0.0
            avg = holding.average_cost or 0.0
            holding.market_value = round(qty * price, 4)
            holding.cost_basis = round(qty * avg, 4) if basis_known else 0.0
            if basis_known:
                holding.unrealized_gain = round(holding.market_value - holding.cost_basis, 4)
                holding.unrealized_gain_percent = round(((holding.unrealized_gain / holding.cost_basis) * 100.0), 2) if holding.cost_basis > 0 else 0.0
            else:
                holding.unrealized_gain = 0.0
                holding.unrealized_gain_percent = 0.0

    @api.model
    def _rebuild(self, account, security):
        """Recompute the (account, security) holding from its investment
        transactions, in trade order (Moneta average-cost):

          * buy      blends (qty_before * avg + qty * price + commission) / qty_after
          * sell     relieves quantity (basis relieved at the running average)
          * split    scales quantity by the ratio and divides the average
          * an unknown-price buy poisons the average (null propagation: a total
            with an unknown component is unknown, never 0)

        Also writes realized_gain back onto sell/dividend/interest records and
        deletes the holding when no investment transactions remain.
        """
        txs = self.env['moneta.investment.transaction'].search([
            ('account_id', '=', account.id),
            ('security_id', '=', security.id),
        ], order='trade_date, id')
        holding = self.search([
            ('account_id', '=', account.id),
            ('security_id', '=', security.id),
        ], limit=1)
        if not txs:
            if holding:
                holding.unlink()
            return

        qty = 0.0
        avg = False  # False = unknown (no known-cost basis yet)
        for tx in txs:
            if tx.action == 'buy':
                qty_before = qty
                qty += tx.quantity or 0.0
                if _field_is_null(self.env, tx, tx.id, 'price'):
                    avg = False
                elif avg is False:
                    # First known-price buy. Shares from earlier unknown buys
                    # (qty_before > 0) keep the average unknown -- their cost
                    # is unknowable, so the blend cannot include them.
                    if qty_before > 0:
                        avg = False
                    else:
                        avg = round(
                            ((tx.quantity or 0.0) * (tx.price or 0.0) + (tx.commission or 0.0)) / qty,
                            8,
                        )
                else:
                    total_cost = qty_before * avg + (tx.quantity or 0.0) * (tx.price or 0.0) + (tx.commission or 0.0)
                    avg = round(total_cost / qty, 8)
            elif tx.action == 'sell':
                qty -= tx.quantity or 0.0
                # Realized gain: proceeds (qty*price - commission) minus the
                # relieved basis (sell_qty * avg); NULL when either is unknown.
                price_unknown = _field_is_null(self.env, tx, tx.id, 'price')
                if price_unknown or avg is False:
                    realized = False
                else:
                    proceeds = (tx.quantity or 0.0) * (tx.price or 0.0) - (tx.commission or 0.0)
                    realized = round(proceeds - (tx.quantity or 0.0) * avg, 4)
                self.env['moneta.investment.transaction'].browse(tx.id).write(
                    {'realized_gain': realized}
                )
            elif tx.action == 'split':
                ratio = tx.quantity or 1.0
                qty *= ratio
                if avg is not False:
                    avg = round((avg or 0.0) / ratio, 8)
            elif tx.action in ('dividend', 'interest'):
                # Realized gain is the amount; the cash entry is a separate
                # transaction created by the investment record itself.
                self.env['moneta.investment.transaction'].browse(tx.id).write(
                    {'realized_gain': tx.total_amount}
                )
            else:
                # buy/split never carry a realized gain; clear stale values
                # (e.g. a record converted from sell to buy).
                self.env['moneta.investment.transaction'].browse(tx.id).write(
                    {'realized_gain': False}
                )

        if not holding:
            holding = self.create({
                'account_id': account.id,
                'security_id': security.id,
            })
        # Writing False stores NULL for an unknown average (verified: Odoo 18
        # maps False -> NULL on numeric columns).
        holding.write({
            'quantity': round(qty, 8),
            'average_cost': avg,
        })