# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaLhdnTaxPlanner(models.Model):
    _name = 'moneta.lhdn.tax.planner'
    _description = 'Malaysia LHDN Personal Income Tax Planner (Borang BE)'
    _order = 'tax_year desc, id desc'

    name = fields.Char(string='Tax Assessment Name', compute='_compute_name', store=True)
    tax_year = fields.Selection([
        ('2024', 'Year of Assessment 2024'),
        ('2025', 'Year of Assessment 2025'),
        ('2026', 'Year of Assessment 2026'),
        ('2027', 'Year of Assessment 2027'),
    ], string='Assessment Year (YA)', default='2025', required=True)

    user_id = fields.Many2one('res.users', string='Taxpayer', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    # --- Gross Incomes ---
    annual_employment_income = fields.Monetary(string='Employment Gross Income (EA Form)', default=0.0)
    annual_business_income = fields.Monetary(string='Business / Freelance Net Income', default=0.0)
    annual_rental_net_income = fields.Monetary(string='Net Rental Real Estate Income', default=0.0)
    annual_other_taxable_income = fields.Monetary(string='Other Taxable Income (Royalties/Annuities)', default=0.0)
    gross_total_income = fields.Monetary(string='Total Gross Income', compute='_compute_lhdn_tax', store=True)

    # --- LHDN Statutory Tax Reliefs (Pelepasan Cukai) ---
    relief_individual = fields.Monetary(string='Individual & Dependent Relatives (RM9,000)', default=9000.0, readonly=True)
    relief_parent_medical = fields.Monetary(string='Medical Expenses / Dental for Parents (Max RM8,000)', default=0.0)
    relief_disabled_individual = fields.Monetary(string='Disabled Individual (RM6,000)', default=0.0)
    relief_education_self = fields.Monetary(string='Self Education Fees - Master/PhD/Upskilling (Max RM7,000)', default=0.0)
    relief_medical_expenses = fields.Monetary(string='Medical Expenses for Self/Spouse/Child (Max RM10,000)', default=0.0)
    
    # Lifestyle & Sports Reliefs
    relief_lifestyle = fields.Monetary(string='Lifestyle - Books, PC, Phone, Broadband (Max RM2,500)', default=0.0)
    relief_lifestyle_sports = fields.Monetary(string='Sports Equipment, Facilities & Tournament Fees (Max RM1,000)', default=0.0)
    
    # Family & Education
    relief_breastfeeding_equipment = fields.Monetary(string='Breastfeeding Equipment (Max RM1,000)', default=0.0)
    relief_childcare_fees = fields.Monetary(string='Child Care Fees to Registered TASKA/TADIKA (Max RM3,000)', default=0.0)
    relief_sspn = fields.Monetary(string='SSPN Net Deposit for Child Education (Max RM8,000)', default=0.0)
    
    # Retirement, Insurance & Social Security
    relief_life_insurance = fields.Monetary(string='Life Insurance / Family Takaful (Max RM3,000)', default=0.0)
    relief_epf = fields.Monetary(string='EPF / Approved Retirement Scheme (Max RM4,000)', default=0.0)
    relief_prs = fields.Monetary(string='Private Retirement Scheme (PRS) / Deferred Annuity (Max RM3,000)', default=0.0)
    relief_socso_eis = fields.Monetary(string='SOCSO / EIS Contribution (Max RM350)', default=0.0)
    
    # Green & Tech
    relief_ev_charging = fields.Monetary(string='EV Charging Equipment, Facility & Subscription (Max RM2,500)', default=0.0)

    # Spousal & Children
    relief_spouse = fields.Monetary(string='Spouse Relief (RM4,000 if no income)', default=0.0)
    relief_children_unmarried_under_18 = fields.Integer(string='No. of Unmarried Children (< 18 yrs) [RM2,000 each]', default=0)
    relief_children_higher_education = fields.Integer(string='No. of Children in Higher Education (Uni/Diploma) [RM8,000 each]', default=0)

    total_tax_reliefs = fields.Monetary(string='Total Pelepasan Cukai', compute='_compute_lhdn_tax', store=True)

    # --- Tax Computation Results ---
    chargeable_income = fields.Monetary(string='Chargeable Income (Pendapatan Bercukai)', compute='_compute_lhdn_tax', store=True)
    marginal_tax_bracket_pct = fields.Float(string='Marginal Tax Bracket (%)', compute='_compute_lhdn_tax', store=True, digits=(4, 1))
    gross_tax_payable = fields.Monetary(string='Gross Income Tax Payable', compute='_compute_lhdn_tax', store=True)

    # Tax Rebates (Rebat Cukai)
    tax_rebate_zakat = fields.Monetary(string='Zakat & Fitrah Paid (100% Tax Rebate)', default=0.0)
    tax_rebate_individual = fields.Monetary(string='Individual Rebate (RM400 if Chargeable Income ≤ RM35k)', compute='_compute_lhdn_tax', store=True)
    total_tax_rebates = fields.Monetary(string='Total Tax Rebates', compute='_compute_lhdn_tax', store=True)

    net_tax_payable = fields.Monetary(string='Net Income Tax Payable (Cukai Kena Dibayar)', compute='_compute_lhdn_tax', store=True)
    monthly_pcb_deducted = fields.Monetary(string='Monthly Tax Deductions (PCB) Paid', default=0.0)
    tax_refund_or_payable = fields.Monetary(string='Estimated Tax Refund (+) / Tax Due (-)', compute='_compute_lhdn_tax', store=True)

    optimization_notes = fields.Text(string='LHDN Tax Relief Optimization Tips', compute='_compute_lhdn_tax', store=True)

    @api.depends('tax_year', 'user_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f"LHDN Borang BE YA {rec.tax_year or '2025'} - {rec.user_id.name or 'User'}"

    @api.depends(
        'annual_employment_income', 'annual_business_income', 'annual_rental_net_income', 'annual_other_taxable_income',
        'relief_parent_medical', 'relief_disabled_individual', 'relief_education_self', 'relief_medical_expenses',
        'relief_lifestyle', 'relief_lifestyle_sports', 'relief_breastfeeding_equipment', 'relief_childcare_fees',
        'relief_sspn', 'relief_life_insurance', 'relief_epf', 'relief_prs', 'relief_socso_eis', 'relief_ev_charging',
        'relief_spouse', 'relief_children_unmarried_under_18', 'relief_children_higher_education',
        'tax_rebate_zakat', 'monthly_pcb_deducted'
    )
    def _compute_lhdn_tax(self):
        for rec in self:
            # 1. Total Gross Income
            gross = (float(rec.annual_employment_income or 0.0) +
                     float(rec.annual_business_income or 0.0) +
                     float(rec.annual_rental_net_income or 0.0) +
                     float(rec.annual_other_taxable_income or 0.0))
            rec.gross_total_income = round(gross, 2)

            # 2. Total Reliefs with Statutory Caps
            r_indiv = 9000.0
            r_parent = min(float(rec.relief_parent_medical or 0.0), 8000.0)
            r_disabled = min(float(rec.relief_disabled_individual or 0.0), 6000.0)
            r_edu = min(float(rec.relief_education_self or 0.0), 7000.0)
            r_med = min(float(rec.relief_medical_expenses or 0.0), 10000.0)
            r_life = min(float(rec.relief_lifestyle or 0.0), 2500.0)
            r_sports = min(float(rec.relief_lifestyle_sports or 0.0), 1000.0)
            r_breast = min(float(rec.relief_breastfeeding_equipment or 0.0), 1000.0)
            r_childcare = min(float(rec.relief_childcare_fees or 0.0), 3000.0)
            r_sspn = min(float(rec.relief_sspn or 0.0), 8000.0)
            
            # Life Insurance + EPF (Combined max RM7,000: Life max RM3,000, EPF max RM4,000)
            r_life_ins = min(float(rec.relief_life_insurance or 0.0), 3000.0)
            r_epf = min(float(rec.relief_epf or 0.0), 4000.0)
            
            r_prs = min(float(rec.relief_prs or 0.0), 3000.0)
            r_socso = min(float(rec.relief_socso_eis or 0.0), 350.0)
            r_ev = min(float(rec.relief_ev_charging or 0.0), 2500.0)
            r_spouse = min(float(rec.relief_spouse or 0.0), 4000.0)
            
            r_child_std = (rec.relief_children_unmarried_under_18 or 0) * 2000.0
            r_child_uni = (rec.relief_children_higher_education or 0) * 8000.0

            total_reliefs = (r_indiv + r_parent + r_disabled + r_edu + r_med + r_life + r_sports +
                             r_breast + r_childcare + r_sspn + r_life_ins + r_epf + r_prs +
                             r_socso + r_ev + r_spouse + r_child_std + r_child_uni)
            rec.total_tax_reliefs = round(total_reliefs, 2)

            # 3. Chargeable Income
            chargeable = max(gross - total_reliefs, 0.0)
            rec.chargeable_income = round(chargeable, 2)

            # 4. Malaysian Resident Tax Brackets (YA 2024 - 2026)
            # 0 - 5,000: 0%
            # 5,001 - 20,000: 1%
            # 20,001 - 35,000: 3%
            # 35,001 - 50,000: 6%
            # 50,001 - 70,000: 11%
            # 70,001 - 100,000: 19%
            # 100,001 - 400,000: 25%
            # 400,001 - 600,000: 26%
            # 600,001 - 2,000,000: 28%
            # > 2,000,000: 30%
            tax = 0.0
            rate = 0.0

            if chargeable <= 5000:
                tax = 0.0
                rate = 0.0
            elif chargeable <= 20000:
                tax = (chargeable - 5000) * 0.01
                rate = 1.0
            elif chargeable <= 35000:
                tax = 150.0 + (chargeable - 20000) * 0.03
                rate = 3.0
            elif chargeable <= 50000:
                tax = 600.0 + (chargeable - 35000) * 0.06
                rate = 6.0
            elif chargeable <= 70000:
                tax = 1500.0 + (chargeable - 50000) * 0.11
                rate = 11.0
            elif chargeable <= 100000:
                tax = 3700.0 + (chargeable - 70000) * 0.19
                rate = 19.0
            elif chargeable <= 400000:
                tax = 9400.0 + (chargeable - 100000) * 0.25
                rate = 25.0
            elif chargeable <= 600000:
                tax = 84400.0 + (chargeable - 400000) * 0.26
                rate = 26.0
            elif chargeable <= 2000000:
                tax = 136400.0 + (chargeable - 600000) * 0.28
                rate = 28.0
            else:
                tax = 528400.0 + (chargeable - 2000000) * 0.30
                rate = 30.0

            rec.marginal_tax_bracket_pct = rate
            rec.gross_tax_payable = round(tax, 2)

            # 5. Rebates
            rebate_indiv = 400.0 if (chargeable <= 35000 and chargeable > 0) else 0.0
            zakat = float(rec.tax_rebate_zakat or 0.0)
            rec.tax_rebate_individual = rebate_indiv
            rec.total_tax_rebates = round(rebate_indiv + zakat, 2)

            net_tax = max(tax - (rebate_indiv + zakat), 0.0)
            rec.net_tax_payable = round(net_tax, 2)

            # 6. PCB & Refund
            pcb = float(rec.monthly_pcb_deducted or 0.0)
            rec.tax_refund_or_payable = round(pcb - net_tax, 2)

            # 7. Smart Optimization Suggestions
            tips = []
            if r_sspn < 8000.0:
                tips.append(f"💡 SSPN Education Savings: You have utilized RM{r_sspn:,.2f} out of RM8,000. Deposit RM{8000.0 - r_sspn:,.2f} more to save up to RM{(8000.0 - r_sspn) * (rate / 100.0):,.2f} in taxes.")
            if r_prs < 3000.0:
                tips.append(f"💡 PRS Retirement Scheme: You have utilized RM{r_prs:,.2f} out of RM3,000. Contribute RM{3000.0 - r_prs:,.2f} more to save up to RM{(3000.0 - r_prs) * (rate / 100.0):,.2f} in taxes.")
            if r_life < 2500.0:
                tips.append(f"💡 Lifestyle Relief: RM{2500.0 - r_life:,.2f} remaining for books, computers, smartphones, home broadband, or gym.")
            if r_sports < 1000.0:
                tips.append(f"💡 Sports Lifestyle Relief: RM{1000.0 - r_sports:,.2f} remaining for sports gear & tournament fees.")
            if zakat > 0:
                tips.append(f"✅ Zakat Rebate: RM{zakat:,.2f} 1-to-1 direct tax rebate applied.")

            rec.optimization_notes = "\n".join(tips) if tips else "🎉 Congratulations! You have fully optimized all major LHDN tax reliefs."
