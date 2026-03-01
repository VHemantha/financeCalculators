"""
Budget Planner Calculator — comprehensive budget analysis.
Supports 6 budgeting methods:
  1. 50/30/20 Rule
  2. Zero-Based Budgeting (ZBB)
  3. 80/20 (Pay Yourself First)
  4. Envelope Method
  5. 60% Solution
  6. Reverse Budget
"""
from flask import Blueprint, jsonify, render_template, request

budget_bp = Blueprint("budget", __name__)

# ── Category definitions ──────────────────────────────────────────────────────
# Each expense key maps to (label, bucket)
# bucket: "need" | "want" | "saving" | "debt"
EXPENSE_META = {
    # Housing
    "housing_rent":        ("Rent / Mortgage",        "need"),
    "housing_hoa":         ("HOA / Strata Fees",       "need"),
    "housing_insurance":   ("Home / Renters Insurance","need"),
    "housing_maintenance": ("Maintenance & Repairs",   "need"),
    # Utilities
    "util_electricity":    ("Electricity",             "need"),
    "util_gas":            ("Gas / Heating",           "need"),
    "util_water":          ("Water / Sewage",          "need"),
    "util_internet":       ("Internet",                "need"),
    "util_phone":          ("Mobile Phone",            "need"),
    # Transport
    "trans_car_payment":   ("Car Payment / Lease",     "need"),
    "trans_fuel":          ("Fuel / Gas",              "need"),
    "trans_car_insurance": ("Car Insurance",           "need"),
    "trans_maintenance":   ("Car Maintenance",         "need"),
    "trans_public":        ("Public Transport",        "need"),
    "trans_rideshare":     ("Ride-share / Taxi",       "want"),
    "trans_parking":       ("Parking / Tolls",         "need"),
    # Food
    "food_groceries":      ("Groceries",               "need"),
    "food_dining":         ("Dining Out / Takeaway",   "want"),
    "food_work_lunch":     ("Work Lunches / Coffee",   "want"),
    # Health
    "health_insurance":    ("Health Insurance",        "need"),
    "health_prescriptions":("Prescriptions / OTC",     "need"),
    "health_dental":       ("Dental / Vision",         "need"),
    "health_gym":          ("Gym / Fitness",           "want"),
    "health_therapy":      ("Therapy / Counselling",   "need"),
    # Insurance (non-health)
    "ins_life":            ("Life Insurance",          "need"),
    "ins_disability":      ("Disability Insurance",    "need"),
    # Debt repayments
    "debt_student":        ("Student Loan Payment",    "debt"),
    "debt_credit_card":    ("Credit Card Payment",     "debt"),
    "debt_personal":       ("Personal Loan Payment",   "debt"),
    "debt_other":          ("Other Debt Payment",      "debt"),
    # Savings & Investments
    "sav_emergency":       ("Emergency Fund",          "saving"),
    "sav_retirement":      ("Retirement (401k/IRA)",   "saving"),
    "sav_investments":     ("Stocks / Index Funds",    "saving"),
    "sav_house":           ("House / Property Fund",   "saving"),
    "sav_education":       ("Education Fund (529)",    "saving"),
    "sav_other":           ("Other Savings Goal",      "saving"),
    # Personal care
    "pers_clothing":       ("Clothing & Shoes",        "want"),
    "pers_grooming":       ("Hair / Personal Care",    "want"),
    # Entertainment & Lifestyle
    "ent_streaming":       ("Streaming & Subscriptions","want"),
    "ent_hobbies":         ("Hobbies & Sports",        "want"),
    "ent_events":          ("Events / Concerts",       "want"),
    "ent_gaming":          ("Gaming",                  "want"),
    "ent_books":           ("Books / Magazines",       "want"),
    "ent_travel":          ("Travel & Vacations",      "want"),
    # Family & Children
    "fam_childcare":       ("Childcare / Daycare",     "need"),
    "fam_school":          ("School / Tuition Fees",   "need"),
    "fam_allowance":       ("Children's Allowance",    "want"),
    "fam_pets":            ("Pets (food, vet, etc.)",  "want"),
    # Giving
    "give_charity":        ("Charity / Donations",     "want"),
    "give_gifts":          ("Gifts (birthdays, etc.)", "want"),
    # Education (self)
    "edu_courses":         ("Online Courses / Training","want"),
    # Other
    "other_misc":          ("Miscellaneous",           "want"),
}

INCOME_KEYS = [
    ("inc_primary",    "Primary Salary / Wages"),
    ("inc_secondary",  "Secondary Job / Part-time"),
    ("inc_freelance",  "Freelance / Self-employed"),
    ("inc_rental",     "Rental Income"),
    ("inc_dividends",  "Dividends / Interest"),
    ("inc_government", "Government Benefits"),
    ("inc_other",      "Other Income"),
]


