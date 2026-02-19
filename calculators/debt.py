"""
Debt & Loan Management Calculators:
  9.  Student Loan Refinance
  10. Credit Card Payoff
  11. Auto Loan / Car Lease
  12. Personal Loan Eligibility
"""
import math
from flask import Blueprint, request, jsonify, render_template
from config import STUDENT_LOAN_RATES, US_CC_AVG_APR, PERSONAL_LOAN_APR_MAP, CREDIT_SCORE_TIERS

debt_bp = Blueprint("debt", __name__)


def _monthly_payment(principal, annual_rate_pct, term_months):
    if annual_rate_pct == 0:
        return principal / term_months if term_months else 0
    r = annual_rate_pct / 100 / 12
    return principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)


def _get_credit_tier(score):
    for threshold, tier in CREDIT_SCORE_TIERS:
        if score >= threshold:
            return tier
    return "Very Poor"


def _get_apr_range(score):
    for min_s, max_s, low, high in PERSONAL_LOAN_APR_MAP:
        if min_s <= score <= max_s:
            return low, high
    return 36.0, 36.0


# ── 9. Student Loan Refinance ─────────────────────────────────────────────────

@debt_bp.route("/debt/student-loan")
def student_loan():
    return render_template("debt/student_loan.html", rates=STUDENT_LOAN_RATES)


@debt_bp.route("/api/debt/student-loan", methods=["POST"])
def api_student_loan():
    data = request.get_json(force=True, silent=True) or {}
    try:
        balance          = float(data["loan_balance"])
        current_rate     = float(data["current_rate"])
        loan_type        = data.get("loan_type", "custom")
        current_term_yrs = float(data.get("current_term_years", 10))
        new_rate         = float(data["new_rate"])
        new_term_yrs     = float(data.get("new_term_years", 10))
        income           = float(data.get("income", 60000))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    # Use preset rate if loan_type specified
    preset_rates = {"undergrad": 6.53, "grad": 8.08, "parent_plus": 9.08}
    if loan_type in preset_rates and "current_rate" not in data:
        current_rate = preset_rates[loan_type]

    current_months = int(current_term_yrs * 12)
    new_months     = int(new_term_yrs * 12)

    current_pmt = _monthly_payment(balance, current_rate, current_months)
    new_pmt     = _monthly_payment(balance, new_rate, new_months)

    total_interest_current = current_pmt * current_months - balance
    total_interest_new     = new_pmt * new_months - balance
    monthly_savings        = current_pmt - new_pmt
    lifetime_savings       = total_interest_current - total_interest_new
    breakeven_months       = None  # no closing costs on student loans

    # Estimated IDR: 10% of discretionary income (income above 150% FPL ~$22k)
    discretionary = max(income - 22000, 0)
    idr_monthly   = discretionary * 0.10 / 12

    warning = ""
    if loan_type in ("undergrad", "grad", "parent_plus"):
        warning = "⚠ Refinancing federal loans with a private lender forfeits income-driven repayment options, Public Service Loan Forgiveness (PSLF), and federal forbearance protections."

    return jsonify({"ok": True, "data": {
        "current_monthly":          round(current_pmt, 2),
        "new_monthly":              round(new_pmt, 2),
        "monthly_savings":          round(monthly_savings, 2),
        "total_interest_current":   round(total_interest_current, 2),
        "total_interest_new":       round(total_interest_new, 2),
        "lifetime_savings":         round(lifetime_savings, 2),
        "breakeven_months":         breakeven_months,
        "idr_monthly":              round(idr_monthly, 2),
        "federal_benefits_warning": warning,
    }})


# ── 10. Credit Card Payoff ────────────────────────────────────────────────────

@debt_bp.route("/debt/credit-card")
def credit_card():
    return render_template("debt/credit_card.html", avg_apr=US_CC_AVG_APR)


@debt_bp.route("/api/debt/credit-card", methods=["POST"])
def api_credit_card():
    data = request.get_json(force=True, silent=True) or {}
    try:
        balance       = float(data["balance"])
        apr           = float(data.get("apr", US_CC_AVG_APR))
        min_pct       = float(data.get("minimum_pct", 2))
        min_floor     = float(data.get("minimum_floor", 25))
        extra_payment = float(data.get("extra_payment", 0))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    monthly_rate = apr / 100 / 12

    def payoff_sim(bal, extra=0):
        months = 0
        total_interest = 0
        total_paid = 0
        schedule = []
        b = bal
        while b > 0.01 and months < 600:
            months += 1
            interest = b * monthly_rate
            min_pmt  = max(b * min_pct / 100, min_floor)
            payment  = min(min_pmt + extra, b + interest)
            principal = payment - interest
            b = max(b - principal, 0)
            total_interest += interest
            total_paid     += payment
            if months <= 360:
                schedule.append({
                    "month":    months,
                    "payment":  round(payment, 2),
                    "interest": round(interest, 2),
                    "principal":round(principal, 2),
                    "balance":  round(b, 2),
                })
        return months, total_interest, total_paid, schedule

    m_min, i_min, p_min, _ = payoff_sim(balance)
    m_extra, i_extra, p_extra, schedule = payoff_sim(balance, extra_payment)

    return jsonify({"ok": True, "data": {
        "minimum_only": {
            "months_to_payoff": m_min,
            "total_interest":   round(i_min, 2),
            "total_paid":       round(p_min, 2),
        },
        "with_extra": {
            "months_to_payoff": m_extra,
            "total_interest":   round(i_extra, 2),
            "total_paid":       round(p_extra, 2),
            "interest_saved":   round(i_min - i_extra, 2),
            "months_saved":     m_min - m_extra,
        },
        "monthly_schedule": schedule,
    }})


