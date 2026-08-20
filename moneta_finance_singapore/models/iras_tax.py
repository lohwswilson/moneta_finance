# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaIRASTaxPlanner(models.Model):
    _name = 'moneta.iras.tax.planner'
    _description = 'Singapore IRAS Personal Income Tax Relief & Optimization Engine'
    _order = 'tax_year desc, id desc'

    name = fields.Char(string='Tax Assessment Name', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    tax_year = fields.Integer(string='Income Year', default=lambda self: fields.Date.today().year, required=True)
    year_of_assessment = fields.Integer(string='Year of Assessment (YA)', compute='_compute_ya', store=True)
    
    tax_residency = fields.Selection([
        ('tax_resident', 'Singapore Tax Resident (Progressive 0% - 24%)'),
        ('non_resident', 'Non-Resident Individual (Flat 15% or 24%)'),
    ], string='Tax Residency Status', default='tax_resident', required=True)

    # 1. Income Sources
    annual_employment_income = fields.Monetary(string='Gross Employment Salary', required=True, default=120000.0)
    annual_bonus = fields.Monetary(string='Bonuses & AWS', default=20000.0)
    trade_business_income = fields.Monetary(string='Trade / Freelance / Business Net Income', default=0.0)
    rental_net_income = fields.Monetary(string='Net Rental Property Income', default=0.0)
    other_taxable_income = fields.Monetary(string='Other Taxable Income (Director Fees, etc.)', default=0.0)

    gross_total_income = fields.Monetary(string='Total Assessable Income', compute='_compute_income_and_reliefs', store=True)

    # 2. Personal Tax Reliefs
    age_group = fields.Selection([
        ('under_55', 'Below 55 Years Old'),
        ('55_to_59', '55 to 59 Years Old'),
        ('60_and_above', '60 Years Old and Above'),
    ], string='Age Group', default='under_55', required=True)

    earned_income_relief = fields.Monetary(string='Earned Income Relief (EIR)', compute='_compute_income_and_reliefs', store=True)
    cpf_employee_relief = fields.Monetary(string='CPF Employee Mandatory Relief (Max $20,400)', default=20400.0)
    
    rstu_self_relief = fields.Monetary(string='CPF Cash Top-Up (RSTU Self - Max $8,000)', default=8000.0)
    rstu_family_relief = fields.Monetary(string='CPF Cash Top-Up (RSTU Loved Ones - Max $8,000)', default=0.0)
    srs_contribution_relief = fields.Monetary(string='SRS Contribution Relief (Max $15,300 / $35,700)', default=15300.0)

    nsman_relief_type = fields.Selection([
        ('none', 'Not Applicable ($0)'),
        ('general', 'NSman General ($1,500)'),
        ('active_ict_ippt', 'Active NSman with ICT/IPPT ($3,000)'),
        ('key_appointment', 'Key Appointment Holder ($3,500 / $5,000)'),
    ], string='NSman Relief Category', default='active_ict_ippt')
    nsman_relief_amount = fields.Monetary(string='NSman Relief', compute='_compute_income_and_reliefs', store=True)
    nsman_parent_wife_relief = fields.Monetary(string='NSman Wife / Parent Relief ($750)', default=0.0)

    qualifying_child_count = fields.Integer(string='Qualifying Children Count ($4,000/child)', default=1)
    child_relief_amount = fields.Monetary(string='Qualifying Child Relief (QCR)', compute='_compute_income_and_reliefs', store=True)

    parent_relief_type = fields.Selection([
        ('none', 'No Parent Relief Claimed'),
        ('non_staying', 'Parent Relief - Non-Staying ($5,500)'),
        ('staying', 'Parent Relief - Living with Parent ($9,000)'),
        ('handicapped', 'Handicapped Parent Relief ($14,000)'),
    ], string='Parent Relief Category', default='none')
    parent_relief_amount = fields.Monetary(string='Parent Relief', compute='_compute_income_and_reliefs', store=True)

    course_fees_relief = fields.Monetary(string='Course Fees Relief (Max $5,500)', default=0.0)
    life_insurance_relief = fields.Monetary(string='Life Insurance Relief (Max $5,000)', default=0.0)

    charitable_donations = fields.Monetary(string='Charitable Donations to IPCs ($)', default=1000.0)
    donation_deduction_amount = fields.Monetary(string='250% Donation Tax Deduction', compute='_compute_income_and_reliefs', store=True)

    # Relief Cap & Chargeable Income
    personal_relief_cap = fields.Monetary(string='Personal Relief Cap', default=80000.0)
    total_personal_reliefs_pre_cap = fields.Monetary(string='Total Personal Reliefs Claimed', compute='_compute_income_and_reliefs', store=True)
    effective_reliefs_applied = fields.Monetary(string='Effective Deductions Applied', compute='_compute_income_and_reliefs', store=True)
    remaining_cap_to_80k = fields.Monetary(string='Remaining Headroom to $80k Cap', compute='_compute_income_and_reliefs', store=True)

    chargeable_income = fields.Monetary(string='Chargeable Income ($)', compute='_compute_tax_liability', store=True)
    marginal_tax_bracket_pct = fields.Float(string='Marginal Tax Bracket (%)', compute='_compute_tax_liability', store=True, digits=(5, 1))
    gross_tax_payable = fields.Monetary(string='Gross Tax Payable ($)', compute='_compute_tax_liability', store=True)
    personal_tax_rebate = fields.Monetary(string='Personal Tax Rebate', default=0.0)
    net_tax_payable = fields.Monetary(string='Estimated Net Tax Payable ($)', compute='_compute_tax_liability', store=True)
    effective_tax_rate_pct = fields.Float(string='Effective Tax Rate (%)', compute='_compute_tax_liability', store=True, digits=(5, 2))

    # Optimization Advisory
    optimization_advisory = fields.Html(string='Year-End Tax Optimization Advisory', compute='_compute_tax_advisory', store=True)
    notes = fields.Text(string='Tax Planning Notes')

    @api.depends('tax_year')
    def _compute_name(self):
        for rec in self:
            rec.name = f"IRAS Tax Plan {rec.tax_year} (YA {rec.tax_year + 1})"

    @api.depends('tax_year')
    def _compute_ya(self):
        for rec in self:
            rec.year_of_assessment = (rec.tax_year or date.today().year) + 1

    @api.depends('annual_employment_income', 'annual_bonus', 'trade_business_income', 'rental_net_income',
                 'other_taxable_income', 'age_group', 'cpf_employee_relief', 'rstu_self_relief',
                 'rstu_family_relief', 'srs_contribution_relief', 'nsman_relief_type', 'nsman_parent_wife_relief',
                 'qualifying_child_count', 'parent_relief_type', 'course_fees_relief', 'life_insurance_relief',
                 'charitable_donations', 'personal_relief_cap')
    def _compute_income_and_reliefs(self):
        for rec in self:
            # 1. Total assessable income
            gross = (
                (rec.annual_employment_income or 0.0) +
                (rec.annual_bonus or 0.0) +
                (rec.trade_business_income or 0.0) +
                (rec.rental_net_income or 0.0) +
                (rec.other_taxable_income or 0.0)
            )
            rec.gross_total_income = round(gross, 2)

            # 2. Earned Income Relief
            if rec.age_group == '60_and_above':
                rec.earned_income_relief = 8000.0
            elif rec.age_group == '55_to_59':
                rec.earned_income_relief = 6000.0
            else:
                rec.earned_income_relief = 1000.0

            # 3. NSman relief
            if rec.nsman_relief_type == 'key_appointment':
                ns_val = 5000.0
            elif rec.nsman_relief_type == 'active_ict_ippt':
                ns_val = 3000.0
            elif rec.nsman_relief_type == 'general':
                ns_val = 1500.0
            else:
                ns_val = 0.0
            rec.nsman_relief_amount = ns_val

            # 4. Child relief ($4,000 per child)
            rec.child_relief_amount = max(rec.qualifying_child_count or 0, 0) * 4000.0

            # 5. Parent relief
            if rec.parent_relief_type == 'handicapped':
                p_val = 14000.0
            elif rec.parent_relief_type == 'staying':
                p_val = 9000.0
            elif rec.parent_relief_type == 'non_staying':
                p_val = 5500.0
            else:
                p_val = 0.0
            rec.parent_relief_amount = p_val

            # 6. Donation 250% deduction
            don_ded = (rec.charitable_donations or 0.0) * 2.5
            rec.donation_deduction_amount = round(don_ded, 2)

            # 7. Sum of personal reliefs (subject to $80k cap)
            # Note: Donations to IPCs are 250% deductions and not subject to the $80k personal relief cap.
            personal_sum = (
                rec.earned_income_relief +
                min(rec.cpf_employee_relief or 0.0, 20400.0) +
                min(rec.rstu_self_relief or 0.0, 8000.0) +
                min(rec.rstu_family_relief or 0.0, 8000.0) +
                (rec.srs_contribution_relief or 0.0) +
                rec.nsman_relief_amount +
                (rec.nsman_parent_wife_relief or 0.0) +
                rec.child_relief_amount +
                rec.parent_relief_amount +
                min(rec.course_fees_relief or 0.0, 5500.0) +
                min(rec.life_insurance_relief or 0.0, 5000.0)
            )
            rec.total_personal_reliefs_pre_cap = round(personal_sum, 2)

            cap = rec.personal_relief_cap or 80000.0
            capped_personal = min(personal_sum, cap)
            rec.remaining_cap_to_80k = max(cap - personal_sum, 0.0)
            rec.effective_reliefs_applied = round(capped_personal + don_ded, 2)

    @api.depends('gross_total_income', 'effective_reliefs_applied', 'tax_residency', 'personal_tax_rebate')
    def _compute_tax_liability(self):
        for rec in self:
            ci = max((rec.gross_total_income or 0.0) - (rec.effective_reliefs_applied or 0.0), 0.0)
            rec.chargeable_income = round(ci, 2)

            if rec.tax_residency == 'non_resident':
                # Non-resident tax rate: flat 15% or 24% (whichever higher)
                tax = ci * 0.24
                rec.marginal_tax_bracket_pct = 24.0
                rec.gross_tax_payable = round(tax, 2)
                rec.net_tax_payable = round(tax, 2)
            else:
                # Singapore Resident Progressive Tax Brackets (YA 2024 - 2026):
                # 0 - 20k: 0%
                # 20k - 30k (10k @ 2%): $200
                # 30k - 40k (10k @ 3.5%): $350 (cum $550)
                # 40k - 80k (40k @ 7%): $2,800 (cum $3,350)
                # 80k - 120k (40k @ 11.5%): $4,600 (cum $7,950)
                # 120k - 160k (40k @ 15%): $6,000 (cum $13,950)
                # 160k - 200k (40k @ 18%): $7,200 (cum $21,150)
                # 200k - 240k (40k @ 19%): $7,600 (cum $28,750)
                # 240k - 280k (40k @ 19.5%): $7,800 (cum $36,550)
                # 280k - 320k (40k @ 20%): $8,000 (cum $44,550)
                # 320k - 500k (180k @ 22%): $39,600 (cum $84,150)
                # 500k - 1m (500k @ 23%): $115,000 (cum $199,150)
                # > 1m @ 24%
                brackets = [
                    (20000.0, 0.0, 0.0),
                    (10000.0, 0.02, 2.0),
                    (10000.0, 0.035, 3.5),
                    (40000.0, 0.07, 7.0),
                    (40000.0, 0.115, 11.5),
                    (40000.0, 0.15, 15.0),
                    (40000.0, 0.18, 18.0),
                    (40000.0, 0.19, 19.0),
                    (40000.0, 0.195, 19.5),
                    (40000.0, 0.20, 20.0),
                    (180000.0, 0.22, 22.0),
                    (500000.0, 0.23, 23.0),
                ]

                tax = 0.0
                rem = ci
                marginal = 0.0

                for band_size, rate, rate_pct in brackets:
                    if rem <= 0:
                        break
                    taxable_in_band = min(rem, band_size)
                    tax += taxable_in_band * rate
                    rem -= taxable_in_band
                    marginal = rate_pct

                if rem > 0:
                    tax += rem * 0.24
                    marginal = 24.0

                rec.marginal_tax_bracket_pct = marginal
                rec.gross_tax_payable = round(tax, 2)
                net = max(tax - (rec.personal_tax_rebate or 0.0), 0.0)
                rec.net_tax_payable = round(net, 2)

            gross_inc = rec.gross_total_income or 0.0
            if gross_inc > 0:
                rec.effective_tax_rate_pct = round((rec.net_tax_payable / gross_inc) * 100.0, 2)
            else:
                rec.effective_tax_rate_pct = 0.0

    @api.depends('remaining_cap_to_80k', 'marginal_tax_bracket_pct', 'rstu_self_relief',
                 'rstu_family_relief', 'srs_contribution_relief', 'charitable_donations')
    def _compute_tax_advisory(self):
        for rec in self:
            m_rate = rec.marginal_tax_bracket_pct or 0.0
            rem_cap = rec.remaining_cap_to_80k or 0.0
            html = []

            html.append("<div class='p-3 bg-light rounded-3'>")
            html.append(f"<h6 class='fw-bold text-primary mb-2'><i class='fa fa-lightbulb-o me-2'></i>Year-End Tax Optimization Strategy (Dec 31 Deadline)</h6>")
            
            if m_rate == 0:
                html.append("<p class='mb-0 text-success'>🎉 Your chargeable income falls within the <strong>0% tax bracket</strong>. No further tax deductions required.</p>")
            else:
                html.append(f"<p class='small text-muted mb-2'>Your current marginal tax bracket is <strong>{m_rate}%</strong>. Every $1,000 in eligible deductions saves <strong>SGD ${m_rate * 10:,.2f}</strong> in cash tax liability.</p>")
                html.append("<ul class='small ps-3 mb-0'>")

                # 1. RSTU Self ($8k cap)
                rstu_self_rem = max(8000.0 - (rec.rstu_self_relief or 0.0), 0.0)
                if rstu_self_rem > 0 and rem_cap > 0:
                    claimable = min(rstu_self_rem, rem_cap)
                    saved = claimable * (m_rate / 100.0)
                    html.append(f"<li><strong>CPF RSTU (Self):</strong> Top up <strong>${claimable:,.0f}</strong> to your CPF SA/RA before Dec 31 to save <strong>${saved:,.2f}</strong> in tax while earning 4.0% p.a. guaranteed interest.</li>")

                # 2. RSTU Loved Ones ($8k cap)
                rstu_fam_rem = max(8000.0 - (rec.rstu_family_relief or 0.0), 0.0)
                if rstu_fam_rem > 0 and rem_cap > 0:
                    claimable = min(rstu_fam_rem, rem_cap)
                    saved = claimable * (m_rate / 100.0)
                    html.append(f"<li><strong>CPF RSTU (Parents / Loved Ones):</strong> Top up <strong>${claimable:,.0f}</strong> to parents' CPF accounts to save <strong>${saved:,.2f}</strong> in tax.</li>")

                # 3. SRS ($15.3k cap)
                srs_rem = max(15300.0 - (rec.srs_contribution_relief or 0.0), 0.0)
                if srs_rem > 0 and rem_cap > 0:
                    claimable = min(srs_rem, rem_cap)
                    saved = claimable * (m_rate / 100.0)
                    html.append(f"<li><strong>SRS Contribution:</strong> Deposit <strong>${claimable:,.0f}</strong> into your SRS account before Dec 31 to lock in <strong>${saved:,.2f}</strong> tax savings.</li>")

                # 4. IPC Donations (250% deduction, not subject to $80k cap)
                html.append("<li><strong>Charitable Donations (250%):</strong> Donations to registered Institutions of a Public Character (IPCs) are <strong>exempt from the $80k cap</strong> and generate 2.5x tax deduction.</li>")

                html.append("</ul>")

            html.append("</div>")
            rec.optimization_advisory = "".join(html)