def _safe_float(data, key, default=0.0):
    try:
        return max(0.0, float(data.get(key, default) or 0))
    except (TypeError, ValueError):
        return default


def _analyse(total_income, buckets, all_expenses, total_expenses):
    """Return analysis for all 6 budgeting methods."""
    needs   = buckets["need"]
    wants   = buckets["want"]
    savings = buckets["saving"]
    debt    = buckets["debt"]

    # For most methods, debt is grouped with needs
    needs_and_debt = needs + debt

    surplus = total_income - total_expenses

    # Ratios (actual)
    savings_rate    = savings / total_income * 100 if total_income else 0
    housing_ratio   = all_expenses.get("housing_rent", 0) / total_income * 100 if total_income else 0
    debt_payments   = debt
    dti             = debt_payments / total_income * 100 if total_income else 0
    needs_pct_actual  = needs_and_debt / total_income * 100 if total_income else 0
    wants_pct_actual  = wants / total_income * 100 if total_income else 0
    savings_pct_actual = savings / total_income * 100 if total_income else 0

    def _method_status(actual_pct, target_pct, higher_is_ok=False):
        diff = actual_pct - target_pct
        if abs(diff) <= 2:
            return "on_track"
        if higher_is_ok:
            return "on_track" if diff >= 0 else "under"
        return "over" if diff > 0 else "under"

    # ── Method targets ─────────────────────────────────────────────────────────
    methods = {
        "50_30_20": {
            "name": "50/30/20 Rule",
            "description": "50% needs, 30% wants, 20% savings. The most popular budgeting rule for building wealth while enjoying life.",
            "targets": {"needs": 50, "wants": 30, "savings": 20},
            "allocated": {
                "needs":   round(total_income * 0.50, 2),
                "wants":   round(total_income * 0.30, 2),
                "savings": round(total_income * 0.20, 2),
            },
            "actual": {
                "needs":   round(needs_and_debt, 2),
                "wants":   round(wants, 2),
                "savings": round(savings, 2),
            },
            "status": {
                "needs":   _method_status(needs_pct_actual, 50),
                "wants":   _method_status(wants_pct_actual, 30),
                "savings": _method_status(savings_pct_actual, 20, higher_is_ok=True),
            },
            "surplus_after": round(surplus, 2),
        },
        "80_20": {
            "name": "80/20 (Pay Yourself First)",
            "description": "Save 20% immediately when you're paid. Spend the remaining 80% on everything else with no further tracking needed.",
            "targets": {"savings": 20, "everything_else": 80},
            "allocated": {
                "savings":        round(total_income * 0.20, 2),
                "everything_else": round(total_income * 0.80, 2),
            },
            "actual": {
                "savings":        round(savings, 2),
                "everything_else": round(needs_and_debt + wants, 2),
            },
            "status": {
                "savings":        _method_status(savings_pct_actual, 20, higher_is_ok=True),
                "everything_else": _method_status((needs_and_debt + wants) / total_income * 100 if total_income else 0, 80),
            },
            "surplus_after": round(surplus, 2),
        },
        "zero_based": {
            "name": "Zero-Based Budget (ZBB)",
            "description": "Every dollar of income is assigned a job. Income minus all allocations = $0. Maximum control and awareness.",
            "targets": {"assigned": 100, "unassigned": 0},
            "allocated": {
                "needs":   round(needs_and_debt, 2),
                "wants":   round(wants, 2),
                "savings": round(savings, 2),
            },
            "unassigned": round(surplus, 2),
            "total_assigned": round(total_expenses, 2),
            "surplus_after": round(surplus, 2),
        },
        "60_solution": {
            "name": "60% Solution",
            "description": "60% committed expenses (all must-pays), 10% retirement, 10% long-term savings, 10% short-term savings, 10% fun money.",
            "targets": {
                "committed":   60,
                "retirement":  10,
                "long_term":   10,
                "short_term":  10,
                "fun":         10,
            },
            "allocated": {
                "committed":  round(total_income * 0.60, 2),
                "retirement": round(total_income * 0.10, 2),
                "long_term":  round(total_income * 0.10, 2),
                "short_term": round(total_income * 0.10, 2),
                "fun":        round(total_income * 0.10, 2),
            },
            "actual": {
                "committed": round(needs_and_debt, 2),
                "savings":   round(savings, 2),
                "fun":       round(wants, 2),
            },
            "committed_pct": round(needs_pct_actual, 1),
            "surplus_after": round(surplus, 2),
        },
        "envelope": {
            "name": "Envelope Method",
            "description": "Assign cash to physical (or digital) envelopes per category. When the envelope is empty, spending stops. Zero overspending.",
            "envelopes": [
                {
                    "name":   meta[0],
                    "bucket": meta[1],
                    "amount": round(all_expenses.get(key, 0), 2),
                }
                for key, meta in EXPENSE_META.items()
                if all_expenses.get(key, 0) > 0
            ],
            "total_envelopes": round(total_expenses, 2),
            "surplus_after":   round(surplus, 2),
        },
        "reverse": {
            "name": "Reverse Budget",
            "description": "Define your savings goals first, then pay bills, then spend whatever is left guilt-free. Goals are non-negotiable.",
            "steps": [
                {"step": 1, "label": "Income",                     "amount": round(total_income, 2)},
                {"step": 2, "label": "Minus Savings & Investments", "amount": -round(savings, 2)},
                {"step": 3, "label": "Minus Fixed Bills (Needs)",   "amount": -round(needs_and_debt, 2)},
                {"step": 4, "label": "Guilt-Free Spending",         "amount": round(total_income - savings - needs_and_debt, 2)},
            ],
            "guilt_free_spending": round(total_income - savings - needs_and_debt, 2),
            "surplus_after": round(surplus, 2),
        },
    }

    # ── Key financial health indicators ────────────────────────────────────────
    emergency_fund_target_3mo  = round(needs_and_debt * 3, 2)
    emergency_fund_target_6mo  = round(needs_and_debt * 6, 2)
    fire_number                = round(total_expenses * 12 * 25, 2)
    months_to_fire_years       = None
    if savings > 0:
        # Very rough: how many years to reach FIRE at current monthly savings + 7% return
        # Using FV formula: FV = PMT * ((1+r)^n - 1) / r  →  solve for n
        import math
        r = 0.07 / 12  # 7% annual / monthly
        fv = fire_number
        pmt = savings
        if pmt > 0 and r > 0:
            try:
                n = math.log(1 + fv * r / pmt) / math.log(1 + r)
                months_to_fire_years = round(n / 12, 1)
            except (ValueError, ZeroDivisionError):
                months_to_fire_years = None

    health = {
        "savings_rate_pct":           round(savings_rate, 1),
        "savings_rate_status":        "excellent" if savings_rate >= 20 else ("good" if savings_rate >= 10 else ("fair" if savings_rate >= 5 else "low")),
        "housing_ratio_pct":          round(housing_ratio, 1),
        "housing_ratio_status":       "good" if housing_ratio <= 28 else ("caution" if housing_ratio <= 36 else "high"),
        "debt_to_income_pct":         round(dti, 1),
        "dti_status":                 "good" if dti <= 15 else ("caution" if dti <= 36 else "high"),
        "emergency_fund_target_3mo":  emergency_fund_target_3mo,
        "emergency_fund_target_6mo":  emergency_fund_target_6mo,
        "fire_number":                fire_number,
        "years_to_fire":              months_to_fire_years,
        "monthly_surplus":            round(surplus, 2),
        "surplus_status":             "surplus" if surplus > 0 else ("balanced" if surplus == 0 else "deficit"),
    }

    return methods, health


