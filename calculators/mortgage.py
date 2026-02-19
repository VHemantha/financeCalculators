"""
Mortgage & Real Estate Calculators:
  1. Mortgage Repayment
  2. Rent vs Buy
  3. Mortgage Refinance
  4. Home Affordability
"""
import math
from flask import Blueprint, request, jsonify, render_template
from config import MORTGAGE_RATES

mortgage_bp = Blueprint("mortgage", __name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _monthly_payment(principal, annual_rate_pct, term_months):
    """Standard annuity formula. Returns 0 for 0% rate (interest-free)."""
    if annual_rate_pct == 0:
        return principal / term_months if term_months else 0
    r = annual_rate_pct / 100 / 12
    return principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)


def _amortize(principal, annual_rate_pct, term_months):
    """Full amortization schedule — list of dicts."""
    schedule = []
    balance = principal
    r = annual_rate_pct / 100 / 12
    payment = _monthly_payment(principal, annual_rate_pct, term_months)
    for m in range(1, term_months + 1):
        interest = balance * r
        principal_paid = payment - interest
        balance = max(balance - principal_paid, 0)
        schedule.append({
            "month": m,
            "payment": round(payment, 2),
            "principal": round(principal_paid, 2),
            "interest": round(interest, 2),
            "balance": round(balance, 2),
        })
    return schedule


def _summarize_by_year(schedule):
    yearly = []
    for yr in range(1, math.ceil(len(schedule) / 12) + 1):
        chunk = schedule[(yr - 1) * 12: yr * 12]
        yearly.append({
            "year": yr,
            "principal_paid": round(sum(r["principal"] for r in chunk), 2),
            "interest_paid":  round(sum(r["interest"]  for r in chunk), 2),
            "balance":        round(chunk[-1]["balance"], 2),
        })
    return yearly


def _validate_number(data, key, min_val, max_val, label):
    try:
        v = float(data[key])
    except (KeyError, TypeError, ValueError):
        return None, f"{label} is required and must be a number"
    if not (min_val <= v <= max_val):
        return None, f"{label} must be between {min_val} and {max_val}"
    return v, None


# ── 1. Mortgage Repayment ─────────────────────────────────────────────────────

@mortgage_bp.route("/mortgage/repayment")
def repayment():
    return render_template("mortgage/repayment.html", rates=MORTGAGE_RATES)


@mortgage_bp.route("/api/mortgage/repayment", methods=["POST"])
def api_repayment():
    data = request.get_json(force=True, silent=True) or {}
    errors = []

    principal, e = _validate_number(data, "principal", 1_000, 100_000_000, "Loan amount")
    if e: errors.append(e)

    annual_rate, e = _validate_number(data, "annual_rate", 0, 30, "Annual interest rate")
    if e: errors.append(e)

    term_years, e = _validate_number(data, "term_years", 1, 40, "Loan term")
    if e: errors.append(e)

    if errors:
        return jsonify({"ok": False, "error": "; ".join(errors)}), 422

    term_months = int(term_years * 12)
    payment = _monthly_payment(principal, annual_rate, term_months)
    total_paid = payment * term_months
    total_interest = total_paid - principal
    schedule = _amortize(principal, annual_rate, term_months)
    yearly = _summarize_by_year(schedule)

    return jsonify({"ok": True, "data": {
        "monthly_payment":  round(payment, 2),
        "total_paid":       round(total_paid, 2),
        "total_interest":   round(total_interest, 2),
        "effective_rate":   annual_rate,
        "amortization_table": schedule,
        "summary_by_year":    yearly,
    }})


# ── 2. Rent vs Buy ────────────────────────────────────────────────────────────

@mortgage_bp.route("/mortgage/rent-vs-buy")
def rent_vs_buy():
    return render_template("mortgage/rent_vs_buy.html", rates=MORTGAGE_RATES)


