"""
Central configuration: all financial rates, tax brackets, and CPI data.
Updated to 2025-26 values. Single source of truth for all calculators.
"""

SITE_URL = "https://finwise-calculators.onrender.com"  # update after deployment
SITE_NAME = "FinWise Calculators"

# ─── MORTGAGE RATES (2025) ───────────────────────────────────────────────────
MORTGAGE_RATES = {
    "US": {"30yr": 6.7, "15yr": 6.2, "label": "United States"},
    "UK": {"30yr": 4.8, "15yr": 4.3, "label": "United Kingdom"},
    "DE": {"30yr": 3.7, "15yr": 3.2, "label": "Germany"},
    "FR": {"30yr": 3.9, "15yr": 3.4, "label": "France"},
    "IN": {"30yr": 9.0, "15yr": 8.7, "label": "India"},
    "SG": {"30yr": 3.8, "15yr": 3.4, "label": "Singapore"},
    "JP": {"30yr": 1.0, "15yr": 0.8, "label": "Japan"},
    "CN": {"30yr": 3.5, "15yr": 3.2, "label": "China"},
}

# ─── US FEDERAL INCOME TAX (2025) ────────────────────────────────────────────
US_STANDARD_DEDUCTION = {
    "single": 15000,
    "mfj": 30000,
    "hoh": 22500,
}

