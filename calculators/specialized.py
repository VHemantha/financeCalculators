"""
Specialized / Niche Calculators:
  16. Inflation Calculator
  17. Rule of 72 Calculator
  18. Latte Factor Calculator
"""
import math
from flask import Blueprint, request, jsonify, render_template
from config import US_CPI, EU_HICP, INDIA_CPI

specialized_bp = Blueprint("specialized", __name__)

CPI_DATA = {"US": US_CPI, "EU": EU_HICP, "IN": INDIA_CPI}
CPI_MIN_YEAR = {"US": 1913, "EU": 2000, "IN": 2000}
CPI_MAX_YEAR = 2024


# ── 16. Inflation Calculator ──────────────────────────────────────────────────

@specialized_bp.route("/specialized/inflation")
def inflation():
    return render_template(
        "specialized/inflation.html",
        cpi_years={
            "US": sorted(US_CPI.keys()),
            "EU": sorted(EU_HICP.keys()),
            "IN": sorted(INDIA_CPI.keys()),
        }
    )


@specialized_bp.route("/api/specialized/inflation", methods=["POST"])
def api_inflation():
    data = request.get_json(force=True, silent=True) or {}
    try:
        amount     = float(data.get("amount", 100))
        start_year = int(data["start_year"])
        end_year   = int(data.get("end_year", CPI_MAX_YEAR))
        region     = data.get("region", "US").upper()
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    cpi = CPI_DATA.get(region)
    if not cpi:
        return jsonify({"ok": False, "error": "Region must be US, EU, or IN"}), 422

    if start_year not in cpi or end_year not in cpi:
        return jsonify({"ok": False, "error": f"Year range for {region}: {min(cpi)} – {max(cpi)}"}), 422

    if start_year >= end_year:
        return jsonify({"ok": False, "error": "Start year must be before end year"}), 422

    start_cpi = cpi[start_year]
    end_cpi   = cpi[end_year]

    adjusted   = amount * end_cpi / start_cpi
    cum_inf    = (end_cpi / start_cpi - 1) * 100
    years_span = end_year - start_year
    avg_annual = (math.pow(end_cpi / start_cpi, 1 / years_span) - 1) * 100 if years_span > 0 else 0
    power_lost = amount - (amount * start_cpi / end_cpi)

    # Year-by-year trajectory (only available years)
    yearly = []
    for yr in range(start_year, end_year + 1):
        if yr in cpi:
            val = amount * cpi[yr] / start_cpi
            yearly.append({
                "year":      yr,
                "value":     round(val, 2),
                "cpi_index": round(cpi[yr], 1),
            })

    return jsonify({"ok": True, "data": {
        "original_amount":          round(amount, 2),
        "adjusted_amount":          round(adjusted, 2),
        "cumulative_inflation_pct": round(cum_inf, 2),
        "avg_annual_rate":          round(avg_annual, 3),
        "purchasing_power_lost":    round(power_lost, 2),
        "yearly_values":            yearly,
    }})


# ── 17. Rule of 72 ────────────────────────────────────────────────────────────

@specialized_bp.route("/specialized/rule-of-72")
def rule_of_72():
    return render_template("specialized/rule_of_72.html")


@specialized_bp.route("/api/specialized/rule-of-72", methods=["POST"])
def api_rule_of_72():
    data = request.get_json(force=True, silent=True) or {}
    try:
        mode  = data.get("mode", "rate_to_years")
        value = float(data["value"])
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    if value <= 0:
        return jsonify({"ok": False, "error": "Value must be positive"}), 422

    if mode == "rate_to_years":
        r = value  # percent
        double_rule72  = 72 / r
        triple_rule114 = 114 / r
        quad_rule144   = 144 / r
        exact_double   = math.log(2) / math.log(1 + r / 100) if r > 0 else None
        exact_triple   = math.log(3) / math.log(1 + r / 100) if r > 0 else None
        exact_quad     = math.log(4) / math.log(1 + r / 100) if r > 0 else None
        desc = f"At {r}% annual return, money doubles in ~{double_rule72:.1f} years."
    else:  # years_to_rate
        t = value  # years
        double_rule72  = 72 / t
        triple_rule114 = 114 / t
        quad_rule144   = 144 / t
        exact_double   = (math.pow(2, 1/t) - 1) * 100 if t > 0 else None
        exact_triple   = (math.pow(3, 1/t) - 1) * 100 if t > 0 else None
        exact_quad     = (math.pow(4, 1/t) - 1) * 100 if t > 0 else None
        desc = f"To double money in {t} years, you need ~{double_rule72:.2f}% annual return."

    return jsonify({"ok": True, "data": {
        "rule_72":  {
            "years" if mode == "rate_to_years" else "rate": round(double_rule72, 2),
        },
        "rule_114": {
            "years" if mode == "rate_to_years" else "rate": round(triple_rule114, 2),
        },
        "rule_144": {
            "years" if mode == "rate_to_years" else "rate": round(quad_rule144, 2),
        },
        "exact": {
            "double": round(exact_double, 3) if exact_double else None,
            "triple": round(exact_triple, 3) if exact_triple else None,
            "quad":   round(exact_quad,   3) if exact_quad else None,
        },
        "description": desc,
        "rate_pct" if mode == "rate_to_years" else "years": value,
    }})


# ── 18. Latte Factor ──────────────────────────────────────────────────────────

@specialized_bp.route("/specialized/latte-factor")
def latte_factor():
    return render_template("specialized/latte_factor.html")


@specialized_bp.route("/api/specialized/latte-factor", methods=["POST"])
def api_latte_factor():
    data = request.get_json(force=True, silent=True) or {}
    try:
        daily_expense  = float(data.get("daily_expense", 5))
        annual_return  = float(data.get("annual_return", 7))
        years          = int(data.get("years", 30))
        inflation_rate = float(data.get("inflation_rate", 2.5))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    monthly_expense  = daily_expense * 30.44  # avg days/month
    annual_expense   = daily_expense * 365
    monthly_return   = annual_return / 100 / 12
    inflation_monthly = inflation_rate / 100 / 12

    balance      = 0
    real_balance = 0
    total_saved  = 0
    yearly       = []

    for yr in range(1, years + 1):
        for _ in range(12):
            balance      = (balance + monthly_expense) * (1 + monthly_return)
            real_balance = (real_balance + monthly_expense) * (1 + monthly_return - inflation_monthly)
            total_saved += monthly_expense

        yearly.append({
            "year":       yr,
            "saved":      round(total_saved, 2),
            "invested":   round(balance, 2),
            "real_value": round(real_balance, 2),
        })

    return jsonify({"ok": True, "data": {
        "daily_expense":           round(daily_expense, 2),
        "monthly_expense":         round(monthly_expense, 2),
        "annual_expense":          round(annual_expense, 2),
        "invested_value_nominal":  round(balance, 2),
        "invested_value_real":     round(real_balance, 2),
        "total_invested":          round(total_saved, 2),
        "investment_gain":         round(balance - total_saved, 2),
        "yearly_projection":       yearly,
    }})