# ── Route ─────────────────────────────────────────────────────────────────────

@budget_bp.route("/budget")
def budget():
    return render_template("budget/budget_planner.html",
                           expense_meta=EXPENSE_META,
                           income_keys=INCOME_KEYS)


@budget_bp.route("/api/budget", methods=["POST"])
def api_budget():
    data = request.get_json(force=True, silent=True) or {}

    # Income
    total_income = sum(_safe_float(data, k) for k, _ in INCOME_KEYS)
    if total_income <= 0:
        return jsonify({"ok": False, "error": "Total income must be greater than zero"}), 422

    # Expenses
    all_expenses = {k: _safe_float(data, k) for k in EXPENSE_META}
    total_expenses = sum(all_expenses.values())

    # Bucket totals
    buckets = {"need": 0.0, "want": 0.0, "saving": 0.0, "debt": 0.0}
    for key, (_, bucket) in EXPENSE_META.items():
        buckets[bucket] += all_expenses[key]

    methods, health = _analyse(total_income, buckets, all_expenses, total_expenses)

    # Category breakdown for chart (non-zero only)
    breakdown = [
        {"key": k, "label": EXPENSE_META[k][0], "bucket": EXPENSE_META[k][1], "amount": round(v, 2)}
        for k, v in all_expenses.items() if v > 0
    ]
    breakdown.sort(key=lambda x: -x["amount"])

    return jsonify({"ok": True, "data": {
        "income": {
            "total":    round(total_income, 2),
            "breakdown": {k: round(_safe_float(data, k), 2) for k, _ in INCOME_KEYS if _safe_float(data, k) > 0},
        },
        "expenses": {
            "total":    round(total_expenses, 2),
            "needs":    round(buckets["need"], 2),
            "wants":    round(buckets["want"], 2),
            "savings":  round(buckets["saving"], 2),
            "debt":     round(buckets["debt"], 2),
            "breakdown": breakdown,
        },
        "methods": methods,
        "health":  health,
        "monthly_surplus": round(total_income - total_expenses, 2),
        "annual_surplus":  round((total_income - total_expenses) * 12, 2),
    }})