# ── 11. Auto Loan / Car Lease ─────────────────────────────────────────────────

@debt_bp.route("/debt/auto-loan")
def auto_loan():
    return render_template("debt/auto_loan.html")


@debt_bp.route("/api/debt/auto-loan", methods=["POST"])
def api_auto_loan():
    data = request.get_json(force=True, silent=True) or {}
    try:
        vehicle_price      = float(data["vehicle_price"])
        down_payment       = float(data.get("down_payment", 0))
        loan_rate          = float(data.get("loan_rate", 7.0))
        loan_term_months   = int(data.get("loan_term_months", 60))
        residual_pct       = float(data.get("residual_value_pct", 55))
        money_factor       = float(data.get("money_factor", 0.00125))
        lease_term_months  = int(data.get("lease_term_months", 36))
        trade_in           = float(data.get("trade_in_value", 0))
        sales_tax_rate     = float(data.get("sales_tax_rate", 8.0))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    # ── Loan ──
    cap_cost_loan = vehicle_price - down_payment - trade_in
    tax_amount    = vehicle_price * sales_tax_rate / 100
    loan_amount   = cap_cost_loan + tax_amount
    loan_monthly  = _monthly_payment(loan_amount, loan_rate, loan_term_months)
    loan_total    = loan_monthly * loan_term_months + down_payment
    loan_interest = loan_monthly * loan_term_months - loan_amount
    # Estimated equity: vehicle depreciates to residual % of MSRP
    residual_value = vehicle_price * residual_pct / 100
    equity_at_end  = residual_value  # approximate

    # ── Lease ──
    cap_cost_lease  = vehicle_price - down_payment - trade_in
    residual_val    = vehicle_price * residual_pct / 100
    depreciation_mo = (cap_cost_lease - residual_val) / lease_term_months
    finance_charge  = (cap_cost_lease + residual_val) * money_factor
    lease_monthly   = depreciation_mo + finance_charge
    lease_total     = lease_monthly * lease_term_months + down_payment
    apr_equiv       = money_factor * 2400  # money factor × 2400 = approx APR %

    # Compare over same term (lease term)
    loan_monthly_same = _monthly_payment(loan_amount, loan_rate, lease_term_months)
    loan_total_same   = loan_monthly_same * lease_term_months + down_payment
    diff = loan_total_same - lease_total

    if diff > 0:
        cheaper = "LEASE"
        rec = f"Leasing saves ~${diff:,.0f} over {lease_term_months} months, but you build no equity."
    else:
        cheaper = "LOAN"
        rec = f"Buying saves ~${-diff:,.0f} over {lease_term_months} months and you own the vehicle."

    return jsonify({"ok": True, "data": {
        "loan": {
            "monthly_payment": round(loan_monthly, 2),
            "total_paid":      round(loan_total, 2),
            "total_interest":  round(loan_interest, 2),
            "equity_at_end":   round(equity_at_end, 2),
        },
        "lease": {
            "monthly_payment": round(lease_monthly, 2),
            "total_paid":      round(lease_total, 2),
            "residual_value":  round(residual_val, 2),
            "equiv_apr":       round(apr_equiv, 2),
            "buyout_option":   round(residual_val, 2),
        },
        "comparison": {
            "cheaper_option": cheaper,
            "difference":     round(abs(diff), 2),
            "recommendation": rec,
        },
    }})


# ── 12. Personal Loan Eligibility ─────────────────────────────────────────────

@debt_bp.route("/debt/personal-loan")
def personal_loan():
    return render_template("debt/personal_loan.html")


@debt_bp.route("/api/debt/personal-loan", methods=["POST"])
def api_personal_loan():
    data = request.get_json(force=True, silent=True) or {}
    try:
        loan_amount    = float(data["loan_amount"])
        annual_income  = float(data["annual_income"])
        monthly_debts  = float(data.get("monthly_debts", 0))
        credit_score   = int(data["credit_score"])
        term_years     = int(data.get("term_years", 3))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    monthly_income = annual_income / 12
    new_loan_monthly_est = _monthly_payment(loan_amount, 20, term_years * 12)  # rough
    total_debt_mo  = monthly_debts + new_loan_monthly_est
    dti_ratio      = (total_debt_mo / monthly_income * 100) if monthly_income > 0 else 100

    apr_low, apr_high = _get_apr_range(credit_score)
    monthly_low   = _monthly_payment(loan_amount, apr_low,  term_years * 12)
    monthly_high  = _monthly_payment(loan_amount, apr_high, term_years * 12)

    credit_tier = _get_credit_tier(credit_score)

    if credit_score >= 680 and dti_ratio < 36:
        eligibility = "LIKELY"
    elif credit_score >= 580 and dti_ratio < 50:
        eligibility = "POSSIBLE"
    else:
        eligibility = "UNLIKELY"

    credit_factor = "Strong" if credit_score >= 720 else ("Adequate" if credit_score >= 650 else "Weak")
    dti_factor    = "Good"   if dti_ratio < 28    else ("Adequate" if dti_ratio < 36   else "High")
    income_factor = "Good"   if annual_income >= 40000 else ("Adequate" if annual_income >= 20000 else "Low")

    return jsonify({"ok": True, "data": {
        "eligibility":            eligibility,
        "estimated_apr_low":      apr_low,
        "estimated_apr_high":     apr_high,
        "estimated_monthly_low":  round(monthly_low, 2),
        "estimated_monthly_high": round(monthly_high, 2),
        "dti_ratio":              round(dti_ratio, 1),
        "credit_tier":            credit_tier,
        "approval_factors": {
            "credit_score": credit_factor,
            "dti":          dti_factor,
            "income":       income_factor,
        },
    }})
