"""
Tax & Salary Calculators:
  13. Take-Home Pay (US / UK / India)
  14. Freelance Tax Estimator (US / UK / India)
  15. Capital Gains Tax (US / UK / India)
"""
from flask import Blueprint, request, jsonify, render_template
from config import (
    US_TAX_BRACKETS, US_STANDARD_DEDUCTION, US_FICA, US_STATE_TAX,
    UK_PERSONAL_ALLOWANCE, UK_TAX_BRACKETS, UK_NI_EMPLOYEE, UK_NI_SELF_EMPLOYED,
    UK_PA_TAPER_START, UK_PA_TAPER_END,
    INDIA_NEW_REGIME, INDIA_OLD_REGIME, INDIA_SURCHARGE,
    US_LTCG_BRACKETS, US_NIIT_RATE, US_NIIT_THRESHOLD, US_LTCG_HOLDING_MONTHS,
    UK_CGT, INDIA_CGT,
)

tax_bp = Blueprint("tax", __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _apply_brackets(taxable_income, brackets):
    """Generic progressive tax calculator. brackets = [(upper, rate), ...]"""
    tax = 0
    prev_upper = 0
    applied = []
    for upper, rate in brackets:
        if taxable_income <= prev_upper:
            break
        taxable_in_band = min(taxable_income, upper) - prev_upper
        band_tax = taxable_in_band * rate
        tax += band_tax
        applied.append({
            "bracket": f"${prev_upper:,.0f} – {'∞' if upper == float('inf') else f'${upper:,.0f}'}",
            "rate":    round(rate * 100, 1),
            "tax":     round(band_tax, 2),
        })
        prev_upper = upper
        if taxable_income <= upper:
            break
    return round(tax, 2), applied


def _india_apply_brackets(taxable_income, brackets):
    """India brackets start from 0."""
    tax = 0
    prev_upper = 0
    applied = []
    for upper, rate in brackets:
        if taxable_income <= prev_upper:
            break
        in_band = min(taxable_income, upper) - prev_upper
        band_tax = in_band * rate
        tax += band_tax
        applied.append({
            "bracket": f"₹{prev_upper:,.0f} – {'∞' if upper == float('inf') else f'₹{upper:,.0f}'}",
            "rate":    round(rate * 100, 1),
            "tax":     round(band_tax, 2),
        })
        prev_upper = upper
        if taxable_income <= upper:
            break
    return round(tax, 2), applied


def _india_surcharge(base_tax, income):
    for upper, rate in INDIA_SURCHARGE:
        if income <= upper:
            return round(base_tax * rate, 2)
    return 0


# ── 13. Take-Home Pay ─────────────────────────────────────────────────────────

@tax_bp.route("/tax/take-home-pay")
def take_home_pay():
    return render_template("tax/take_home_pay.html", states=list(US_STATE_TAX.keys()))


@tax_bp.route("/api/tax/take-home-pay", methods=["POST"])
def api_take_home_pay():
    data = request.get_json(force=True, silent=True) or {}
    try:
        gross        = float(data["gross_income"])
        country      = data.get("country", "US").upper()
        filing       = data.get("filing_status", "single").lower()
        state        = data.get("state", "other")
        pay_freq     = data.get("pay_frequency", "annual")
        regime       = data.get("regime", "new")
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    freq_divisor = {"annual": 1, "monthly": 12, "biweekly": 26}.get(pay_freq, 1)

    if country == "US":
        result = _us_take_home(gross, filing, state)
    elif country == "UK":
        result = _uk_take_home(gross)
    elif country == "IN":
        result = _india_take_home(gross, regime)
    else:
        return jsonify({"ok": False, "error": "Country must be US, UK, or IN"}), 422

    result["take_home_per_period"] = round(result["take_home_annual"] / freq_divisor, 2)
    return jsonify({"ok": True, "data": result})


def _us_take_home(gross, filing, state):
    filing = filing if filing in US_TAX_BRACKETS else "single"
    std_ded = US_STANDARD_DEDUCTION.get(filing, 15000)
    taxable = max(gross - std_ded, 0)

    fed_tax, brackets_applied = _apply_brackets(taxable, US_TAX_BRACKETS[filing])

    # FICA
    ss_tax  = min(gross, US_FICA["ss_wage_base"]) * US_FICA["ss_rate"]
    med_tax = gross * US_FICA["medicare_rate"]
    add_med = max(gross - US_FICA["additional_medicare_threshold_single"], 0) * US_FICA["additional_medicare_rate"]

    # State
    state_rate = US_STATE_TAX.get(state, US_STATE_TAX["other"])
    state_tax  = gross * state_rate

    total_tax    = fed_tax + ss_tax + med_tax + add_med + state_tax
    take_home    = gross - total_tax
    eff_rate     = (total_tax / gross * 100) if gross > 0 else 0
    marg_rate    = 0
    for upper, rate in US_TAX_BRACKETS[filing]:
        if taxable <= upper:
            marg_rate = rate * 100
            break

    return {
        "gross_annual":          round(gross, 2),
        "total_tax":             round(total_tax, 2),
        "effective_rate":        round(eff_rate, 2),
        "marginal_rate":         round(marg_rate, 1),
        "take_home_annual":      round(take_home, 2),
        "breakdown": {
            "federal_tax":       round(fed_tax, 2),
            "state_tax":         round(state_tax, 2),
            "social_security":   round(ss_tax, 2),
            "medicare":          round(med_tax + add_med, 2),
        },
        "tax_brackets_applied":  brackets_applied,
    }


def _uk_take_home(gross):
    # Taper personal allowance above £100,000
    pa = UK_PERSONAL_ALLOWANCE
    if gross > UK_PA_TAPER_START:
        pa = max(pa - (gross - UK_PA_TAPER_START) / 2, 0)

    taxable = max(gross - pa, 0)
    income_tax, brackets_applied = _apply_brackets(taxable, UK_TAX_BRACKETS)

    # NI Employee
    lower = UK_NI_EMPLOYEE["lower_earnings_limit"]
    upper = UK_NI_EMPLOYEE["upper_earnings_limit"]
    ni = 0
    if gross > lower:
        ni += min(gross, upper) * UK_NI_EMPLOYEE["rate_main"]
        if gross > upper:
            ni += (gross - upper) * UK_NI_EMPLOYEE["rate_upper"]
        ni -= lower * UK_NI_EMPLOYEE["rate_main"]

    total_tax  = income_tax + ni
    take_home  = gross - total_tax
    eff_rate   = (total_tax / gross * 100) if gross > 0 else 0
    marg_rate  = 0
    for upper_b, rate in UK_TAX_BRACKETS:
        if taxable <= upper_b:
            marg_rate = rate * 100
            break

    return {
        "gross_annual":     round(gross, 2),
        "total_tax":        round(total_tax, 2),
        "effective_rate":   round(eff_rate, 2),
        "marginal_rate":    round(marg_rate, 1),
        "take_home_annual": round(take_home, 2),
        "breakdown": {
            "income_tax":         round(income_tax, 2),
            "national_insurance": round(ni, 2),
        },
        "tax_brackets_applied": brackets_applied,
    }


def _india_take_home(gross, regime):
    cfg = INDIA_NEW_REGIME if regime == "new" else INDIA_OLD_REGIME
    std_ded  = cfg["standard_deduction"]
    taxable  = max(gross - std_ded, 0)
    base_tax, brackets_applied = _india_apply_brackets(taxable, cfg["brackets"])

    # Section 87A rebate
    if taxable <= cfg["rebate_87a_limit"]:
        base_tax = 0

    surcharge = _india_surcharge(base_tax, gross)
    cess      = (base_tax + surcharge) * cfg["cess_rate"]
    total_tax = base_tax + surcharge + cess
    take_home = gross - total_tax
    eff_rate  = (total_tax / gross * 100) if gross > 0 else 0
    marg_rate = 0
    for upper_b, rate in cfg["brackets"]:
        if taxable <= upper_b:
            marg_rate = rate * 100
            break

    return {
        "gross_annual":     round(gross, 2),
        "total_tax":        round(total_tax, 2),
        "effective_rate":   round(eff_rate, 2),
        "marginal_rate":    round(marg_rate, 1),
        "take_home_annual": round(take_home, 2),
        "breakdown": {
            "income_tax": round(base_tax, 2),
            "surcharge":  round(surcharge, 2),
            "cess":       round(cess, 2),
        },
        "tax_brackets_applied": brackets_applied,
    }


# ── 14. Freelance Tax ─────────────────────────────────────────────────────────

@tax_bp.route("/tax/freelance")
def freelance():
    return render_template("tax/freelance_tax.html", states=list(US_STATE_TAX.keys()))


@tax_bp.route("/api/tax/freelance", methods=["POST"])
def api_freelance():
    data = request.get_json(force=True, silent=True) or {}
    try:
        gross_revenue        = float(data["gross_revenue"])
        business_expenses    = float(data.get("business_expenses", 0))
        country              = data.get("country", "US").upper()
        filing               = data.get("filing_status", "single").lower()
        state                = data.get("state", "other")
        presumptive          = bool(data.get("presumptive_scheme", False))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    if country == "US":
        return jsonify({"ok": True, "data": _us_freelance(gross_revenue, business_expenses, filing, state)})
    elif country == "UK":
        return jsonify({"ok": True, "data": _uk_freelance(gross_revenue, business_expenses)})
    elif country == "IN":
        return jsonify({"ok": True, "data": _india_freelance(gross_revenue, business_expenses, presumptive)})
    else:
        return jsonify({"ok": False, "error": "Country must be US, UK, or IN"}), 422


def _us_freelance(gross, expenses, filing, state):
    net_profit  = gross - expenses
    # SE tax: 15.3% on 92.35% of net
    se_base     = net_profit * 0.9235
    se_tax      = se_base * 0.153
    se_deduct   = se_tax / 2  # deduct half of SE tax from income tax

    taxable_income = max(net_profit - se_deduct - US_STANDARD_DEDUCTION.get(filing, 15000), 0)
    income_tax, _ = _apply_brackets(taxable_income, US_TAX_BRACKETS.get(filing, US_TAX_BRACKETS["single"]))
    state_rate     = US_STATE_TAX.get(state, US_STATE_TAX["other"])
    state_tax      = net_profit * state_rate

    total_tax     = income_tax + se_tax + state_tax
    take_home     = net_profit - total_tax
    quarterly_est = total_tax / 4
    eff_rate      = (total_tax / gross * 100) if gross > 0 else 0

    due_dates = ["April 15", "June 16", "September 15", "January 15 (next yr)"]

    return {
        "net_profit":           round(net_profit, 2),
        "taxable_income":       round(taxable_income, 2),
        "income_tax":           round(income_tax, 2),
        "self_employment_tax":  round(se_tax, 2),
        "se_tax_deduction":     round(se_deduct, 2),
        "state_tax":            round(state_tax, 2),
        "total_tax":            round(total_tax, 2),
        "effective_rate":       round(eff_rate, 2),
        "take_home":            round(take_home, 2),
        "quarterly_estimate":   round(quarterly_est, 2),
        "quarterly_due_dates":  due_dates,
    }


def _uk_freelance(gross, expenses):
    net_profit = gross - expenses
    ni_cfg = UK_NI_SELF_EMPLOYED
    class2 = ni_cfg["class2_annual"] if net_profit > 12570 else 0

    class4 = 0
    if net_profit > ni_cfg["class4_lower"]:
        class4 += min(net_profit, ni_cfg["class4_upper"]) * ni_cfg["class4_rate_main"]
        class4 -= ni_cfg["class4_lower"] * ni_cfg["class4_rate_main"]
    if net_profit > ni_cfg["class4_upper"]:
        class4 += (net_profit - ni_cfg["class4_upper"]) * ni_cfg["class4_rate_upper"]

    pa = min(UK_PERSONAL_ALLOWANCE, UK_PERSONAL_ALLOWANCE - max(net_profit - UK_PA_TAPER_START, 0) / 2)
    taxable    = max(net_profit - pa, 0)
    income_tax, _ = _apply_brackets(taxable, UK_TAX_BRACKETS)

    total_tax  = income_tax + class2 + class4
    take_home  = net_profit - total_tax
    eff_rate   = (total_tax / gross * 100) if gross > 0 else 0

    return {
        "net_profit":           round(net_profit, 2),
        "taxable_income":       round(taxable, 2),
        "income_tax":           round(income_tax, 2),
        "uk_class2_nic":        round(class2, 2),
        "uk_class4_nic":        round(class4, 2),
        "total_tax":            round(total_tax, 2),
        "effective_rate":       round(eff_rate, 2),
        "take_home":            round(take_home, 2),
        "self_employment_tax":  round(class2 + class4, 2),
        "quarterly_estimate":   round(total_tax / 2, 2),  # UK: 2 payments on account
        "quarterly_due_dates":  ["January 31", "July 31"],
    }


def _india_freelance(gross, expenses, presumptive):
    if presumptive:
        # Section 44ADA: 50% of gross receipts treated as profit
        net_profit = gross * 0.50
    else:
        net_profit = gross - expenses

    cfg = INDIA_NEW_REGIME
    taxable  = max(net_profit - cfg["standard_deduction"], 0)
    base_tax, _ = _india_apply_brackets(taxable, cfg["brackets"])
    if taxable <= cfg["rebate_87a_limit"]:
        base_tax = 0
    surcharge = _india_surcharge(base_tax, net_profit)
    cess      = (base_tax + surcharge) * cfg["cess_rate"]
    total_tax = base_tax + surcharge + cess
    take_home = net_profit - total_tax
    eff_rate  = (total_tax / gross * 100) if gross > 0 else 0

    advance_tax = [
        {"due": "June 15",      "pct": 15, "amount": round(total_tax * 0.15, 2)},
        {"due": "September 15", "pct": 45, "amount": round(total_tax * 0.30, 2)},
        {"due": "December 15",  "pct": 75, "amount": round(total_tax * 0.30, 2)},
        {"due": "March 15",     "pct": 100,"amount": round(total_tax * 0.25, 2)},
    ]

    return {
        "net_profit":                    round(net_profit, 2),
        "taxable_income":                round(taxable, 2),
        "income_tax":                    round(base_tax, 2),
        "self_employment_tax":           0,
        "total_tax":                     round(total_tax, 2),
        "effective_rate":                round(eff_rate, 2),
        "take_home":                     round(take_home, 2),
        "quarterly_estimate":            round(total_tax / 4, 2),
        "india_advance_tax_schedule":    advance_tax,
        "quarterly_due_dates":           [d["due"] for d in advance_tax],
        "presumptive_scheme_used":       presumptive,
    }


# ── 15. Capital Gains Tax ─────────────────────────────────────────────────────

@tax_bp.route("/tax/capital-gains")
def capital_gains():
    return render_template("tax/capital_gains.html")


@tax_bp.route("/api/tax/capital-gains", methods=["POST"])
def api_capital_gains():
    data = request.get_json(force=True, silent=True) or {}
    try:
        country        = data.get("country", "US").upper()
        asset_type     = data.get("asset_type", "equity")
        purchase_price = float(data["purchase_price"])
        sale_price     = float(data["sale_price"])
        holding_months = float(data.get("holding_months", 13))
        annual_income  = float(data.get("annual_income", 75000))
        filing         = data.get("filing_status", "single").lower()
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    gross_gain = sale_price - purchase_price

    if country == "US":
        result = _us_cgt(gross_gain, annual_income, filing, holding_months, asset_type)
    elif country == "UK":
        result = _uk_cgt(gross_gain, annual_income, asset_type)
    elif country == "IN":
        result = _india_cgt(gross_gain, asset_type, holding_months)
    else:
        return jsonify({"ok": False, "error": "Country must be US, UK, or IN"}), 422

    return jsonify({"ok": True, "data": result})


def _us_cgt(gross_gain, income, filing, holding_months, asset_type):
    is_long_term = holding_months >= US_LTCG_HOLDING_MONTHS
    if not is_long_term:
        # Short-term: ordinary income rate
        taxable_income = income + gross_gain
        tax, _ = _apply_brackets(taxable_income, US_TAX_BRACKETS.get(filing, US_TAX_BRACKETS["single"]))
        base_tax_no_gain, _ = _apply_brackets(income, US_TAX_BRACKETS.get(filing, US_TAX_BRACKETS["single"]))
        gain_tax = tax - base_tax_no_gain
        rate = (gain_tax / gross_gain * 100) if gross_gain > 0 else 0
        label = "STCG"
    else:
        brackets = US_LTCG_BRACKETS.get(filing, US_LTCG_BRACKETS["single"])
        gain_tax = 0
        rate = 0
        for upper, r in brackets:
            if income <= upper:
                gain_tax = gross_gain * r
                rate     = r * 100
                break
        label = "LTCG"

    # NIIT
    niit_threshold = US_NIIT_THRESHOLD.get(filing, 200000)
    niit = max(income + gross_gain - niit_threshold, 0)
    niit = min(niit, gross_gain) * US_NIIT_RATE
    total_tax = gain_tax + niit

    return {
        "gain":           round(gross_gain, 2),
        "is_long_term":   is_long_term,
        "tax_rate":       round(rate, 1),
        "tax_owed":       round(total_tax, 2),
        "net_proceeds":   round(gross_gain - total_tax, 2),
        "classification": label,
        "regime_notes":   f"{'LTCG' if is_long_term else 'STCG (taxed as ordinary income)'}. NIIT: ${niit:,.2f}",
        "breakdown": {
            "gross_gain":    round(gross_gain, 2),
            "exemption":     0,
            "taxable_gain":  round(gross_gain, 2),
            "capital_gains_tax": round(gain_tax, 2),
            "niit":          round(niit, 2),
            "total_tax":     round(total_tax, 2),
        },
    }


def _uk_cgt(gross_gain, income, asset_type):
    exempt = UK_CGT["annual_exempt"]
    taxable_gain = max(gross_gain - exempt, 0)
    is_higher = income > UK_CGT["higher_rate_threshold"]
    rate = UK_CGT["higher_rate"] if is_higher else UK_CGT["basic_rate"]
    tax  = taxable_gain * rate

    return {
        "gain":           round(gross_gain, 2),
        "is_long_term":   True,
        "tax_rate":       round(rate * 100, 1),
        "tax_owed":       round(tax, 2),
        "net_proceeds":   round(gross_gain - tax, 2),
        "classification": "CGT",
        "regime_notes":   f"UK annual exempt amount £{exempt:,} deducted. Rate: {rate*100:.0f}% ({'higher' if is_higher else 'basic'} rate).",
        "breakdown": {
            "gross_gain":   round(gross_gain, 2),
            "exemption":    round(min(gross_gain, exempt), 2),
            "taxable_gain": round(taxable_gain, 2),
            "tax":          round(tax, 2),
        },
    }


def _india_cgt(gross_gain, asset_type, holding_months):
    if asset_type == "equity":
        threshold = INDIA_CGT["equity_holding_months"]
        is_lt = holding_months >= threshold
        if is_lt:
            exempt = INDIA_CGT["equity_ltcg_exemption"]
            taxable = max(gross_gain - exempt, 0)
            rate    = INDIA_CGT["equity_ltcg_rate"]
            label   = "LTCG"
        else:
            exempt  = 0
            taxable = gross_gain
            rate    = INDIA_CGT["equity_stcg_rate"]
            label   = "STCG"
    else:  # property or other
        threshold = INDIA_CGT["property_holding_months"]
        is_lt = holding_months >= threshold
        rate  = INDIA_CGT["property_ltcg_rate"] if is_lt else 0.30  # slab rate approx
        exempt = 0
        taxable = gross_gain
        label   = "LTCG" if is_lt else "STCG"

    tax = taxable * rate
    cess = tax * INDIA_NEW_REGIME["cess_rate"]
    total = tax + cess

    return {
        "gain":           round(gross_gain, 2),
        "is_long_term":   is_lt,
        "tax_rate":       round(rate * 100, 1),
        "tax_owed":       round(total, 2),
        "net_proceeds":   round(gross_gain - total, 2),
        "classification": label,
        "regime_notes":   f"India {label} on {asset_type}. 4% cess included. {'₹1.25L exemption applied for equity LTCG.' if asset_type=='equity' and is_lt else ''}",
        "breakdown": {
            "gross_gain":    round(gross_gain, 2),
            "exemption":     round(exempt, 2),
            "taxable_gain":  round(taxable, 2),
            "base_tax":      round(tax, 2),
            "cess":          round(cess, 2),
            "total_tax":     round(total, 2),
        },
    }
