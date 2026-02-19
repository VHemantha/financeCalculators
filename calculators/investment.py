"""
Investment & Retirement Calculators:
  5. Compound Interest
  6. 401(k) / Pension Planner
  7. SIP Calculator
  8. FIRE Calculator
"""
import math
from flask import Blueprint, request, jsonify, render_template
from config import INVESTMENT_PRESETS

investment_bp = Blueprint("investment", __name__)

COMPOUND_FREQ = {"annually": 1, "semi": 2, "quarterly": 4, "monthly": 12, "daily": 365}


# ── 5. Compound Interest ──────────────────────────────────────────────────────

@investment_bp.route("/investment/compound-interest")
def compound_interest():
    return render_template("investment/compound_interest.html", presets=INVESTMENT_PRESETS)


@investment_bp.route("/api/investment/compound-interest", methods=["POST"])
def api_compound_interest():
    data = request.get_json(force=True, silent=True) or {}
    try:
        principal       = float(data.get("principal", 0))
        monthly_add     = float(data.get("monthly_addition", 0))
        annual_rate     = float(data["annual_rate"])
        years           = int(data["years"])
        freq_key        = data.get("compound_freq", "monthly")
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    n = COMPOUND_FREQ.get(freq_key, 12)
    r_per_period = annual_rate / 100 / n
    periods_per_year = n

    yearly = []
    balance = principal
    total_contributed = principal

    for yr in range(1, years + 1):
        for _ in range(periods_per_year):
            balance = balance * (1 + r_per_period) + monthly_add * (12 / periods_per_year)
        total_contributed += monthly_add * 12
        yearly.append({
            "year":        yr,
            "balance":     round(balance, 2),
            "contributed": round(total_contributed, 2),
            "interest":    round(balance - total_contributed, 2),
        })

    # Effective APY
    effective_apy = (1 + annual_rate / 100 / n) ** n - 1

    return jsonify({"ok": True, "data": {
        "final_balance":     round(balance, 2),
        "total_contributed": round(total_contributed, 2),
        "total_interest":    round(balance - total_contributed, 2),
        "effective_apy":     round(effective_apy * 100, 4),
        "yearly_breakdown":  yearly,
    }})


# ── 6. 401(k) / Pension Planner ───────────────────────────────────────────────

@investment_bp.route("/investment/401k-pension")
def pension_401k():
    return render_template("investment/pension_401k.html", presets=INVESTMENT_PRESETS)


@investment_bp.route("/api/investment/401k-pension", methods=["POST"])
def api_pension_401k():
    data = request.get_json(force=True, silent=True) or {}
    try:
        current_age        = int(data["current_age"])
        retirement_age     = int(data.get("retirement_age", 65))
        current_balance    = float(data.get("current_balance", 0))
        annual_salary      = float(data["annual_salary"])
        contribution_pct   = float(data.get("contribution_pct", 10))
        employer_match_pct = float(data.get("employer_match_pct", 3))
        employer_match_limit= float(data.get("employer_match_limit", 6))
        expected_return    = float(data.get("expected_return", 7))
        inflation_rate     = float(data.get("inflation_rate", 2.5))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    if retirement_age <= current_age:
        return jsonify({"ok": False, "error": "Retirement age must be greater than current age"}), 422

    years = retirement_age - current_age
    EMP_LIMIT = INVESTMENT_PRESETS["401k_employee_limit"]

    annual_employee = min(annual_salary * contribution_pct / 100, EMP_LIMIT)
    # Employer matches contribution_pct up to employer_match_limit% of salary
    employer_match_contribution = min(annual_salary * contribution_pct / 100,
                                      annual_salary * employer_match_limit / 100)
    annual_employer = employer_match_contribution * employer_match_pct / contribution_pct if contribution_pct > 0 else 0
    annual_total    = annual_employee + annual_employer

    monthly_return = expected_return / 100 / 12
    monthly_total  = annual_total / 12
    inflation_monthly = inflation_rate / 100 / 12

    balance = current_balance
    real_balance = current_balance
    yearly = []

    for yr in range(1, years + 1):
        age = current_age + yr
        for _ in range(12):
            balance      = balance * (1 + monthly_return) + monthly_total
            real_balance = real_balance * (1 + monthly_return - inflation_monthly) + monthly_total
        yearly.append({
            "year":         yr,
            "age":          age,
            "balance":      round(balance, 2),
            "real_balance": round(real_balance, 2),
        })

    monthly_income_4pct  = balance * 0.04 / 12
    monthly_income_real  = real_balance * 0.04 / 12
    irs_warning = annual_salary * contribution_pct / 100 > EMP_LIMIT

    return jsonify({"ok": True, "data": {
        "years_to_retirement":           years,
        "annual_employee_contribution":  round(annual_employee, 2),
        "annual_employer_contribution":  round(annual_employer, 2),
        "total_annual_contribution":     round(annual_total, 2),
        "irs_limit_warning":             irs_warning,
        "projected_balance":             round(balance, 2),
        "projected_balance_real":        round(real_balance, 2),
        "monthly_income_4pct":           round(monthly_income_4pct, 2),
        "monthly_income_real":           round(monthly_income_real, 2),
        "yearly_growth":                 yearly,
    }})