@mortgage_bp.route("/api/mortgage/rent-vs-buy", methods=["POST"])
def api_rent_vs_buy():
    data = request.get_json(force=True, silent=True) or {}
    try:
        home_price          = float(data["home_price"])
        down_pct            = float(data.get("down_payment_pct", 20))
        mortgage_rate       = float(data.get("mortgage_rate", 6.7))
        term_years          = int(data.get("term_years", 30))
        annual_home_growth  = float(data.get("annual_home_growth", 4))
        monthly_rent        = float(data["monthly_rent"])
        annual_rent_increase= float(data.get("annual_rent_increase", 3))
        investment_return   = float(data.get("investment_return", 7))
        prop_tax_rate       = float(data.get("property_tax_rate", 1.2))
        maintenance_pct     = float(data.get("maintenance_pct", 1))
        insurance_monthly   = float(data.get("insurance_monthly", 150))
        years               = int(data.get("years", 10))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    years = min(years, 30)
    down_payment  = home_price * down_pct / 100
    loan          = home_price - down_payment
    term_months   = term_years * 12
    monthly_pmt   = _monthly_payment(loan, mortgage_rate, term_months)

    # Renter invests the down payment + any monthly difference
    renter_portfolio   = down_payment
    buyer_equity       = down_payment
    home_value         = home_price
    rent               = monthly_rent
    monthly_invest_ret = investment_return / 100 / 12
    monthly_home_growth= annual_home_growth / 100 / 12

    yearly = []
    cumulative_buy_cost  = down_payment
    cumulative_rent_cost = 0
    breakeven_year       = None

    # Get amortization for equity tracking
    amort = _amortize(loan, mortgage_rate, term_months)

    for yr in range(1, years + 1):
        chunk = amort[(yr - 1) * 12: yr * 12]
        principal_paid_yr = sum(r["principal"] for r in chunk)
        interest_paid_yr  = sum(r["interest"]  for r in chunk)
        balance_end       = chunk[-1]["balance"] if chunk else loan

        home_value *= (1 + annual_home_growth / 100)
        buyer_equity = home_value - balance_end

        # Annual buy costs: mortgage interest + property tax + maintenance + insurance
        prop_tax_annual    = home_price * prop_tax_rate / 100
        maintenance_annual = home_price * maintenance_pct / 100
        insurance_annual   = insurance_monthly * 12
        buy_annual_cost    = interest_paid_yr + prop_tax_annual + maintenance_annual + insurance_annual
        cumulative_buy_cost += buy_annual_cost

        # Renter: monthly rent grows by annual_rent_increase each year
        rent_annual = rent * 12
        cumulative_rent_cost += rent_annual
        rent *= (1 + annual_rent_increase / 100)  # next year's rent

        # Renter invests the cost difference each month
        monthly_diff = monthly_pmt - (rent_annual / 12)
        for _ in range(12):
            renter_portfolio *= (1 + monthly_invest_ret)
            if monthly_diff > 0:
                renter_portfolio += monthly_diff

        # Renter net worth: portfolio value
        # Buyer net worth: equity
        buy_net   = round(buyer_equity, 2)
        rent_net  = round(renter_portfolio, 2)

        if breakeven_year is None and buy_net >= rent_net:
            breakeven_year = yr

        yearly.append({
            "year": yr,
            "buy_net_worth":        buy_net,
            "rent_net_worth":       rent_net,
            "cumulative_buy_cost":  round(cumulative_buy_cost, 2),
            "cumulative_rent_cost": round(cumulative_rent_cost, 2),
        })

    last = yearly[-1]
    diff = last["buy_net_worth"] - last["rent_net_worth"]
    if diff > 5000:
        rec = "BUY"
    elif diff < -5000:
        rec = "RENT"
    else:
        rec = "NEUTRAL"

    return jsonify({"ok": True, "data": {
        "breakeven_year":             breakeven_year,
        "buy_net_worth_at_horizon":   last["buy_net_worth"],
        "rent_net_worth_at_horizon":  last["rent_net_worth"],
        "recommendation":             rec,
        "yearly_comparison":          yearly,
    }})


# ── 3. Mortgage Refinance ─────────────────────────────────────────────────────

@mortgage_bp.route("/mortgage/refinance")
def refinance():
    return render_template("mortgage/refinance.html", rates=MORTGAGE_RATES)


@mortgage_bp.route("/api/mortgage/refinance", methods=["POST"])
def api_refinance():
    data = request.get_json(force=True, silent=True) or {}
    try:
        current_balance       = float(data["current_balance"])
        current_rate          = float(data["current_rate"])
        current_remaining_yrs = float(data.get("current_remaining_years", 25))
        new_rate              = float(data["new_rate"])
        new_term_yrs          = float(data.get("new_term_years", 30))
        closing_costs         = float(data.get("closing_costs", 4000))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    current_months = int(current_remaining_yrs * 12)
    new_months     = int(new_term_yrs * 12)

    current_pmt = _monthly_payment(current_balance, current_rate, current_months)
    new_pmt     = _monthly_payment(current_balance, new_rate, new_months)

    monthly_savings         = current_pmt - new_pmt
    breakeven_months        = int(closing_costs / monthly_savings) if monthly_savings > 0 else None
    total_interest_current  = current_pmt * current_months - current_balance
    total_interest_new      = new_pmt * new_months - current_balance
    net_savings             = total_interest_current - total_interest_new - closing_costs

    rec = "REFINANCE" if (monthly_savings > 0 and breakeven_months and breakeven_months < current_months) else "STAY"

    return jsonify({"ok": True, "data": {
        "current_monthly":        round(current_pmt, 2),
        "new_monthly":            round(new_pmt, 2),
        "monthly_savings":        round(monthly_savings, 2),
        "breakeven_months":       breakeven_months,
        "total_interest_current": round(total_interest_current, 2),
        "total_interest_new":     round(total_interest_new, 2),
        "net_savings":            round(net_savings, 2),
        "recommendation":         rec,
    }})


