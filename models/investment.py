import json
import urllib.request
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
    if not rec_id:
        return True
    if isinstance(rec_id, models.NewId) or (isinstance(rec_id, str) and not rec_id.isdigit()):
        return True
    if hasattr(rec_id, 'origin') and rec_id.origin:
        rec_id = rec_id.origin.id
    if isinstance(rec_id, models.NewId) or not isinstance(rec_id, int):
        return True

    env.cr.execute(
        "SELECT %s IS NULL FROM %s WHERE id = %%s" % (fname, model._table),
        (rec_id,),
    )
    row = env.cr.fetchone()
    return bool(row and row[0])


def _xirr(cashflows, max_rate=10.0, tol=1e-7, iters=200):
    """Annualized money-weighted return (XIRR) for dated cash flows.

    ``cashflows`` is a list of ``(datetime.date, float)`` tuples in the
    investor's convention: outflows negative (buys), inflows positive (sells,
    dividends, terminal market value). Returns the annualized rate ``r`` that
    solves ``sum(cf / (1 + r) ** ((d - d0) / 365)) == 0`` via bisection, or
    ``None`` when no real root is bracketed (all cash flows share a sign -- no
    outflow or no inflow).
    """
    if not cashflows or len(cashflows) < 2:
        return None
    amounts = [cf for _, cf in cashflows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None
    d0 = min(d for d, _ in cashflows)

    def npv(rate):
        total = 0.0
        for d, cf in cashflows:
            years = (d - d0).days / 365.0
            total += cf / ((1.0 + rate) ** years)
        return total

    lo, hi = -0.999999, max_rate
    f_lo, f_hi = npv(lo), npv(hi)
    # A very large late inflow can push the root past the default ceiling;
    # expand the upper bound while NPV is still positive there.
    while f_hi > 0 and hi < 1e6:
        hi *= 4.0
        f_hi = npv(hi)
    if f_lo * f_hi > 0:
        return None  # no sign change in the bracket -> no real root
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def _modified_dietz(cashflows, end_value, end_date):
    """Time-weighted return (Modified Dietz) for dated cash flows.

    ``cashflows`` is in the *portfolio* convention: contributions (buys)
    positive, withdrawals (sells / dividends) negative. ``end_value`` is the
    market value still invested at ``end_date``; the beginning value is taken
    as 0 (the holding starts empty). Returns the period return (e.g. ``0.10``
    for +10%), or ``None`` when the weighted-capital denominator is zero (no
    invested capital over the period).
    """
    if not cashflows or end_date is None:
        return None
    d0 = min(d for d, _ in cashflows)
    total_days = (end_date - d0).days
    net_cf = 0.0
    weighted = 0.0
    if total_days <= 0:
        # Everything happened on one day: a plain total return over the single
        # contribution (no time weighting is possible, or needed).
        for _, cf in cashflows:
            net_cf += cf
        weighted = net_cf
    else:
        for d, cf in cashflows:
            net_cf += cf
            w = (total_days - (d - d0).days) / float(total_days)
            weighted += cf * w
    if weighted == 0:
        return None
    return (end_value - net_cf) / weighted


class MonetaSecurity(models.Model):
    _name = 'moneta.security'
    _description = 'Moneta Investment Security / Asset'
    _order = 'symbol, name'
    @api.depends('symbol', 'name')
    def _compute_display_name(self):
        for sec in self:
            if sec.symbol and sec.name and sec.symbol != sec.name:
                sec.display_name = f"[{sec.symbol}] {sec.name}"
            else:
                sec.display_name = sec.symbol or sec.name or 'Security'


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

    # Dividend Tracking (Wealthfolio Style)
    annual_dividend_rate = fields.Monetary(string='Annual Dividend / Share', default=0.0)
    dividend_yield_pct = fields.Float(string='Dividend Yield (%)', digits=(5, 2), default=0.0)
    dividend_frequency = fields.Selection([
        ('monthly', 'Monthly (12x/yr)'),
        ('quarterly', 'Quarterly (4x/yr)'),
        ('semi_annual', 'Semi-Annual (2x/yr)'),
        ('annual', 'Annual (1x/yr)'),
    ], string='Dividend Frequency', default='quarterly')
    next_ex_dividend_date = fields.Date(string='Next Ex-Dividend Date')
    next_pay_date = fields.Date(string='Next Pay Date')
    is_benchmark = fields.Boolean(string='Is Benchmark Index (S&P 500 / VOO / VT)', default=False)

    # MS Money Market & Valuation Metrics (Track 2.3)
    fifty_two_week_high = fields.Monetary(string='52-Week High')
    fifty_two_week_low = fields.Monetary(string='52-Week Low')
    day_change = fields.Monetary(string="Day's Change ($)")
    day_change_percent = fields.Float(string="Day's Change (%)", digits=(5, 2))
    day_volume = fields.Float(string="Volume (Shares)", digits=(12, 0))
    market_cap = fields.Monetary(string='Market Capitalization')
    pe_ratio = fields.Float(string='P/E Ratio', digits=(6, 2))
    forward_pe = fields.Float(string='Forward P/E', digits=(6, 2))
    eps = fields.Monetary(string='EPS')
    beta = fields.Float(string='Beta', digits=(5, 2))

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


    @api.model
    def _lookup_symbol_info(self, symbol):
        """Query public market quote endpoint to auto-discover ticker metadata."""
        if not symbol:
            return {}
        sym = symbol.strip().upper()
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
                if not meta:
                    return {}

                name = meta.get('shortName') or meta.get('longName') or sym
                exchange = meta.get('fullExchangeName') or meta.get('exchangeName') or ''
                curr_code = (meta.get('currency') or 'USD').upper()
                if curr_code in ('GBP', 'GBP'):
                    curr_code = 'GBP'
                price = meta.get('regularMarketPrice')
                prev_close = meta.get('chartPreviousClose') or meta.get('previousClose')
                day_change = (price - prev_close) if (price is not None and prev_close is not None) else 0.0
                day_change_pct = (day_change / prev_close * 100.0) if prev_close else 0.0
                high_52 = meta.get('fiftyTwoWeekHigh') or meta.get('regularMarketDayHigh')
                low_52 = meta.get('fiftyTwoWeekLow') or meta.get('regularMarketDayLow')
                volume = meta.get('regularMarketVolume')
                inst_type = (meta.get('instrumentType') or '').lower()

                asset_class = 'stock'
                if 'etf' in inst_type:
                    asset_class = 'etf'
                elif 'crypto' in inst_type or sym.endswith('-USD'):
                    asset_class = 'crypto'
                elif 'fund' in inst_type:
                    asset_class = 'mutual_fund'
                elif 'bond' in inst_type:
                    asset_class = 'bond'

                curr = self.env['res.currency'].with_context(active_test=False).search([('name', '=', curr_code)], limit=1)
                if curr and not curr.active:
                    curr.active = True

                return {
                    'symbol': sym,
                    'name': name,
                    'exchange': exchange,
                    'currency_id': curr.id if curr else self.env.company.currency_id.id,
                    'asset_class': asset_class,
                    'price': float(price) if price is not None else False,
                    'day_change': float(day_change) if day_change is not None else 0.0,
                    'day_change_percent': float(day_change_pct) if day_change_pct is not None else 0.0,
                    'fifty_two_week_high': float(high_52) if high_52 is not None else False,
                    'fifty_two_week_low': float(low_52) if low_52 is not None else False,
                    'day_volume': float(volume) if volume is not None else 0.0,
                }
        except Exception:
            return {}

    @api.onchange('symbol')
    def _onchange_symbol(self):
        if self.symbol:
            info = self._lookup_symbol_info(self.symbol)
            if info:
                self.symbol = info.get('symbol', self.symbol.upper())
                self.name = info.get('name') or self.name or self.symbol
                if info.get('exchange'):
                    self.exchange = info.get('exchange')
                if info.get('asset_class'):
                    self.asset_class = info.get('asset_class')
                if info.get('currency_id'):
                    self.currency_id = info.get('currency_id')
                if info.get('quote_timestamp'):
                    self.quote_timestamp = info.get('quote_timestamp')
                if info.get('day_change') is not None:
                    self.day_change = info.get('day_change')
                if info.get('day_change_percent') is not None:
                    self.day_change_percent = info.get('day_change_percent')
                if info.get('fifty_two_week_high'):
                    self.fifty_two_week_high = info.get('fifty_two_week_high')
                if info.get('fifty_two_week_low'):
                    self.fifty_two_week_low = info.get('fifty_two_week_low')
                if info.get('day_volume'):
                    self.day_volume = info.get('day_volume')
                price = info.get('price')
                if price:
                    today = fields.Date.context_today(self)
                    self.price_ids = [(5, 0, 0), (0, 0, {
                        'price_date': today,
                        'price_close': price,
                        'source': 'yahoo',
                    })]


    @api.model
    def name_create(self, name):
        """Allow 1-click quick-creation from dropdowns (e.g. typing NVDA)."""
        symbol = name.strip().upper()
        info = self._lookup_symbol_info(symbol)
        vals = {
            'symbol': symbol,
            'name': info.get('name') or name,
            'exchange': info.get('exchange', ''),
            'asset_class': info.get('asset_class', 'stock'),
            'currency_id': info.get('currency_id', self.env.company.currency_id.id),
        }
        sec = self.create(vals)
        return sec.id, sec.display_name


    @api.model
    def _cron_fetch_live_quotes(self):
        """Automated Cron: fetch latest live market prices for all tracked securities in portfolio."""
        holdings = self.env['moneta.holding'].search([('quantity', '>', 0)])
        securities = holdings.mapped('security_id')
        if not securities:
            securities = self.search([('symbol', '!=', False)])
        
        today = fields.Date.context_today(self)
        for sec in securities:
            if not sec.symbol:
                continue
            try:
                info = sec._lookup_symbol_info(sec.symbol)
                price = info.get('price')
                if price:
                    existing = self.env['moneta.security.price'].search([
                        ('security_id', '=', sec.id),
                        ('price_date', '=', today),
                    ], limit=1)
                    if existing:
                        existing.write({'price_close': price, 'source': 'yahoo'})
                    else:
                        self.env['moneta.security.price'].create({
                            'security_id': sec.id,
                            'price_date': today,
                            'price_close': price,
                            'source': 'yahoo',
                        })
            except Exception:
                continue
        
        self.env['moneta.holding'].invalidate_model()
        for acc in holdings.mapped('account_id'):
            self.env['moneta.account.balance.monthly']._rebuild_for_account(acc)

    def action_fetch_quote(self):
        """Fetch live quote and auto-fill metadata from Yahoo Finance."""
        today = fields.Date.context_today(self)
        count = 0
        for rec in self:
            if not rec.symbol:
                continue
            info = rec._lookup_symbol_info(rec.symbol)
            if not info:
                continue
            vals = {
                'symbol': info.get('symbol', rec.symbol),
                'name': info.get('name') or rec.name or rec.symbol,
                'exchange': info.get('exchange') or rec.exchange,
                'asset_class': info.get('asset_class') or rec.asset_class,
                'currency_id': info.get('currency_id') or rec.currency_id.id,
                'day_change': info.get('day_change', 0.0),
                'day_change_percent': info.get('day_change_percent', 0.0),
                'fifty_two_week_high': info.get('fifty_two_week_high', False),
                'fifty_two_week_low': info.get('fifty_two_week_low', False),
                'day_volume': info.get('day_volume', 0.0),
            }
            rec.write(vals)

            price = info.get('price')
            if price:
                existing_price = self.env['moneta.security.price'].search([
                    ('security_id', '=', rec.id),
                    ('price_date', '=', today),
                ], limit=1)
                if existing_price:
                    existing_price.write({'price_close': price, 'source': 'yahoo'})
                else:
                    self.env['moneta.security.price'].create({
                        'security_id': rec.id,
                        'price_date': today,
                        'price_close': price,
                        'source': 'yahoo',
                    })
            count += 1

        if len(self) == 1 and count == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lookup Notice',
                    'message': f"No online quote data found for '{self.symbol}'. You can fill in the details manually.",
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Live Quotes Updated',
                'message': f"Successfully refreshed live quote data from Yahoo Finance for {count} security(ies).",
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def action_fetch_all_quotes(self):
        """Fetches live quotes for all active securities."""
        securities = self.search([])
        return securities.action_fetch_quote()

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

    @api.model
    def _auto_refresh_stale_quotes(self):
        """Auto-refreshes securities missing today's price."""
        today = fields.Date.context_today(self)
        securities = self.search([('symbol', '!=', False)])
        updated_any = False
        for sec in securities:
            has_today_price = self.env['moneta.security.price'].search_count([
                ('security_id', '=', sec.id),
                ('price_date', '=', today),
            ])
            if not has_today_price:
                try:
                    info = sec._lookup_symbol_info(sec.symbol)
                    price = info.get('price')
                    if price:
                        self.env['moneta.security.price'].create({
                            'security_id': sec.id,
                            'price_date': today,
                            'price_close': price,
                            'source': 'yahoo',
                        })
                        sec.write({
                            'day_change': info.get('day_change', 0.0),
                            'day_change_percent': info.get('day_change_percent', 0.0),
                            'fifty_two_week_high': info.get('fifty_two_week_high', False),
                            'fifty_two_week_low': info.get('fifty_two_week_low', False),
                            'day_volume': info.get('day_volume', 0.0),
                        })
                        updated_any = True
                except Exception:
                    continue
        if updated_any:
            self.invalidate_model()

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        try:
            self._auto_refresh_stale_quotes()
        except Exception:
            pass
        return super().web_search_read(
            domain=domain, specification=specification, offset=offset,
            limit=limit, order=order, count_limit=count_limit
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            self._auto_refresh_stale_quotes()
        except Exception:
            pass
        return super().search_read(
            domain=domain, fields=fields, offset=offset,
            limit=limit, order=order
        )


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

    @api.constrains('security_id', 'weight')
    def _check_allocation_total(self):
        # The parent security's own constraint only fires when the security
        # record is written; creating/updating allocation lines directly must
        # enforce the same 100% ceiling here.
        for rec in self:
            if rec.security_id:
                total = sum(rec.security_id.allocation_ids.mapped('weight'))
                if total > 100.001:
                    raise ValidationError(
                        f"Total allocation weights for security '{rec.security_id.name}' cannot exceed 100% (currently {total:.2f}%)."
                    )


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
        # A new price changes every holding's market value; drop the ORM cache so
        # stored valuations (market_value / cost_basis / unrealized_gain)
        # recompute on next read instead of showing a stale figure. The monthly
        # account snapshots are rebuilt below per affected account.
        self.env['moneta.holding'].invalidate_model()
        for price in prices:
            price._rebuild_holding_accounts()
        return prices

    def write(self, vals):
        res = super().write(vals)
        self.env['moneta.holding'].invalidate_model()
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

    @api.depends('action', 'security_id.symbol', 'security_id.name', 'quantity', 'trade_date')
    def _compute_display_name(self):
        for tx in self:
            action_str = (tx.action or 'trade').upper()
            sym = tx.security_id.symbol or tx.security_id.name or 'Asset'
            qty = f"{tx.quantity:g}" if tx.quantity else "0"
            date_str = str(tx.trade_date) if tx.trade_date else ""
            tx.display_name = f"{action_str} {qty} {sym} ({date_str})"


    action = fields.Selection([
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('dividend', 'Dividend'),
        ('interest', 'Interest'),
        ('split', 'Split'),
    ], string='Action', required=True, default='buy')

    account_id = fields.Many2one(
        'moneta.account', string='Brokerage Account',
        domain="[('account_type', 'in', ('brokerage', 'retirement', 'crypto'))]",
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

    state = fields.Selection([
        ('unreconciled', 'Unreconciled'),
        ('cleared', 'Cleared'),
        ('reconciled', 'Reconciled'),
        ('void', 'Void'),
    ], string='Status', default='unreconciled', required=True, index=True)
    reconciled_date = fields.Date(string='Reconciled Date')

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

    @api.depends('action', 'quantity', 'price', 'commission', 'state')
    def _compute_total_amount(self):
        for tx in self:
            if tx.state == 'void':
                tx.total_amount = 0.0
                continue
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

    def action_toggle_cleared(self):
        """Quicken-style 1-click status cycle for investment transactions:
        unreconciled -> cleared -> reconciled -> unreconciled."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == 'unreconciled':
                rec.write({'state': 'cleared'})
            elif rec.state == 'cleared':
                rec.write({'state': 'reconciled', 'reconciled_date': rec.reconciled_date or today})
            elif rec.state == 'reconciled':
                rec.write({'state': 'unreconciled', 'reconciled_date': False})

    def action_clear(self):
        self.write({'state': 'cleared'})

    def action_reconcile(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.write({'state': 'reconciled', 'reconciled_date': rec.reconciled_date or today})

    def action_unreconcile(self):
        self.write({'state': 'unreconciled', 'reconciled_date': False})

    def action_void(self):
        """Mark as void: removes from holdings, returns, and net worth."""
        for rec in self:
            rec.write({'state': 'void', 'reconciled_date': False})
            if rec.linked_transaction_id and rec.linked_transaction_id.state != 'void':
                rec.linked_transaction_id.write({'state': 'void'})

    def action_unvoid(self):
        """Un-void transaction."""
        for rec in self:
            rec.write({'state': 'unreconciled'})
            if rec.linked_transaction_id and rec.linked_transaction_id.state == 'void':
                rec.linked_transaction_id.write({'state': 'unreconciled'})

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
            ('state', '!=', 'void'),
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
        if account.account_type not in ('brokerage', 'retirement', 'crypto'):
            raise ValidationError("Investment transactions require a brokerage account.")
        projected = self._projected_quantity(account, security_id, exclude_ids, extra_sell)
        if projected < -1e-8:
            raise ValidationError(
                "Cannot sell more than the held quantity (held: %s)." % round(max(projected + extra_sell, 0.0), 8)
            )

    def _set_realized_gain(self, value):
        """Store realized_gain honouring the null-propagation contract.

        The ORM coerces False/None to 0.0 for numeric columns, so an unknown
        gain (NULL = unknown, never 0) must be written with raw SQL.
        """
        if value is False:
            self.env.cr.execute(
                "UPDATE moneta_investment_transaction SET realized_gain = NULL WHERE id = %s",
                (self.id,),
            )
            self.invalidate_recordset()
        else:
            self.write({'realized_gain': value})

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

    @api.depends('security_id.symbol', 'security_id.name', 'account_id.name', 'quantity')
    def _compute_display_name(self):
        for rec in self:
            sym = rec.security_id.symbol or rec.security_id.name or 'Holding'
            acc = rec.account_id.name or 'Account'
            qty = f"{rec.quantity:g}" if rec.quantity else "0"
            rec.display_name = f"{sym} ({qty} shs) · {acc}"


    account_id = fields.Many2one('moneta.account', string='Investment Account', domain="[('account_type', 'in', ('brokerage', 'retirement', 'crypto'))]", required=True, ondelete='cascade')
    security_id = fields.Many2one('moneta.security', string='Security', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='security_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env['moneta.holding'].invalidate_model()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env['moneta.holding'].invalidate_model()
        return res


    # Derived from investment transactions (average cost, commission in basis).
    # NULL average_cost = unknown cost basis (null propagation), never 0.
    quantity = fields.Float(string='Shares / Units', digits=(16, 8), default=0.0)
    average_cost = fields.Monetary(string='Average Cost / Unit')

    current_price = fields.Monetary(related='security_id.current_price', string='Current Price', readonly=True)
    # Odoo coerces every numeric assignment through float(value or 0.0), so a
    # Monetary field cannot itself express 'unknown' -- the null propagation
    # contract is carried by explicit known-flags (booleans never coerce).
    # Consumers treat the value as unknown when the flag is False.
    price_known = fields.Boolean(string='Price Known', compute='_compute_valuation_flags')
    basis_known = fields.Boolean(string='Cost Basis Known', compute='_compute_valuation_flags')
    market_value = fields.Monetary(string='Market Value', compute='_compute_valuation', store=True, aggregator='sum')
    cost_basis = fields.Monetary(string='Cost Basis', compute='_compute_valuation', store=True, aggregator='sum')
    unrealized_gain = fields.Monetary(string='Unrealized Gain / Loss', compute='_compute_valuation', store=True, aggregator='sum')
    unrealized_gain_percent = fields.Float(string='Gain / Loss (%)', compute='_compute_valuation_flags', digits=(5, 2))
    asset_class = fields.Selection(related='security_id.asset_class', string='Asset Class', store=True)
    symbol = fields.Char(related='security_id.symbol', string='Symbol', store=True)

    # Advanced Return & Dividend Analytics (Wealthfolio Style)
    annual_dividend_income = fields.Monetary(string='Est. Annual Dividends', compute='_compute_valuation', store=True, aggregator='sum')
    dividend_yield = fields.Float(string='Dividend Yield (%)', compute='_compute_valuation_flags', digits=(5, 2))
    twr_percent = fields.Float(string='TWR (%)', compute='_compute_returns', digits=(5, 2), help='Time-Weighted Return (Modified Dietz): period return with cash-flow timing weight.')
    mwr_percent = fields.Float(string='MWR / IRR (%)', compute='_compute_returns', digits=(5, 2), help='Money-Weighted Return: annualized internal rate of return (XIRR) on dated cash flows.')

    # MS Money Portfolio Metrics (Track 2.3)
    day_gain_loss = fields.Monetary(string="Today's Gain / Loss", compute='_compute_holding_market_metrics')
    day_gain_loss_percent = fields.Float(string="Today's Gain (%)", compute='_compute_holding_market_metrics', digits=(5, 2))
    percent_of_portfolio = fields.Float(string='% of Portfolio', compute='_compute_portfolio_weights', digits=(5, 2))
    fifty_two_week_high = fields.Monetary(related='security_id.fifty_two_week_high', readonly=True)
    fifty_two_week_low = fields.Monetary(related='security_id.fifty_two_week_low', readonly=True)
    pe_ratio = fields.Float(related='security_id.pe_ratio', readonly=True)
    market_cap = fields.Monetary(related='security_id.market_cap', readonly=True)
    beta = fields.Float(related='security_id.beta', readonly=True)

    @api.depends('quantity', 'security_id.day_change', 'security_id.day_change_percent')
    def _compute_holding_market_metrics(self):
        for h in self:
            qty = h.quantity or 0.0
            day_chg = h.security_id.day_change or 0.0
            h.day_gain_loss = round(qty * day_chg, 4)
            h.day_gain_loss_percent = h.security_id.day_change_percent or 0.0

    def _compute_portfolio_weights(self):
        for h in self:
            total_account_mv = sum(self.search([('account_id', '=', h.account_id.id)]).mapped('market_value'))
            if total_account_mv > 0 and h.market_value:
                h.percent_of_portfolio = round((h.market_value / total_account_mv) * 100.0, 2)
            else:
                h.percent_of_portfolio = 0.0

    # Stored related owner so the per-user record rule resolves to the account owner.
    user_id = fields.Many2one('res.users', related='account_id.user_id', store=True, index=True)




    def action_refresh_all_quotes(self):
        """Fetch fresh live quotes for all securities in portfolio and recompute gains."""
        holdings = self.search([])
        securities = holdings.mapped('security_id')
        if not securities:
            securities = self.env['moneta.security'].search([('symbol', '!=', False)])
        
        updated = 0
        for sec in securities:
            if not sec.symbol:
                continue
            info = sec._lookup_symbol_info(sec.symbol)
            price = info.get('price')
            if price:
                today = fields.Date.context_today(self)
                existing = self.env['moneta.security.price'].search([
                    ('security_id', '=', sec.id),
                    ('price_date', '=', today),
                ], limit=1)
                if existing:
                    existing.write({'price_close': price, 'source': 'yahoo'})
                else:
                    self.env['moneta.security.price'].create({
                        'security_id': sec.id,
                        'price_date': today,
                        'price_close': price,
                        'source': 'yahoo',
                    })
                updated += 1

        # Invalidate holding cache so all live quotes & gains recalculate
        self.env['moneta.holding'].invalidate_model()
        self.env['moneta.security'].invalidate_model()
        accounts = holdings.mapped('account_id')
        for acc in accounts:
            self.env['moneta.account.balance.monthly']._rebuild_for_account(acc)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_fetch_quote(self):
        """Fetch live quote for this holding's security from Yahoo Finance."""
        self.ensure_one()
        if self.security_id:
            res = self.security_id.action_fetch_quote()
            self._compute_valuation()
            self._compute_holding_market_metrics()
            return res
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def _auto_refresh_stale_quotes(self):
        """Automatically updates stale quotes from Yahoo Finance when viewing holdings."""
        today = fields.Date.context_today(self)
        holdings = self.search([('quantity', '>', 0)])
        securities = holdings.mapped('security_id').filtered(lambda s: bool(s.symbol))
        if not securities:
            return

        updated_any = False
        for sec in securities:
            has_today_price = self.env['moneta.security.price'].search_count([
                ('security_id', '=', sec.id),
                ('price_date', '=', today),
            ])
            if not has_today_price:
                try:
                    info = sec._lookup_symbol_info(sec.symbol)
                    price = info.get('price')
                    if price:
                        self.env['moneta.security.price'].create({
                            'security_id': sec.id,
                            'price_date': today,
                            'price_close': price,
                            'source': 'yahoo',
                        })
                        sec.write({
                            'day_change': info.get('day_change', 0.0),
                            'day_change_percent': info.get('day_change_percent', 0.0),
                            'fifty_two_week_high': info.get('fifty_two_week_high', False),
                            'fifty_two_week_low': info.get('fifty_two_week_low', False),
                            'day_volume': info.get('day_volume', 0.0),
                        })
                        updated_any = True
                except Exception:
                    continue

        if updated_any:
            self.invalidate_model()
            securities.invalidate_model()

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        try:
            self._auto_refresh_stale_quotes()
        except Exception:
            pass
        return super().web_search_read(
            domain=domain, specification=specification, offset=offset,
            limit=limit, order=order, count_limit=count_limit
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            self._auto_refresh_stale_quotes()
        except Exception:
            pass
        return super().search_read(
            domain=domain, fields=fields, offset=offset,
            limit=limit, order=order
        )

    @api.depends('quantity', 'average_cost', 'current_price')
    def _compute_valuation(self):
        # Stored valuation fields only. The known-flags and derived percents
        # live in _compute_valuation_flags: Odoo 18 warns when one compute
        # method mixes stored and non-stored fields (accessing the non-stored
        # ones would recompute and rewrite the stored ones).
        for holding in self:
            basis_known = not _field_is_null(self.env, self, holding.id, 'average_cost')
            qty = holding.quantity or 0.0
            price = holding.current_price or 0.0
            avg = holding.average_cost or 0.0
            holding.market_value = round(qty * price, 4)
            holding.cost_basis = round(qty * avg, 4) if basis_known else 0.0
            if basis_known:
                holding.unrealized_gain = round(holding.market_value - holding.cost_basis, 4)
            else:
                holding.unrealized_gain = 0.0

            # Dividend analytics. TWR/MWR are computed separately by
            # _compute_returns (they need the dated trade cash flows, which are
            # too costly to rebuild on every list-view read).
            div_rate = float(holding.security_id.annual_dividend_rate or 0.0)
            holding.annual_dividend_income = round(qty * div_rate, 4)

    @api.depends('quantity', 'average_cost', 'current_price',
                 'market_value', 'cost_basis', 'unrealized_gain',
                 'annual_dividend_income')
    def _compute_valuation_flags(self):
        for holding in self:
            price_known = self.env['moneta.security.price'].search_count([
                ('security_id', '=', holding.security_id.id),
            ]) > 0
            basis_known = not _field_is_null(self.env, self, holding.id, 'average_cost')
            holding.price_known = price_known
            holding.basis_known = basis_known
            if basis_known and holding.cost_basis > 0:
                holding.unrealized_gain_percent = round(((holding.unrealized_gain / holding.cost_basis) * 100.0), 2)
            else:
                holding.unrealized_gain_percent = 0.0
            holding.dividend_yield = holding.security_id.dividend_yield_pct or ((holding.annual_dividend_income / holding.market_value * 100.0) if holding.market_value > 0 else 0.0)

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
            ('state', '!=', 'void'),
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
                    elif qty > 0:
                        avg = round(
                            ((tx.quantity or 0.0) * (tx.price or 0.0) + (tx.commission or 0.0)) / qty,
                            8,
                        )
                    else:
                        avg = 0.0
                elif qty > 0:
                    total_cost = (qty_before * (avg or 0.0)) + (tx.quantity or 0.0) * (tx.price or 0.0) + (tx.commission or 0.0)
                    avg = round(total_cost / qty, 8)
                else:
                    avg = 0.0
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
                self.env['moneta.investment.transaction'].browse(tx.id)._set_realized_gain(realized)
            elif tx.action == 'split':
                ratio = tx.quantity or 1.0
                qty *= ratio
                if avg is not False:
                    avg = round((avg or 0.0) / ratio, 8)
            elif tx.action in ('dividend', 'interest'):
                # Realized gain is the amount; the cash entry is a separate
                # transaction created by the investment record itself.
                self.env['moneta.investment.transaction'].browse(tx.id)._set_realized_gain(tx.total_amount)
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
        holding.write({'quantity': round(qty, 8)})
        if avg is False:
            # The ORM coerces False/None to 0.0 for numeric columns
            # (Float.convert_to_column), so an unknown basis cannot be expressed
            # through a normal write -- store NULL directly to honour the
            # null-propagation contract (NULL = unknown, never 0).
            self.env.cr.execute(
                "UPDATE moneta_holding SET average_cost = NULL WHERE id = %s",
                (holding.id,),
            )
            holding.invalidate_recordset()
        else:
            holding.write({'average_cost': avg})

    def _get_return_cashflows(self):
        """Dated cash flows for this holding's investment transactions, fetched
        in a single query (avoids one _field_is_null round-trip per trade).

        Returns ``(xirr_cfs, dietz_cfs, has_unknown)``:

          * ``xirr_cfs`` -- investor convention (buys negative, sells / dividends
            positive); the terminal market value is appended by the caller.
          * ``dietz_cfs`` -- portfolio convention (contributions positive,
            withdrawals negative); the end value is passed separately.
          * ``has_unknown`` -- a buy or sell carried a NULL price, so the cost
            or proceeds are unknowable and the returns cannot be computed.

        Splits carry no cash flow and are skipped.
        """
        acc_id = self.account_id.id
        sec_id = self.security_id.id
        if not isinstance(acc_id, int) or not isinstance(sec_id, int):
            return [], [], True
        self.env.cr.execute(
            "SELECT action, trade_date, quantity, price, commission "
            "FROM moneta_investment_transaction "
            "WHERE account_id = %s AND security_id = %s AND state <> 'void' "
            "ORDER BY trade_date, id",
            (acc_id, sec_id),
        )
        xirr, dietz = [], []
        unknown = False
        for action, tdate, qty, price, comm in self.env.cr.fetchall():
            if tdate is None:
                continue
            qty = qty or 0.0
            comm = comm or 0.0
            if action == 'buy':
                if price is None:
                    unknown = True
                    continue
                amt = qty * price + comm
                xirr.append((tdate, -amt))
                dietz.append((tdate, +amt))
            elif action == 'sell':
                if price is None:
                    unknown = True
                    continue
                amt = qty * price - comm
                xirr.append((tdate, +amt))
                dietz.append((tdate, -amt))
            elif action in ('dividend', 'interest'):
                if price is None:
                    continue  # unknown dividend amount: skip, don't poison
                amt = (qty or 1.0) * price
                xirr.append((tdate, +amt))
                dietz.append((tdate, -amt))
            # 'split' carries no cash flow
        return xirr, dietz, unknown

    @api.depends('quantity', 'average_cost', 'current_price')
    def _compute_returns(self):
        """Time-Weighted (Modified Dietz) and Money-Weighted (XIRR) returns.

        Both need the dated trade cash flows, so they live in a dedicated method
        rather than ``_compute_valuation`` -- a list view that does not display
        TWR / MWR then pays nothing for them.

        Falls back to the simple unrealized-gain percent whenever a real return
        cannot be computed: unknown cost basis, unknown current price while
        shares are still held, a buy / sell with a NULL price, or insufficient
        cash flows (no sign change for XIRR, no invested capital for Dietz).
        """
        today = fields.Date.context_today(self)
        # Touch the valuation fields so _compute_valuation runs once for the
        # whole batch and the per-holding values are cached for the loop.
        # Use mapped(), not attribute access: self is a multi-record set here
        # (a list view computes TWR / MWR for all holdings at once) and
        # Field.__get__ raises "Expected singleton" on multi-record access.
        self.mapped('market_value')
        self.mapped('cost_basis')
        self.mapped('basis_known')
        self.mapped('price_known')
        self.mapped('unrealized_gain_percent')
        for holding in self:
            fallback = holding.unrealized_gain_percent or 0.0
            qty = holding.quantity or 0.0
            xirr_cfs, dietz_cfs, unknown = holding._get_return_cashflows()
            # Shares still held need a known basis AND a current price to value
            # the terminal position; without either the return is unknowable.
            if unknown or (qty > 0 and (not holding.basis_known or not holding.price_known)):
                holding.twr_percent = fallback
                holding.mwr_percent = fallback
                continue
            if not xirr_cfs:
                holding.twr_percent = fallback
                holding.mwr_percent = fallback
                continue
            mv = float(holding.market_value or 0.0)
            if qty > 0:
                # Terminal market value as the final inflow / end value, today.
                if mv <= 0:
                    holding.twr_percent = fallback
                    holding.mwr_percent = fallback
                    continue
                xirr_cfs.append((today, mv))
                end_value, end_date = mv, today
            else:
                # Fully sold out: the last trade is the terminal cash flow, and
                # the holding period ends there (not today, so post-sell idle time
                # does not dilute the return).
                end_date = max(d for d, _ in xirr_cfs)
                end_value = 0.0
            mwr = _xirr(xirr_cfs)
            twr = _modified_dietz(dietz_cfs, end_value, end_date)
            holding.mwr_percent = round(mwr * 100.0, 2) if mwr is not None else fallback
            holding.twr_percent = round(twr * 100.0, 2) if twr is not None else fallback