# (upper_bound, rate) — last entry has float('inf')
US_TAX_BRACKETS = {
    "single": [
        (11925, 0.10),
        (48475, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250525, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
    "mfj": [
        (23850, 0.10),
        (96950, 0.12),
        (206700, 0.22),
        (394600, 0.24),
        (501050, 0.32),
        (751600, 0.35),
        (float("inf"), 0.37),
    ],
    "hoh": [
        (17000, 0.10),
        (64850, 0.12),
        (103350, 0.22),
        (197300, 0.24),
        (250500, 0.32),
        (626350, 0.35),
        (float("inf"), 0.37),
    ],
}

US_FICA = {
    "ss_rate": 0.062,
    "ss_wage_base": 176100,
    "medicare_rate": 0.0145,
    "additional_medicare_rate": 0.009,
    "additional_medicare_threshold_single": 200000,
    "additional_medicare_threshold_mfj": 250000,
}

# State income tax — simplified flat effective rates for major states
US_STATE_TAX = {
    "CA": 0.093,
    "NY": 0.0685,
    "NJ": 0.0637,
    "MA": 0.05,
    "IL": 0.0495,
    "TX": 0.0,
    "FL": 0.0,
    "WA": 0.0,
    "NV": 0.0,
    "AK": 0.0,
    "other": 0.05,
}

# ─── UK INCOME TAX (2025-26) ─────────────────────────────────────────────────
UK_PERSONAL_ALLOWANCE = 12570
UK_PA_TAPER_START = 100000
UK_PA_TAPER_END = 125140

# (upper_bound, rate) — income above personal allowance
UK_TAX_BRACKETS = [
    (50270, 0.20),
    (125140, 0.40),
    (float("inf"), 0.45),
]

UK_NI_EMPLOYEE = {
    "lower_earnings_limit": 6396,
    "upper_earnings_limit": 50270,
    "rate_main": 0.08,
    "rate_upper": 0.02,
}

UK_NI_SELF_EMPLOYED = {
    "class2_annual": 179,
    "class4_lower": 12570,
    "class4_upper": 50270,
    "class4_rate_main": 0.06,
    "class4_rate_upper": 0.02,
}

# ─── INDIA INCOME TAX (2025-26) ──────────────────────────────────────────────
INDIA_NEW_REGIME = {
    "standard_deduction": 75000,
    "brackets": [
        (400000, 0.0),
        (800000, 0.05),
        (1200000, 0.10),
        (1600000, 0.15),
        (2000000, 0.20),
        (2400000, 0.25),
        (float("inf"), 0.30),
    ],
    "rebate_87a_limit": 1200000,
    "cess_rate": 0.04,
}

INDIA_OLD_REGIME = {
    "standard_deduction": 50000,
    "brackets": [
        (250000, 0.0),
        (500000, 0.05),
        (1000000, 0.20),
        (float("inf"), 0.30),
    ],
    "rebate_87a_limit": 500000,
    "cess_rate": 0.04,
}

# Surcharge slabs (on top of income tax, India)
INDIA_SURCHARGE = [
    (5000000, 0.0),
    (10000000, 0.10),
    (20000000, 0.15),
    (50000000, 0.25),
    (float("inf"), 0.25),  # capped at 25% for new regime (post Budget 2023)
]

# ─── CAPITAL GAINS TAX (2025) ────────────────────────────────────────────────
US_LTCG_BRACKETS = {
    "single": [
        (48350, 0.0),
        (533400, 0.15),
        (float("inf"), 0.20),
    ],
    "mfj": [
        (96700, 0.0),
        (600050, 0.15),
        (float("inf"), 0.20),
    ],
}
US_NIIT_RATE = 0.038
US_NIIT_THRESHOLD = {"single": 200000, "mfj": 250000}
US_LTCG_HOLDING_MONTHS = 12

UK_CGT = {
    "annual_exempt": 3000,
    "basic_rate": 0.18,
    "higher_rate": 0.24,
    "higher_rate_threshold": 50270,
}

INDIA_CGT = {
    "equity_ltcg_rate": 0.125,
    "equity_ltcg_exemption": 125000,
    "equity_stcg_rate": 0.20,
    "property_ltcg_rate": 0.20,
    "other_ltcg_rate": 0.20,
    "equity_holding_months": 12,
    "property_holding_months": 24,
}

# ─── US STUDENT LOAN RATES (2025-26) ─────────────────────────────────────────
STUDENT_LOAN_RATES = {
    "undergrad": 6.53,
    "grad": 8.08,
    "parent_plus": 9.08,
}

# ─── CREDIT CARD / PERSONAL LOAN ─────────────────────────────────────────────
US_CC_AVG_APR = 21.5

# (min_score, max_score, apr_low, apr_high)
PERSONAL_LOAN_APR_MAP = [
    (750, 850, 7.5, 12.0),
    (720, 749, 12.0, 17.0),
    (680, 719, 17.0, 21.0),
    (640, 679, 21.0, 28.0),
    (580, 639, 28.0, 36.0),
    (300, 579, 36.0, 36.0),
]

CREDIT_SCORE_TIERS = [
    (750, "Excellent"),
    (720, "Very Good"),
    (680, "Good"),
    (640, "Fair"),
    (580, "Poor"),
    (0, "Very Poor"),
]

# ─── INVESTMENT PRESETS ───────────────────────────────────────────────────────
INVESTMENT_PRESETS = {
    "401k_employee_limit": 23500,
    "401k_total_limit": 70000,
    "401k_catchup_50_59": 7500,
    "401k_catchup_60_63": 11250,
    "ira_limit": 7000,
    "ira_catchup": 1000,
    "sip_nifty50": 12.0,
    "sip_large_cap": 11.0,
    "sip_mid_cap": 14.0,
    "sip_small_cap": 16.0,
    "fire_swr": 4.0,
    "sp500_avg_return": 10.0,
    "eu_stocks_avg": 7.0,
    "bonds_avg": 4.0,
    "default_inflation": 2.5,
    "default_investment_return": 7.0,
    "us_mortgage_30yr": 6.7,
    "fed_funds_rate": 4.375,
    "ecb_deposit_rate": 2.25,
}

# ─── US CPI DATA (annual average, BLS CPI-U, base 1982-84=100) ───────────────
US_CPI = {
    1913: 9.9,   1914: 10.0,  1915: 10.1,  1916: 10.9,  1917: 12.8,
    1918: 15.1,  1919: 17.3,  1920: 20.0,  1921: 17.9,  1922: 16.8,
    1923: 17.1,  1924: 17.1,  1925: 17.5,  1926: 17.7,  1927: 17.4,
    1928: 17.1,  1929: 17.1,  1930: 16.7,  1931: 15.2,  1932: 13.7,
    1933: 13.0,  1934: 13.4,  1935: 13.7,  1936: 13.9,  1937: 14.4,
    1938: 14.1,  1939: 13.9,  1940: 14.0,  1941: 14.7,  1942: 16.3,
    1943: 17.3,  1944: 17.6,  1945: 18.0,  1946: 19.5,  1947: 22.3,
    1948: 24.1,  1949: 23.8,  1950: 24.1,  1951: 26.0,  1952: 26.5,
    1953: 26.7,  1954: 26.9,  1955: 26.8,  1956: 27.2,  1957: 28.1,
    1958: 28.9,  1959: 29.1,  1960: 29.6,  1961: 29.9,  1962: 30.2,
    1963: 30.6,  1964: 31.0,  1965: 31.5,  1966: 32.4,  1967: 33.4,
    1968: 34.8,  1969: 36.7,  1970: 38.8,  1971: 40.5,  1972: 41.8,
    1973: 44.4,  1974: 49.3,  1975: 53.8,  1976: 56.9,  1977: 60.6,
    1978: 65.2,  1979: 72.6,  1980: 82.4,  1981: 90.9,  1982: 96.5,
    1983: 99.6,  1984: 103.9, 1985: 107.6, 1986: 109.6, 1987: 113.6,
    1988: 118.3, 1989: 124.0, 1990: 130.7, 1991: 136.2, 1992: 140.3,
    1993: 144.5, 1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5,
    1998: 163.0, 1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.9,
    2003: 184.0, 2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.3,
    2008: 215.3, 2009: 214.5, 2010: 218.1, 2011: 224.9, 2012: 229.6,
    2013: 233.0, 2014: 236.7, 2015: 237.0, 2016: 240.0, 2017: 245.1,
    2018: 251.1, 2019: 255.7, 2020: 258.8, 2021: 271.0, 2022: 292.7,
    2023: 304.7, 2024: 314.2,
}

# ─── EU HICP DATA (2015=100) ──────────────────────────────────────────────────
EU_HICP = {
    2000: 75.8,  2001: 77.6,  2002: 79.3,  2003: 80.9,  2004: 82.7,
    2005: 84.8,  2006: 86.9,  2007: 88.7,  2008: 91.5,  2009: 91.7,
    2010: 93.5,  2011: 96.2,  2012: 98.7,  2013: 99.9,  2014: 100.1,
    2015: 100.0, 2016: 100.2, 2017: 101.8, 2018: 103.6, 2019: 104.3,
    2020: 104.3, 2021: 108.0, 2022: 116.9, 2023: 124.6, 2024: 128.3,
}

# ─── INDIA CPI DATA (2012=100, General) ──────────────────────────────────────
INDIA_CPI = {
    2000: 55.2,  2001: 56.8,  2002: 59.2,  2003: 61.5,  2004: 63.0,
    2005: 65.8,  2006: 70.2,  2007: 75.3,  2008: 82.0,  2009: 91.4,
    2010: 100.0, 2011: 108.9, 2012: 117.3, 2013: 126.1, 2014: 133.3,
    2015: 137.9, 2016: 143.0, 2017: 149.0, 2018: 153.7, 2019: 158.6,
    2020: 164.8, 2021: 172.5, 2022: 185.2, 2023: 196.4, 2024: 204.1,
}

# ─── SITEMAP PAGES ────────────────────────────────────────────────────────────
SITEMAP_PAGES = [
    ("/", 1.0, "daily"),
    ("/mortgage/repayment", 0.9, "monthly"),
    ("/mortgage/rent-vs-buy", 0.9, "monthly"),
    ("/mortgage/refinance", 0.9, "monthly"),
    ("/mortgage/affordability", 0.9, "monthly"),
    ("/investment/compound-interest", 0.9, "monthly"),
    ("/investment/401k-pension", 0.9, "monthly"),
    ("/investment/sip", 0.9, "monthly"),
    ("/investment/fire", 0.9, "monthly"),
    ("/debt/student-loan", 0.9, "monthly"),
    ("/debt/credit-card", 0.9, "monthly"),
    ("/debt/auto-loan", 0.9, "monthly"),
    ("/debt/personal-loan", 0.9, "monthly"),
    ("/tax/take-home-pay", 0.9, "monthly"),
    ("/tax/freelance", 0.9, "monthly"),
    ("/tax/capital-gains", 0.9, "monthly"),
    ("/specialized/inflation", 0.8, "monthly"),
    ("/specialized/rule-of-72", 0.8, "monthly"),
    ("/specialized/latte-factor", 0.8, "monthly"),
]
