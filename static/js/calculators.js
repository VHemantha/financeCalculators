/**
 * FinWise Calculators — FC.calculators namespace
 * All 18 calculator modules. Each module has init(), preview(), calculate(), renderResults().
 * Initialized from main.js via: FC.calculators[page].init()
 */

// ── Shared Helpers ─────────────────────────────────────────────────────────────

/** Serialize all form fields to a plain object (string values). */
function _fv(form) {
  const o = {};
  new FormData(form).forEach((v, k) => { o[k] = v; });
  return o;
}

const _n  = v => parseFloat(v)  || 0;
const _ni = v => parseInt(v, 10) || 0;

/** Standard annuity formula: monthly payment. Returns 0 if rate=0. */
function _pmt(principal, annualRatePct, termMonths) {
  if (annualRatePct <= 0) return termMonths > 0 ? principal / termMonths : 0;
  const r = annualRatePct / 100 / 12;
  return principal * (r * Math.pow(1 + r, termMonths)) / (Math.pow(1 + r, termMonths) - 1);
}

/** Attach debounced input + async submit handlers to a form. */
function _initForm(formId, previewFn, calcFn) {
  const form = document.getElementById(formId);
  if (!form) return null;
  form.addEventListener('input', FC.debounce(() => previewFn(form), 200));
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('[type=submit]');
    FC.setLoading(btn, true);
    try { await calcFn(form); }
    catch (err) { FC.showError('results-container', err.message); }
    finally { FC.setLoading(btn, false); }
  });
  previewFn(form);
  return form;
}

/** Tab group — clicks update a hidden input and optionally trigger a callback. */
function _initTabGroup(groupId, hiddenId, dataKey, onSwitch) {
  const group = document.getElementById(groupId);
  if (!group) return;
  const hidden = document.getElementById(hiddenId);
  group.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      group.querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      const val = btn.dataset[dataKey] || btn.textContent.trim();
      if (hidden) hidden.value = val;
      if (onSwitch) onSwitch(val, btn);
    });
  });
}