# ── 7. SIP Calculator ─────────────────────────────────────────────────────────

@investment_bp.route("/investment/sip")
def sip():
    return render_template("investment/sip.html", presets=INVESTMENT_PRESETS)


@investment_bp.route("/api/investment/sip", methods=["POST"])
def api_sip():
    data = request.get_json(force=True, silent=True) or {}
    try:
        monthly_investment = float(data["monthly_investment"])
        annual_return      = float(data.get("annual_return", 12))
        years              = int(data["years"])
        step_up_pct        = float(data.get("step_up_pct", 0))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    r_monthly = annual_return / 100 / 12
    sip_amount = monthly_investment
    total_invested = 0
    balance = 0
    yearly = []

    for yr in range(1, years + 1):
        for _ in range(12):
            balance = (balance + sip_amount) * (1 + r_monthly)
            total_invested += sip_amount
        # Step-up after each year
        sip_amount *= (1 + step_up_pct / 100)
        yearly.append({
            "year":     yr,
            "invested": round(total_invested, 2),
            "value":    round(balance, 2),
            "returns":  round(balance - total_invested, 2),
        })

    absolute_return = ((balance / total_invested) - 1) * 100 if total_invested > 0 else 0
    wealth_ratio    = balance / total_invested if total_invested > 0 else 0

    return jsonify({"ok": True, "data": {
        "total_invested":    round(total_invested, 2),
        "estimated_returns": round(balance - total_invested, 2),
        "final_amount":      round(balance, 2),
        "absolute_return_pct": round(absolute_return, 2),
        "wealth_ratio":      round(wealth_ratio, 2),
        "yearly_breakdown":  yearly,
    }})


# ── 8. FIRE Calculator ────────────────────────────────────────────────────────

@investment_bp.route("/investment/fire")
def fire():
    return render_template("investment/fire.html", presets=INVESTMENT_PRESETS)


@investment_bp.route("/api/investment/fire", methods=["POST"])
def api_fire():
    data = request.get_json(force=True, silent=True) or {}
    try:
        current_age     = int(data["current_age"])
        annual_expenses = float(data["annual_expenses"])
        current_savings = float(data.get("current_savings", 0))
        annual_savings  = float(data.get("annual_savings", 0))
        expected_return = float(data.get("expected_return", 7))
        swr             = float(data.get("safe_withdrawal_rate", 4))
        inflation_rate  = float(data.get("inflation_rate", 2.5))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    fire_number = annual_expenses / (swr / 100)
    current_progress = (current_savings / fire_number * 100) if fire_number > 0 else 0
    monthly_savings  = annual_savings / 12
    monthly_return   = expected_return / 100 / 12
    inflation_monthly = inflation_rate / 100 / 12

    balance = current_savings
    fire_target = fire_number
    years_to_fire = None
    fire_age = None
    yearly = []

    for yr in range(1, 71):  # max 70 years
        age = current_age + yr
        for _ in range(12):
            balance     += balance * monthly_return + monthly_savings
            fire_target *= (1 + inflation_monthly)

        yearly.append({
            "year":        yr,
            "age":         age,
            "balance":     round(balance, 2),
            "fire_target": round(fire_target, 2),
        })

        if years_to_fire is None and balance >= fire_target:
            years_to_fire = yr
            fire_age      = current_age + yr
            break

    return jsonify({"ok": True, "data": {
        "fire_number":          round(fire_number, 0),
        "years_to_fire":        years_to_fire,
        "fire_age":             fire_age,
        "current_progress_pct": round(current_progress, 1),
        "monthly_expenses":     round(annual_expenses / 12, 2),
        "yearly_projection":    yearly,
    }})