# ── 4. Home Affordability ─────────────────────────────────────────────────────

@mortgage_bp.route("/mortgage/affordability")
def affordability():
    return render_template("mortgage/affordability.html", rates=MORTGAGE_RATES)


@mortgage_bp.route("/api/mortgage/affordability", methods=["POST"])
def api_affordability():
    data = request.get_json(force=True, silent=True) or {}
    try:
        gross_annual    = float(data["gross_annual_income"])
        monthly_debts   = float(data.get("monthly_debts", 0))
        down_payment    = float(data.get("down_payment", 0))
        annual_rate     = float(data.get("annual_rate", 6.7))
        term_years      = int(data.get("term_years", 30))
        prop_tax_rate   = float(data.get("property_tax_rate", 1.2))
        insurance_mo    = float(data.get("insurance_monthly", 150))
        hoa_mo          = float(data.get("hoa_monthly", 0))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    monthly_income = gross_annual / 12
    term_months    = term_years * 12

    # 28% front-end: PITI ≤ 28% of gross monthly income
    max_piti_28    = monthly_income * 0.28
    max_pi_28      = max_piti_28 - (prop_tax_rate / 100 / 12 * 250000) - insurance_mo - hoa_mo
    # Solve for principal: PI = P * r(1+r)^n / ((1+r)^n-1)  →  P = PI / factor
    r = annual_rate / 100 / 12
    if r > 0 and term_months > 0:
        factor = r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)
        # Iterative: use estimated P to get actual tax, redo
        max_loan_28    = max_pi_28 / factor if factor > 0 else 0
        max_price_28   = max_loan_28 + down_payment
        actual_tax_mo  = max_price_28 * prop_tax_rate / 100 / 12
        actual_pi_28   = max_piti_28 - actual_tax_mo - insurance_mo - hoa_mo
        max_loan_28    = actual_pi_28 / factor if factor > 0 else 0
        max_price_28   = max(max_loan_28 + down_payment, 0)
    else:
        max_price_28   = 0

    # 36% back-end: all debt ≤ 36% of gross monthly income
    max_total_debt_36 = monthly_income * 0.36
    max_pi_36         = max_total_debt_36 - monthly_debts - (prop_tax_rate / 100 / 12 * 250000) - insurance_mo - hoa_mo
    if r > 0 and term_months > 0 and max_pi_36 > 0:
        max_loan_36   = max_pi_36 / factor
        max_price_36  = max_loan_36 + down_payment
        actual_tax_mo = max_price_36 * prop_tax_rate / 100 / 12
        actual_pi_36  = max_total_debt_36 - monthly_debts - actual_tax_mo - insurance_mo - hoa_mo
        max_loan_36   = actual_pi_36 / factor if factor > 0 else 0
        max_price_36  = max(max_loan_36 + down_payment, 0)
    else:
        max_price_36  = 0

    max_price = min(max_price_28, max_price_36)
    max_loan  = max(max_price - down_payment, 0)
    max_piti  = _monthly_payment(max_loan, annual_rate, term_months) + (max_price * prop_tax_rate / 100 / 12) + insurance_mo + hoa_mo
    current_dti = (monthly_debts / monthly_income * 100) if monthly_income > 0 else 0

    if current_dti < 28:
        dti_status = "GOOD"
    elif current_dti < 36:
        dti_status = "CAUTION"
    else:
        dti_status = "HIGH"

    return jsonify({"ok": True, "data": {
        "max_home_price_28pct": round(max_price_28, 0),
        "max_home_price_36pct": round(max_price_36, 0),
        "max_home_price":       round(max_price, 0),
        "max_monthly_piti":     round(max_piti, 2),
        "monthly_income":       round(monthly_income, 2),
        "current_dti":          round(current_dti, 1),
        "dti_status":           dti_status,
    }})