/** Show one section, hide others. sectionMap = {value: elementId}. */
function _showSection(value, sectionMap) {
  Object.entries(sectionMap).forEach(([k, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden', k !== value);
  });
}

/** Build a big primary result card (green). */
function _bigCard(label, value, sub = '') {
  return `<div class="result-card result-card--highlight">
    <div class="result-card__label">${label}</div>
    <div class="result-card__value">${value}</div>
    ${sub ? `<div class="result-card__sub">${sub}</div>` : ''}
  </div>`;
}

/** Build a yellow variant of the primary result card. */
function _bigCardY(label, value, sub = '') {
  return `<div class="result-card result-card--yellow">
    <div class="result-card__label">${label}</div>
    <div class="result-card__value">${value}</div>
    ${sub ? `<div class="result-card__sub">${sub}</div>` : ''}
  </div>`;
}

/** Stat card in the 2-col result grid. color = 'green'|'yellow'|'red'|'' */
function _stat(label, value, color = '') {
  return `<div class="result-stat">
    <div class="result-stat__label">${label}</div>
    <div class="result-stat__value ${color}">${value}</div>
  </div>`;
}

/** A breakdown row (label / value). */
function _row(label, value, color = '') {
  return `<div class="breakdown-row">
    <span class="breakdown-row__label">${label}</span>
    <span class="breakdown-row__value ${color}">${value}</span>
  </div>`;
}

/** Canvas element inside a chart-wrap with optional title. */
function _chartWrap(id, title = '') {
  return `<div class="chart-wrap">
    ${title ? `<div class="chart-wrap__title">${title}</div>` : ''}
    <div class="chart-container"><canvas id="${id}"></canvas></div>
  </div>`;
}

/** Currency formatting shorthand. */
const $  = (v, cur = 'USD', dec = 0) => FC.fmt.currency(v, cur, dec);
const $2 = (v, cur = 'USD')          => FC.fmt.currency(v, cur, 2);
const pct = (v, d = 1)               => FC.fmt.percent(v, d);
const compact = (v, cur = 'USD')      => FC.fmt.compact(v, cur);

// ── 1. Mortgage Repayment ──────────────────────────────────────────────────────

FC.calculators.mortgage = {
  _regionPresets: {
    US:     { rate: 6.7, sym: '$',   label: 'USD' },
    UK:     { rate: 4.8, sym: '£',   label: 'GBP' },
    DE:     { rate: 3.7, sym: '€',   label: 'EUR' },
    IN:     { rate: 9.0, sym: '₹',   label: 'INR' },
    SG:     { rate: 3.8, sym: 'S$',  label: 'SGD' },
    JP:     { rate: 1.0, sym: '¥',   label: 'JPY' },
    custom: null,
  },

  init() {
    const form = document.getElementById('mortgage-form');
    if (!form) return;

    // Region select — auto-fill rate + currency symbol
    form.querySelector('#region')?.addEventListener('change', e => {
      const p = this._regionPresets[e.target.value];
      if (p) {
        form.querySelector('#annual_rate').value = p.rate;
        const sym = document.getElementById('currency-symbol');
        const dp  = document.getElementById('dp-symbol');
        const lbl = document.getElementById('preview-label-currency');
        if (sym) sym.textContent = p.sym;
        if (dp)  dp.textContent  = p.sym;
        if (lbl) lbl.textContent = p.label;
      }
      this.preview(form);
    });

    // Down payment % display
    ['#principal', '#down_payment'].forEach(sel =>
      form.querySelector(sel)?.addEventListener('input', () => {
        const price = _n(form.querySelector('#principal')?.value);
        const dp    = _n(form.querySelector('#down_payment')?.value);
        const el    = document.getElementById('dp-pct-display');
        if (el && price > 0) el.textContent = ((dp / price) * 100).toFixed(0) + '%';
      })
    );

    _initForm('mortgage-form',
      f => this.preview(f),
      f => this.calculate(f)
    );
  },

  preview(form) {
    const f    = _fv(form);
    const loan = _n(f.principal) - _n(f.down_payment);
    if (loan <= 0) { FC.setText('preview-monthly', '—'); return; }
    const payment = _pmt(loan, _n(f.annual_rate), _ni(f.term_years) * 12);
    FC.setText('preview-monthly', $2(payment));
  },

  async calculate(form) {
    const f    = _fv(form);
    const loan = _n(f.principal) - _n(f.down_payment);
    if (loan <= 0) throw new Error('Loan amount must be positive after down payment');
    const { data } = await FC.api.post('/api/mortgage/repayment', {
      principal:   loan,
      annual_rate: _n(f.annual_rate),
      term_years:  _ni(f.term_years),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const html = `<div class="results-panel">
      ${_bigCard('Monthly Payment', $2(d.monthly_payment), `${d.effective_rate}% annual interest`)}
      <div class="result-grid">
        ${_stat('Total Interest',  $(d.total_interest), 'yellow')}
        ${_stat('Total Cost',      $(d.total_paid))}
      </div>
      <div class="result-card">
        ${_row('Principal (Loan Amount)', $(d.total_paid - d.total_interest))}
        ${_row('Interest Over Life', $(d.total_interest), 'yellow')}
        ${_row('Total Repaid', $(d.total_paid))}
      </div>
      ${_chartWrap('mortgage-amort-chart', 'Amortization by Year — Principal vs Interest')}
      <div class="table-wrap">
        <div class="table-title">Amortization Schedule</div>
        <table class="data-table">
          <thead><tr><th>Year</th><th>Principal Paid</th><th>Interest Paid</th><th>Balance</th></tr></thead>
          <tbody>
            ${d.summary_by_year.slice(0, 5).map(r =>
              `<tr><td>Yr ${r.year}</td><td>${$2(r.principal_paid)}</td><td>${$2(r.interest_paid)}</td><td>${$(r.balance)}</td></tr>`
            ).join('')}
            ${d.summary_by_year.length > 8 ? '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:8px">⋯</td></tr>' : ''}
            ${d.summary_by_year.slice(-3).map(r =>
              `<tr><td>Yr ${r.year}</td><td>${$2(r.principal_paid)}</td><td>${$2(r.interest_paid)}</td><td>${$(r.balance)}</td></tr>`
            ).join('')}
          </tbody>
        </table>
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.summary_by_year;
    FC.chart.bar('mortgage-amort-chart', yrs.map(r => `Y${r.year}`), [
      { label: 'Principal', data: yrs.map(r => r.principal_paid), backgroundColor: FC.COLORS.green },
      { label: 'Interest',  data: yrs.map(r => r.interest_paid),  backgroundColor: FC.COLORS.yellow },
    ], { scales: { x: { stacked: true }, y: { stacked: true,
      ticks: { callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0)+'K' : v) }
    }}});
  },
};

// ── 2. Rent vs Buy ─────────────────────────────────────────────────────────────

FC.calculators.rentVsBuy = {
  init() {
    _initForm('rentVsBuy-form',
      _f => {},        // no preview panel
      f  => this.calculate(f)
    );
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/mortgage/rent-vs-buy', {
      home_price:           _n(f.home_price),
      down_payment_pct:     _n(f.down_payment_pct),
      mortgage_rate:        _n(f.mortgage_rate),
      annual_home_growth:   _n(f.annual_home_growth),
      monthly_rent:         _n(f.monthly_rent),
      annual_rent_increase: _n(f.annual_rent_increase),
      investment_return:    _n(f.investment_return),
      property_tax_rate:    _n(f.property_tax_rate),
      years:                _ni(f.years),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const recColor = { BUY: 'green', RENT: 'yellow', NEUTRAL: '' };
    const recLabel = { BUY: '🏠 Buy is Better', RENT: '🏘 Rent is Better', NEUTRAL: '⚖️ Roughly Equal' };
    const beText   = d.breakeven_year ? `Break-even at year ${d.breakeven_year}` : 'Buying does not break even in this period';

    const html = `<div class="results-panel">
      <div class="result-card result-card--${recColor[d.recommendation] || 'highlight'}">
        <div class="result-card__label">Recommendation</div>
        <div class="result-card__value" style="font-size:1.6rem">${recLabel[d.recommendation]}</div>
        <div class="result-card__sub">${beText}</div>
      </div>
      <div class="result-grid">
        ${_stat('Buyer Net Worth', compact(d.buy_net_worth_at_horizon),  'green')}
        ${_stat('Renter Net Worth', compact(d.rent_net_worth_at_horizon), 'yellow')}
      </div>
      ${_chartWrap('rvb-chart', 'Net Worth Comparison Over Time')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_comparison;
    FC.chart.line('rvb-chart', yrs.map(r => `Yr ${r.year}`), [
      { label: '🏠 Buy Net Worth',  data: yrs.map(r => r.buy_net_worth),  borderColor: FC.COLORS.green,
        backgroundColor: FC.COLORS.greenFade, fill: false, tension: 0.3 },
      { label: '🏘 Rent Net Worth', data: yrs.map(r => r.rent_net_worth), borderColor: FC.COLORS.yellow,
        backgroundColor: FC.COLORS.yellowFade, fill: false, tension: 0.3 },
    ], { scales: { y: { ticks: { callback: v => '$' + (v/1000).toFixed(0)+'K' }}}});
  },
};

// ── 3. Mortgage Refinance ─────────────────────────────────────────────────────

FC.calculators.refinance = {
  init() {
    _initForm('refinance-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/mortgage/refinance', {
      current_balance:         _n(f.current_balance),
      current_rate:            _n(f.current_rate),
      current_remaining_years: _n(f.current_remaining_years),
      new_rate:                _n(f.new_rate),
      new_term_years:          _n(f.new_term_years),
      closing_costs:           _n(f.closing_costs),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const isGood    = d.recommendation === 'REFINANCE';
    const beText    = d.breakeven_months
      ? FC.fmt.months(d.breakeven_months) + ' to recoup closing costs'
      : 'Closing costs never recouped — not recommended';
    const netSavingsColor = d.net_savings > 0 ? 'green' : 'red';

    const html = `<div class="results-panel">
      <div class="result-card ${isGood ? 'result-card--highlight' : 'result-card--yellow'}">
        <div class="result-card__label">Recommendation</div>
        <div class="result-card__value" style="font-size:1.5rem">${isGood ? '✅ Refinance' : '⏸ Stay with Current Loan'}</div>
        <div class="result-card__sub">${beText}</div>
      </div>
      <div class="result-grid">
        ${_stat('Current Monthly',  $2(d.current_monthly))}
        ${_stat('New Monthly',      $2(d.new_monthly), 'green')}
        ${_stat('Monthly Savings',  $2(d.monthly_savings), d.monthly_savings > 0 ? 'green' : 'red')}
        ${_stat('Net Lifetime Savings', $(d.net_savings), netSavingsColor)}
      </div>
      <div class="result-card">
        ${_row('Interest (current loan)',  $(d.total_interest_current))}
        ${_row('Interest (new loan)',      $(d.total_interest_new), 'green')}
        ${_row('Net Savings', $(d.net_savings), netSavingsColor)}
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 4. Home Affordability ─────────────────────────────────────────────────────

FC.calculators.affordability = {
  init() {
    _initForm('affordability-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/mortgage/affordability', {
      gross_annual_income: _n(f.gross_annual_income),
      monthly_debts:       _n(f.monthly_debts),
      down_payment:        _n(f.down_payment),
      annual_rate:         _n(f.annual_rate),
      term_years:          _ni(f.term_years),
      property_tax_rate:   _n(f.property_tax_rate),
      insurance_monthly:   _n(f.insurance_monthly),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const statusColor = { GOOD: 'green', CAUTION: 'yellow', HIGH: 'red' };
    const statusLabel = { GOOD: '✅ Good DTI', CAUTION: '⚠️ Caution', HIGH: '❌ High DTI' };

    const html = `<div class="results-panel">
      ${_bigCard('Maximum Home Price', $(d.max_home_price), `Based on stricter of 28% / 36% DTI rules`)}
      <div class="result-grid">
        ${_stat('28% Rule (Front-end)', $(d.max_home_price_28pct), 'green')}
        ${_stat('36% Rule (Back-end)',  $(d.max_home_price_36pct), 'yellow')}
        ${_stat('Max Monthly PITI',     $2(d.max_monthly_piti))}
        ${_stat('Monthly Income',       $2(d.monthly_income))}
      </div>
      <div class="result-card">
        <div class="result-card__label">DTI Status</div>
        <div class="result-card__value ${statusColor[d.dti_status]}" style="font-size:1.5rem">${statusLabel[d.dti_status]}</div>
        <div class="result-card__sub">Current debt-to-income ratio: ${d.current_dti}%</div>
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 5. Compound Interest ──────────────────────────────────────────────────────

FC.calculators.compoundInterest = {
  init() {
    const form = document.getElementById('compoundInterest-form');
    if (!form) return;

    // Rate preset tabs
    document.getElementById('ci-presets')?.querySelectorAll('.tab').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('ci-presets').querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        form.querySelector('#ci-rate').value = btn.dataset.rate;
        this.preview(form);
      });
    });

    _initForm('compoundInterest-form', f => this.preview(f), f => this.calculate(f));
  },

  preview(form) {
    const f = _fv(form);
    const P = _n(f.principal), pmt = _n(f.monthly_addition);
    const r = _n(f.annual_rate) / 100 / 12;
    const n = _ni(f.years) * 12;
    if (n <= 0) { FC.setText('preview-monthly', '—'); return; }
    const fv = r > 0
      ? P * Math.pow(1 + r, n) + pmt * (Math.pow(1 + r, n) - 1) / r
      : P + pmt * n;
    FC.setText('preview-monthly', compact(fv));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/investment/compound-interest', {
      principal:        _n(f.principal),
      monthly_addition: _n(f.monthly_addition),
      annual_rate:      _n(f.annual_rate),
      years:            _ni(f.years),
      compound_freq:    f.compound_freq || 'monthly',
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const html = `<div class="results-panel">
      ${_bigCard('Final Balance', compact(d.final_balance), `Effective APY: ${pct(d.effective_apy, 3)}`)}
      <div class="result-grid">
        ${_stat('Total Invested',  compact(d.total_contributed))}
        ${_stat('Interest Earned', compact(d.total_interest), 'green')}
      </div>
      ${_chartWrap('ci-chart', 'Investment Growth Over Time')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_breakdown;
    FC.chart.bar('ci-chart', yrs.map(r => `Yr ${r.year}`), [
      { label: 'Contributions', data: yrs.map(r => r.contributed),  backgroundColor: FC.COLORS.muted },
      { label: 'Interest',      data: yrs.map(r => Math.max(r.interest, 0)), backgroundColor: FC.COLORS.green },
    ], { scales: { x: { stacked: true }, y: { stacked: true,
      ticks: { callback: v => '$'+(v/1000).toFixed(0)+'K' }
    }}});
  },
};

// ── 6. 401(k) / Pension Planner ───────────────────────────────────────────────

FC.calculators.pension401k = {
  init() {
    _initForm('pension401k-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/investment/401k-pension', {
      current_age:         _ni(f.current_age),
      retirement_age:      _ni(f.retirement_age),
      current_balance:     _n(f.current_balance),
      annual_salary:       _n(f.annual_salary),
      contribution_pct:    _n(f.contribution_pct),
      employer_match_pct:  _n(f.employer_match_pct),
      employer_match_limit:_n(f.employer_match_limit),
      expected_return:     _n(f.expected_return),
      inflation_rate:      _n(f.inflation_rate),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const warn = d.irs_limit_warning
      ? `<div class="alert alert--warning" style="margin:0">⚠ Your contribution exceeds the 2025 IRS limit of $23,500. The calculation uses the capped amount.</div>`
      : '';

    const html = `<div class="results-panel">
      ${warn}
      ${_bigCard('Projected 401(k) Balance', compact(d.projected_balance),
        `${d.years_to_retirement} years to retirement`)}
      <div class="result-grid">
        ${_stat('Real Value (Inflation-Adj.)', compact(d.projected_balance_real), 'yellow')}
        ${_stat('Monthly Income (4% Rule)',    $2(d.monthly_income_4pct), 'green')}
        ${_stat('Your Annual Contribution',    $(d.annual_employee_contribution))}
        ${_stat('Employer Annual Match',       $(d.annual_employer_contribution), 'green')}
      </div>
      ${_chartWrap('pk-chart', 'Balance Growth — Nominal vs Real')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_growth;
    FC.chart.line('pk-chart', yrs.map(r => `Age ${r.age}`), [
      { label: 'Nominal Balance', data: yrs.map(r => r.balance),      borderColor: FC.COLORS.green,
        backgroundColor: FC.COLORS.greenFade, fill: true, tension: 0.3 },
      { label: 'Real Balance',    data: yrs.map(r => r.real_balance),  borderColor: FC.COLORS.yellow,
        backgroundColor: FC.COLORS.yellowFade, fill: false, tension: 0.3 },
    ], { scales: { y: { ticks: { callback: v => '$'+(v/1000).toFixed(0)+'K' }}}});
  },
};

// ── 7. SIP Calculator ─────────────────────────────────────────────────────────

FC.calculators.sip = {
  init() {
    const form = document.getElementById('sip-form');
    if (!form) return;

    // Fund preset tabs
    document.getElementById('sip-presets')?.querySelectorAll('.tab').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('sip-presets').querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        form.querySelector('#sip-rate').value = btn.dataset.rate;
        this.preview(form);
      });
    });

    _initForm('sip-form', f => this.preview(f), f => this.calculate(f));
  },

  preview(form) {
    const f = _fv(form);
    const P = _n(f.monthly_investment);
    const r = _n(f.annual_return) / 100 / 12;
    const n = _ni(f.years) * 12;
    if (n <= 0 || P <= 0) { FC.setText('preview-monthly', '—'); return; }
    const fv = r > 0 ? P * ((Math.pow(1 + r, n) - 1) / r) * (1 + r) : P * n;
    FC.setText('preview-monthly', FC.fmt.compact(fv, 'INR'));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/investment/sip', {
      monthly_investment: _n(f.monthly_investment),
      annual_return:      _n(f.annual_return),
      years:              _ni(f.years),
      step_up_pct:        _n(f.step_up_pct),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const cur = 'INR';
    const html = `<div class="results-panel">
      ${_bigCard('Maturity Value', FC.fmt.compact(d.final_amount, cur),
        `Wealth ratio: ${d.wealth_ratio.toFixed(2)}x your investment`)}
      <div class="result-grid">
        ${_stat('Total Invested',    FC.fmt.compact(d.total_invested, cur))}
        ${_stat('Estimated Returns', FC.fmt.compact(d.estimated_returns, cur), 'green')}
        ${_stat('Absolute Return',   pct(d.absolute_return_pct), 'green')}
      </div>
      ${_chartWrap('sip-chart', 'SIP Growth — Invested vs Returns')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_breakdown;
    FC.chart.bar('sip-chart', yrs.map(r => `Yr ${r.year}`), [
      { label: 'Invested', data: yrs.map(r => r.invested), backgroundColor: FC.COLORS.muted },
      { label: 'Returns',  data: yrs.map(r => Math.max(r.returns, 0)), backgroundColor: FC.COLORS.green },
    ], { scales: { x: { stacked: true }, y: { stacked: true,
      ticks: { callback: v => '₹'+(v/100000).toFixed(1)+'L' }
    }}});
  },
};

// ── 8. FIRE Calculator ────────────────────────────────────────────────────────

FC.calculators.fire = {
  init() {
    _initForm('fire-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/investment/fire', {
      current_age:          _ni(f.current_age),
      annual_expenses:      _n(f.annual_expenses),
      current_savings:      _n(f.current_savings),
      annual_savings:       _n(f.annual_savings),
      expected_return:      _n(f.expected_return),
      safe_withdrawal_rate: _n(f.safe_withdrawal_rate),
      inflation_rate:       _n(f.inflation_rate),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const reached = d.years_to_fire !== null;
    const statusText = reached
      ? `🎯 Financial independence at age ${d.fire_age} (${d.years_to_fire} years)`
      : '⏳ FIRE not reached in projection — increase savings or reduce expenses';

    const progressPct = Math.min(d.current_progress_pct, 100);

    const html = `<div class="results-panel">
      ${_bigCard('FIRE Number', compact(d.fire_number), statusText)}
      <div class="result-grid">
        ${_stat('Years to FIRE',       reached ? `${d.years_to_fire} years` : 'N/A', reached ? 'green' : 'red')}
        ${_stat('FIRE Age',            reached ? `Age ${d.fire_age}` : 'N/A', reached ? 'green' : '')}
        ${_stat('Monthly Expenses',    $2(d.monthly_expenses))}
        ${_stat('Progress',            pct(d.current_progress_pct, 1), progressPct > 80 ? 'green' : '')}
      </div>
      <div class="result-card">
        <div class="result-card__label">Progress to FIRE</div>
        <div style="margin-top:8px;background:var(--bg-input);border-radius:999px;height:12px;overflow:hidden">
          <div style="width:${progressPct}%;height:100%;background:var(--green-500);border-radius:999px;transition:width 0.6s ease"></div>
        </div>
        <div class="result-card__sub" style="margin-top:8px">${pct(progressPct, 1)} of ${compact(d.fire_number)} target</div>
      </div>
      ${_chartWrap('fire-chart', 'Portfolio Growth vs FIRE Target')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs  = d.yearly_projection;
    const show = yrs.slice(0, Math.min(yrs.length, 40));
    FC.chart.line('fire-chart', show.map(r => `Age ${r.age}`), [
      { label: 'Portfolio',    data: show.map(r => r.balance),     borderColor: FC.COLORS.green,
        backgroundColor: FC.COLORS.greenFade, fill: true, tension: 0.3 },
      { label: 'FIRE Target', data: show.map(r => r.fire_target),  borderColor: FC.COLORS.yellow,
        borderDash: [6, 3], fill: false, tension: 0.3 },
    ], { scales: { y: { ticks: { callback: v => '$'+(v/1000).toFixed(0)+'K' }}}});
  },
};

// ── 9. Student Loan Refinance ─────────────────────────────────────────────────

FC.calculators.studentLoan = {
  init() {
    const form = document.getElementById('studentLoan-form');
    if (!form) return;

    // Loan type auto-fills current rate
    const RATES = { undergrad: 6.53, grad: 8.08, parent_plus: 9.08 };
    form.querySelector('#sl-type')?.addEventListener('change', e => {
      const preset = RATES[e.target.value];
      if (preset) form.querySelector('#sl-cur-rate').value = preset;
    });

    _initForm('studentLoan-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/debt/student-loan', {
      loan_balance:       _n(f.loan_balance),
      current_rate:       _n(f.current_rate),
      loan_type:          f.loan_type,
      current_term_years: _n(f.current_term_years),
      new_rate:           _n(f.new_rate),
      new_term_years:     _n(f.new_term_years),
      income:             _n(f.income),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const saves = d.monthly_savings > 0;
    const warn  = d.federal_benefits_warning
      ? `<div class="alert alert--warning" style="margin:0;font-size:.83rem">${d.federal_benefits_warning}</div>` : '';

    const html = `<div class="results-panel">
      ${warn}
      <div class="result-grid">
        ${_stat('Current Monthly',  $2(d.current_monthly))}
        ${_stat('New Monthly',      $2(d.new_monthly), saves ? 'green' : 'red')}
        ${_stat('Monthly Savings',  $2(d.monthly_savings), saves ? 'green' : 'red')}
        ${_stat('Lifetime Savings', $(d.lifetime_savings), saves ? 'green' : 'red')}
      </div>
      <div class="result-card">
        ${_row('Interest (current loan)',     $(d.total_interest_current))}
        ${_row('Interest (refinanced loan)',  $(d.total_interest_new), saves ? 'green' : 'red')}
        ${_row('Lifetime Interest Saved',     $(d.lifetime_savings), saves ? 'green' : 'red')}
      </div>
      <div class="result-stat" style="padding:var(--s4)">
        <div class="result-stat__label">IDR Alternative Payment</div>
        <div class="result-stat__value">${$2(d.idr_monthly)}<span style="font-size:.8rem;font-weight:400;margin-left:4px;color:var(--text-muted)">/mo (income-driven)</span></div>
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 10. Credit Card Payoff ────────────────────────────────────────────────────

FC.calculators.creditCard = {
  init() {
    _initForm('creditCard-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/debt/credit-card', {
      balance:       _n(f.balance),
      apr:           _n(f.apr),
      minimum_pct:   _n(f.minimum_pct),
      minimum_floor: _n(f.minimum_floor),
      extra_payment: _n(f.extra_payment),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const min   = d.minimum_only;
    const extra = d.with_extra;
    const hasExtra = extra.months_saved > 0;

    const html = `<div class="results-panel">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--s3)">
        <div class="result-card">
          <div class="result-card__label">Minimum Only</div>
          <div style="font-family:var(--font-heading);font-size:1.8rem;font-weight:700;color:var(--color-danger)">${FC.fmt.months(min.months_to_payoff)}</div>
          <div class="result-card__sub">Total interest: ${$(min.total_interest)}</div>
        </div>
        <div class="result-card result-card--highlight">
          <div class="result-card__label">With Extra Payment</div>
          <div style="font-family:var(--font-heading);font-size:1.8rem;font-weight:700;color:var(--green-400)">${FC.fmt.months(extra.months_to_payoff)}</div>
          <div class="result-card__sub">Total interest: ${$(extra.total_interest)}</div>
        </div>
      </div>
      ${hasExtra ? `
      <div class="result-card result-card--highlight">
        <div class="result-card__label">Savings from Extra Payment</div>
        ${_row('Months Saved',    `${extra.months_saved} months`, 'green')}
        ${_row('Interest Saved',  $(extra.interest_saved), 'green')}
        ${_row('Time to Payoff',  FC.fmt.months(extra.months_to_payoff), 'green')}
      </div>` : ''}
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 11. Auto Loan / Car Lease ─────────────────────────────────────────────────

FC.calculators.autoLoan = {
  init() {
    _initForm('autoLoan-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/debt/auto-loan', {
      vehicle_price:    _n(f.vehicle_price),
      down_payment:     _n(f.down_payment),
      trade_in_value:   _n(f.trade_in_value),
      sales_tax_rate:   _n(f.sales_tax_rate),
      loan_rate:        _n(f.loan_rate),
      loan_term_months: _ni(f.loan_term_months),
      residual_value_pct: _n(f.residual_value_pct),
      money_factor:     _n(f.money_factor),
      lease_term_months: _ni(f.lease_term_months),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const comp = d.comparison;
    const isLoan  = comp.cheaper_option === 'LOAN';
    const loanCls = isLoan  ? 'result-card--highlight' : 'result-card';
    const leaseCls= !isLoan ? 'result-card--highlight' : 'result-card';

    const html = `<div class="results-panel">
      <div class="result-card">
        <div class="result-card__label">Recommendation</div>
        <div class="result-card__value" style="font-size:1.3rem">${isLoan ? '🚗 Buy is cheaper' : '📄 Lease is cheaper'}</div>
        <div class="result-card__sub">${comp.recommendation}</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--s3)">
        <div class="${loanCls}">
          <div class="result-card__label">🚗 Buy (Loan)</div>
          ${_row('Monthly Payment', $2(d.loan.monthly_payment))}
          ${_row('Total Cost', $(d.loan.total_paid))}
          ${_row('Total Interest', $(d.loan.total_interest))}
          ${_row('Vehicle Equity', $(d.loan.equity_at_end), 'green')}
        </div>
        <div class="${leaseCls}">
          <div class="result-card__label">📄 Lease</div>
          ${_row('Monthly Payment', $2(d.lease.monthly_payment))}
          ${_row('Total Cost', $(d.lease.total_paid))}
          ${_row('Equiv. APR', pct(d.lease.equiv_apr) + '%')}
          ${_row('Buyout Option', $(d.lease.buyout_option))}
        </div>
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 12. Personal Loan Eligibility ─────────────────────────────────────────────

FC.calculators.personalLoan = {
  init() {
    _initForm('personalLoan-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/debt/personal-loan', {
      loan_amount:   _n(f.loan_amount),
      annual_income: _n(f.annual_income),
      monthly_debts: _n(f.monthly_debts),
      credit_score:  _ni(f.credit_score),
      term_years:    _ni(f.term_years),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const eligColor = { LIKELY: 'green', POSSIBLE: 'yellow', UNLIKELY: 'red' };
    const eligLabel = { LIKELY: '✅ Likely Approved', POSSIBLE: '⚠️ Possible Approval', UNLIKELY: '❌ Unlikely to Qualify' };
    const factorColor = v => v === 'Strong' || v === 'Good' ? 'green' : v === 'Adequate' ? 'yellow' : 'red';
    const af = d.approval_factors;

    const html = `<div class="results-panel">
      <div class="result-card ${d.eligibility === 'LIKELY' ? 'result-card--highlight' : 'result-card--yellow'}">
        <div class="result-card__label">Eligibility Estimate</div>
        <div class="result-card__value ${eligColor[d.eligibility]}" style="font-size:1.5rem">${eligLabel[d.eligibility]}</div>
        <div class="result-card__sub">${d.credit_tier} Credit · DTI: ${d.dti_ratio}%</div>
      </div>
      <div class="result-grid">
        ${_stat('Estimated APR Range', `${d.estimated_apr_low}–${d.estimated_apr_high}%`)}
        ${_stat('Est. Monthly (Low)',  $2(d.estimated_monthly_low), 'green')}
        ${_stat('Est. Monthly (High)', $2(d.estimated_monthly_high))}
        ${_stat('DTI Ratio', pct(d.dti_ratio), d.dti_ratio < 36 ? 'green' : 'red')}
      </div>
      <div class="result-card">
        <div class="result-card__label" style="margin-bottom:var(--s3)">Approval Factors</div>
        ${_row('Credit Score', `${af.credit_score} (${d.credit_tier})`, factorColor(af.credit_score))}
        ${_row('Debt-to-Income', `${af.dti} — ${d.dti_ratio}%`, factorColor(af.dti))}
        ${_row('Income Level',   af.income, factorColor(af.income))}
      </div>
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 13. Take-Home Pay ─────────────────────────────────────────────────────────

FC.calculators.takeHomePay = {
  _cur: 'USD',
  _curSym: '$',

  init() {
    const form = document.getElementById('takeHomePay-form');
    if (!form) return;

    const CURRENCIES = { US: ['USD','$'], UK: ['GBP','£'], IN: ['INR','₹'] };

    _initTabGroup('thp-country-tabs', 'thp-country', 'country', (country) => {
      _showSection(country, { US: 'us-options', IN: 'india-options' });
      const [cur, sym]  = CURRENCIES[country] || CURRENCIES.US;
      this._cur    = cur;
      this._curSym = sym;
      const el = document.getElementById('thp-currency');
      if (el) el.textContent = sym;
    });

    // India regime tabs (inline onclick already in HTML, but also handle active state)
    form.querySelectorAll('[data-regime]').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.closest('.tab-group').querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
      });
    });

    _initForm('takeHomePay-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/tax/take-home-pay', {
      gross_income:   _n(f.gross_income),
      country:        f.country || 'US',
      filing_status:  f.filing_status || 'single',
      state:          f.state || 'TX',
      pay_frequency:  f.pay_frequency || 'monthly',
      regime:         f.regime || 'new',
    });
    this.renderResults(data, f.pay_frequency || 'monthly');
  },

  renderResults(d, freq) {
    const cur = this._cur;
    const freqLabel = { annual: 'Annual', monthly: 'Monthly', biweekly: 'Bi-Weekly' }[freq] || 'Monthly';
    const breakdownEntries = Object.entries(d.breakdown).map(([k, v]) =>
      _row(k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), FC.fmt.currency(v, cur, 2), 'red')
    ).join('');

    const html = `<div class="results-panel">
      ${_bigCard(freqLabel + ' Take-Home', FC.fmt.currency(d.take_home_per_period, cur, 2),
        `Effective tax rate: ${pct(d.effective_rate)} · Marginal: ${pct(d.marginal_rate)}`)}
      <div class="result-grid">
        ${_stat('Gross Annual',     FC.fmt.currency(d.gross_annual, cur))}
        ${_stat('Total Annual Tax', FC.fmt.currency(d.total_tax, cur), 'red')}
        ${_stat('Effective Rate',   pct(d.effective_rate))}
        ${_stat('Marginal Rate',    pct(d.marginal_rate))}
      </div>
      <div class="result-card">
        <div class="result-card__label" style="margin-bottom:var(--s3)">Tax Breakdown</div>
        ${_row('Gross Income', FC.fmt.currency(d.gross_annual, cur))}
        ${breakdownEntries}
        ${_row('Total Tax', FC.fmt.currency(d.total_tax, cur), 'red')}
        ${_row('Take-Home (Annual)', FC.fmt.currency(d.take_home_annual, cur), 'green')}
      </div>
      ${_chartWrap('thp-chart', 'Tax vs Take-Home')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const bd     = d.breakdown;
    const labels = Object.keys(bd).map(k => k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const values = Object.values(bd);
    const takeHome = d.take_home_annual;

    FC.chart.doughnut('thp-chart',
      [...labels, 'Take-Home'],
      [{
        data: [...values, takeHome],
        backgroundColor: [
          FC.COLORS.red, FC.COLORS.yellow, FC.COLORS.purple, FC.COLORS.blue,
          FC.COLORS.teal, FC.COLORS.green,
        ],
        borderColor: '#0F1A12',
        borderWidth: 2,
      }]
    );
  },
};

// ── 14. Freelance Tax ─────────────────────────────────────────────────────────

FC.calculators.freelanceTax = {
  _cur: 'USD',

  init() {
    const form = document.getElementById('freelanceTax-form');
    if (!form) return;

    const CURRENCIES = { US: 'USD', UK: 'GBP', IN: 'INR' };
    const SYMBOLS    = { US: '$',   UK: '£',   IN: '₹'  };

    _initTabGroup('fl-country-tabs', 'fl-country', 'country', country => {
      _showSection(country, { US: 'fl-us-options', IN: 'fl-india-options' });
      this._cur = CURRENCIES[country] || 'USD';
      const sym = SYMBOLS[country] || '$';
      ['fl-currency','fl-exp-currency'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = sym;
      });
    });

    // India 44ADA tabs
    form.querySelectorAll('[data-presumptive]').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.closest('.tab-group').querySelectorAll('.tab').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
      });
    });

    _initForm('freelanceTax-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/tax/freelance', {
      gross_revenue:      _n(f.gross_revenue),
      business_expenses:  _n(f.business_expenses),
      country:            f.country || 'US',
      filing_status:      f.filing_status || 'single',
      state:              f.state || 'TX',
      presumptive_scheme: f.presumptive_scheme === 'true',
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const cur = this._cur;
    const fmt = v => FC.fmt.currency(v, cur, 2);

    // Build quarterly schedule display
    const quarterly = d.quarterly_estimate;
    const dates     = d.quarterly_due_dates || [];
    const qRows     = dates.map((dt, i) =>
      _row(`Payment ${i+1} — due ${dt}`, fmt(quarterly))
    ).join('');
    const quarterlySection = quarterly ? `
      <div class="result-card result-card--yellow">
        <div class="result-card__label">Quarterly Estimated Tax Payments</div>
        <div class="result-card__value">${fmt(quarterly)}</div>
        <div class="result-card__sub">per installment to avoid underpayment penalties</div>
      </div>
      ${qRows ? `<div class="result-card">
        <div class="result-card__label" style="margin-bottom:var(--s3)">Payment Schedule</div>
        ${qRows}
      </div>` : ''}` : '';

    const html = `<div class="results-panel">
      ${_bigCard('Net Take-Home', fmt(d.take_home),
        `Effective tax rate: ${pct(d.effective_rate)}`)}
      <div class="result-grid">
        ${_stat('Net Profit',      fmt(d.net_profit))}
        ${_stat('Total Tax',       fmt(d.total_tax), 'red')}
        ${_stat('Self-Emp. Tax',   fmt(d.self_employment_tax || 0))}
        ${_stat('Income Tax',      fmt(d.income_tax || 0))}
      </div>
      ${quarterlySection}
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 15. Capital Gains Tax ─────────────────────────────────────────────────────

FC.calculators.capitalGains = {
  _cur: 'USD',

  init() {
    const form = document.getElementById('capitalGains-form');
    if (!form) return;

    const CURRENCIES = { US: ['USD','$'], UK: ['GBP','£'], IN: ['INR','₹'] };

    _initTabGroup('cg-country-tabs', 'cg-country', 'country', country => {
      _showSection(country, { US: 'cg-us-options', UK: 'cg-uk-options' });
      const [cur, sym]  = CURRENCIES[country] || CURRENCIES.US;
      this._cur    = cur;
      ['cg-currency','cg-sale-currency'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = sym;
      });
    });

    _initForm('capitalGains-form', _f => {}, f => this.calculate(f));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/tax/capital-gains', {
      country:        f.country || 'US',
      asset_type:     f.asset_type || 'equity',
      purchase_price: _n(f.purchase_price),
      sale_price:     _n(f.sale_price),
      holding_months: _ni(f.holding_months),
      annual_income:  _n(f.annual_income),
      filing_status:  f.filing_status || 'single',
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const cur = this._cur;
    const fmt = v => FC.fmt.currency(v, cur, 2);
    const isGain     = d.gain >= 0;
    const gainColor  = isGain ? 'green' : 'red';
    const effRate    = d.gain > 0 ? (d.tax_owed / d.gain * 100) : 0;

    const bdRows = d.breakdown ? Object.entries(d.breakdown).map(([k, v]) =>
      _row(k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
           typeof v === 'number' ? fmt(v) : v,
           k.includes('tax') || k.includes('cess') ? 'red' : '')
    ).join('') : '';

    const html = `<div class="results-panel">
      <div class="result-card ${isGain ? 'result-card--highlight' : 'result-card--yellow'}">
        <div class="result-card__label">${isGain ? 'Capital Gain' : 'Capital Loss'} — ${d.classification || ''}</div>
        <div class="result-card__value ${gainColor}">${fmt(d.gain)}</div>
        <div class="result-card__sub">Tax Rate: ${pct(d.tax_rate, 1)}</div>
      </div>
      <div class="result-grid">
        ${_stat('Tax Owed',       fmt(d.tax_owed), 'red')}
        ${_stat('Net Proceeds',   fmt(d.net_proceeds), 'green')}
        ${_stat('Effective Rate', pct(effRate, 2))}
      </div>
      ${bdRows ? `<div class="result-card">
        <div class="result-card__label" style="margin-bottom:var(--s3)">Tax Breakdown</div>
        ${bdRows}
      </div>` : ''}
      ${d.regime_notes ? `<div class="alert alert--warning" style="font-size:.83rem">ℹ️ ${d.regime_notes}</div>` : ''}
    </div>`;
    document.getElementById('results-container').innerHTML = html;
  },
};

// ── 16. Inflation Calculator ──────────────────────────────────────────────────

FC.calculators.inflation = {
  _cur: 'USD',
  _curSym: '$',

  init() {
    const form = document.getElementById('inflation-form');
    if (!form) return;

    const CONFIGS = {
      US: { cur: 'USD', sym: '$', label: 'US (1913+)' },
      EU: { cur: 'EUR', sym: '€', label: 'EU (2000+)' },
      IN: { cur: 'INR', sym: '₹', label: 'India (2000+)' },
    };
    const MIN_YEARS = { US: 1913, EU: 2000, IN: 2000 };

    _initTabGroup('inf-region-tabs', 'inf-region', 'region', region => {
      const cfg = CONFIGS[region] || CONFIGS.US;
      this._cur    = cfg.cur;
      this._curSym = cfg.sym;
      const sym = document.getElementById('inf-currency');
      if (sym) sym.textContent = cfg.sym;
      // Update year hints
      const hint = document.getElementById('inf-year-hint');
      if (hint) hint.textContent = `${cfg.label} data available`;
      // Update min year
      const startEl = document.getElementById('inf-start');
      if (startEl) startEl.min = MIN_YEARS[region] || 1913;
    });

    _initForm('inflation-form', f => this.preview(f), f => this.calculate(f));
  },

  preview(form) {
    const f   = _fv(form);
    const amt = _n(f.amount);
    const sy  = _ni(f.start_year);
    const ey  = _ni(f.end_year);
    if (!amt || sy >= ey) { FC.setText('preview-monthly', '—'); return; }
    // Quick estimate based on 3% average annual inflation
    const est = amt * Math.pow(1.03, ey - sy);
    FC.setText('preview-monthly', FC.fmt.currency(est, this._cur, 2));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/specialized/inflation', {
      region:     f.region || 'US',
      amount:     _n(f.amount),
      start_year: _ni(f.start_year),
      end_year:   _ni(f.end_year),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const cur = this._cur;
    const fmt = v => FC.fmt.currency(v, cur, 2);

    const html = `<div class="results-panel">
      ${_bigCard('Adjusted Value', fmt(d.adjusted_amount),
        `${fmt(d.original_amount)} in original terms`)}
      <div class="result-grid">
        ${_stat('Cumulative Inflation', pct(d.cumulative_inflation_pct, 1), 'yellow')}
        ${_stat('Avg Annual Rate',      pct(d.avg_annual_rate, 2))}
        ${_stat('Purchasing Power Lost', fmt(d.purchasing_power_lost), 'red')}
      </div>
      ${_chartWrap('inf-chart', 'Inflation Impact Over Time')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_values;
    FC.chart.line('inf-chart', yrs.map(r => r.year), [
      { label: 'Value Over Time', data: yrs.map(r => r.value),
        borderColor: FC.COLORS.yellow, backgroundColor: FC.COLORS.yellowFade,
        fill: true, tension: 0.3 },
    ], { scales: { y: {
      ticks: { callback: v => this._curSym + (v >= 1000 ? (v/1000).toFixed(1)+'K' : v.toFixed(0)) }
    }}});
  },
};

// ── 17. Rule of 72 ───────────────────────────────────────────────────────────

FC.calculators.ruleOf72 = {
  init() {
    const form = document.getElementById('ruleOf72-form');
    if (!form) return;

    // Mode tabs — toggle input groups
    _initTabGroup('r72-mode-tabs', 'r72-mode', 'mode', mode => {
      const rateGrp  = document.getElementById('r72-rate-group');
      const yearsGrp = document.getElementById('r72-years-group');
      if (rateGrp)  rateGrp.classList.toggle('hidden',  mode !== 'rate_to_years');
      if (yearsGrp) yearsGrp.classList.toggle('hidden', mode !== 'years_to_rate');
      this.preview(form);
    });

    _initForm('ruleOf72-form', f => this.preview(f), f => this.calculate(f));
  },

  preview(form) {
    const f    = _fv(form);
    const mode = f.mode || 'rate_to_years';
    const val  = mode === 'rate_to_years' ? _n(f.value) : _n(f.value_years);
    if (!val) { FC.setText('preview-monthly', '—'); return; }
    const result = 72 / val;
    const unit   = mode === 'rate_to_years' ? ' yrs' : '%';
    FC.setText('preview-monthly', result.toFixed(1) + unit);
  },

  async calculate(form) {
    const f    = _fv(form);
    const mode = f.mode || 'rate_to_years';
    const val  = mode === 'rate_to_years' ? _n(f.value) : _n(f.value_years);
    if (!val) throw new Error('Please enter a positive value');
    const { data } = await FC.api.post('/api/specialized/rule-of-72', {
      mode,
      value: val,
    });
    this.renderResults(data, mode);
  },

  renderResults(d, mode) {
    const isRateToYears = mode === 'rate_to_years';
    const colLabel = isRateToYears ? 'Years' : 'Required Rate';
    const unit     = isRateToYears ? ' yrs' : '%';
    const fmt      = v => v !== null ? (v.toFixed(2) + unit) : '—';
    const r72  = d.rule_72.years  || d.rule_72.rate;
    const r114 = d.rule_114.years || d.rule_114.rate;
    const r144 = d.rule_144.years || d.rule_144.rate;

    const html = `<div class="results-panel">
      <div class="result-card result-card--highlight">
        <div class="result-card__label">${isRateToYears ? 'Years to Double (Rule of 72)' : 'Rate Needed to Double'}</div>
        <div class="result-card__value">${fmt(r72)}</div>
        <div class="result-card__sub">${d.description}</div>
      </div>
      <div class="table-wrap">
        <div class="table-title">Double · Triple · Quadruple</div>
        <table class="data-table">
          <thead>
            <tr><th>Goal</th><th>Rule Estimate</th><th>Exact (Log)</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>2× (Rule of 72)</td>
              <td style="color:var(--green-400)">${fmt(r72)}</td>
              <td>${fmt(d.exact.double)}</td>
            </tr>
            <tr>
              <td>3× (Rule of 114)</td>
              <td style="color:var(--yellow-400)">${fmt(r114)}</td>
              <td>${fmt(d.exact.triple)}</td>
            </tr>
            <tr>
              <td>4× (Rule of 144)</td>
              <td style="color:var(--blue)">${fmt(r144)}</td>
              <td>${fmt(d.exact.quad)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      ${_chartWrap('r72-chart', isRateToYears ? 'Years to 2×, 3×, 4× Growth' : 'Required Rates')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    FC.chart.bar('r72-chart',
      isRateToYears ? ['Double (2×)', 'Triple (3×)', 'Quadruple (4×)'] : ['Double (2×)', 'Triple (3×)', 'Quadruple (4×)'],
      [{
        label: isRateToYears ? 'Years (Rule Est.)' : 'Rate % (Rule Est.)',
        data:  [r72, r114, r144],
        backgroundColor: [FC.COLORS.green, FC.COLORS.yellow, FC.COLORS.blue],
      }, {
        label: 'Exact Value',
        data:  [d.exact.double, d.exact.triple, d.exact.quad],
        backgroundColor: [FC.COLORS.greenDark, FC.COLORS.yellowFade, FC.COLORS.teal],
        borderColor: [FC.COLORS.greenDark, FC.COLORS.yellow, FC.COLORS.teal],
        borderWidth: 2,
        type: 'bar',
      }]
    );
  },
};

// ── 18. Latte Factor ──────────────────────────────────────────────────────────

FC.calculators.latteFactor = {
  init() {
    const form = document.getElementById('latteFactor-form');
    if (!form) return;

    // Expense preset buttons
    form.querySelectorAll('[data-expense]').forEach(btn => {
      btn.addEventListener('click', () => {
        const expInput = form.querySelector('#lf-expense');
        if (expInput) {
          expInput.value = btn.dataset.expense;
          // Trigger range display update
          expInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
      });
    });

    _initForm('latteFactor-form', f => this.preview(f), f => this.calculate(f));
  },

  preview(form) {
    const f    = _fv(form);
    const daily = _n(f.daily_expense);
    const r     = _n(f.annual_return) / 100 / 12;
    const n     = _ni(f.years) * 12;
    const pmt   = daily * 30.44;
    if (n <= 0 || pmt <= 0) { FC.setText('preview-monthly', '—'); return; }
    const fv = r > 0 ? pmt * ((Math.pow(1 + r, n) - 1) / r) * (1 + r) : pmt * n;
    FC.setText('preview-monthly', compact(fv));
  },

  async calculate(form) {
    const f = _fv(form);
    const { data } = await FC.api.post('/api/specialized/latte-factor', {
      daily_expense:  _n(f.daily_expense),
      annual_return:  _n(f.annual_return),
      inflation_rate: _n(f.inflation_rate),
      years:          _ni(f.years),
    });
    this.renderResults(data);
  },

  renderResults(d) {
    const html = `<div class="results-panel">
      ${_bigCard('Nominal Portfolio Value', compact(d.invested_value_nominal),
        `If $${d.daily_expense.toFixed(2)}/day was invested instead`)}
      <div class="result-grid">
        ${_stat('Real Value (Inflation-Adj.)', compact(d.invested_value_real), 'yellow')}
        ${_stat('Total Invested',             compact(d.total_invested))}
        ${_stat('Investment Gain',            compact(d.investment_gain), 'green')}
        ${_stat('Daily Cost',                 $2(d.daily_expense) + '/day')}
      </div>
      <div class="result-card">
        ${_row('Daily Expense',         $2(d.daily_expense))}
        ${_row('Monthly Expense',       $2(d.monthly_expense))}
        ${_row('Annual Expense',        $2(d.annual_expense))}
        ${_row('Portfolio (Nominal)',    compact(d.invested_value_nominal), 'green')}
        ${_row('Portfolio (Real)',       compact(d.invested_value_real), 'yellow')}
      </div>
      ${_chartWrap('lf-chart', 'Invested vs Real Value Over Time')}
    </div>`;
    document.getElementById('results-container').innerHTML = html;

    const yrs = d.yearly_projection;
    FC.chart.line('lf-chart', yrs.map(r => `Yr ${r.year}`), [
      { label: 'Invested (Nominal)', data: yrs.map(r => r.invested),   borderColor: FC.COLORS.green,
        backgroundColor: FC.COLORS.greenFade, fill: true, tension: 0.3 },
      { label: 'Real Value',         data: yrs.map(r => r.real_value), borderColor: FC.COLORS.yellow,
        backgroundColor: FC.COLORS.yellowFade, fill: false, tension: 0.3 },
      { label: 'Amount Saved',       data: yrs.map(r => r.saved),      borderColor: FC.COLORS.muted,
        borderDash: [4,4], fill: false, tension: 0.3 },
    ], { scales: { y: { ticks: { callback: v => '$'+(v >= 1000 ? (v/1000).toFixed(0)+'K' : v) }}}});
  },
};
