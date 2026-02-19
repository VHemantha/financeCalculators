/**
 * FinWise Calculators — Shared Utilities
 * Exposes window.FC namespace with formatting, API, and chart helpers.
 */

window.FC = (function () {
  "use strict";

  // ── Formatters ────────────────────────────────────────────────────────────
  const fmt = {
    currency(value, currency = "USD", decimals = 0) {
      if (!isFinite(value)) return "—";
      const localeMap = { USD: "en-US", GBP: "en-GB", EUR: "de-DE", INR: "en-IN" };
      const locale = localeMap[currency] || "en-US";
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency,
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(value);
    },

    number(value, decimals = 0) {
      if (!isFinite(value)) return "—";
      return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(value);
    },

    percent(value, decimals = 2) {
      if (!isFinite(value)) return "—";
      return `${value.toFixed(decimals)}%`;
    },

    compact(value, currency = "USD") {
      if (!isFinite(value)) return "—";
      const symbols = { USD: "$", GBP: "£", EUR: "€", INR: "₹" };
      const prefix = symbols[currency] || "";
      if (Math.abs(value) >= 1e9) return prefix + (value / 1e9).toFixed(2) + "B";
      if (Math.abs(value) >= 1e6) return prefix + (value / 1e6).toFixed(2) + "M";
      if (Math.abs(value) >= 1e3) return prefix + (value / 1e3).toFixed(1) + "K";
      return prefix + value.toFixed(0);
    },

    months(months) {
      if (!isFinite(months)) return "—";
      const y = Math.floor(months / 12);
      const m = months % 12;
      if (y === 0) return `${m} months`;
      if (m === 0) return `${y} year${y > 1 ? "s" : ""}`;
      return `${y} yr ${m} mo`;
    },
  };

  // ── Debounce ──────────────────────────────────────────────────────────────
  function debounce(fn, delay = 300) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ── API helper ────────────────────────────────────────────────────────────
  const api = {
    async post(endpoint, payload) {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "Calculation failed");
      return json;
    },
  };

  // ── UI helpers ────────────────────────────────────────────────────────────
  function setLoading(btn, isLoading) {
    btn.disabled = isLoading;
    if (isLoading) {
      btn.dataset.originalText = btn.textContent;
      btn.innerHTML = '<span class="spinner"></span> Calculating…';
    } else {
      btn.textContent = btn.dataset.originalText || "Calculate";
    }
  }

  function showError(containerId, message) {
    const el = document.getElementById(containerId);
    if (el) {
      el.innerHTML = `<div class="alert alert--warning">⚠ ${message}</div>`;
      el.classList.remove("hidden");
    }
  }

  function clearResults(containerId) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = "";
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function setHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  // ── Chart factory ─────────────────────────────────────────────────────────
  const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: true,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: {
          color: "#A1C4A8",
          font: { family: "Inter", size: 11 },
          boxWidth: 12,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: "#162019",
        borderColor: "#2A3D2E",
        borderWidth: 1,
        titleColor: "#F0FDF4",
        bodyColor: "#A1C4A8",
        padding: 10,
      },
    },
    scales: {
      x: {
        ticks: { color: "#4B6B50", font: { size: 10 } },
        grid:  { color: "rgba(42,61,46,0.5)" },
      },
      y: {
        ticks: { color: "#4B6B50", font: { size: 10 } },
        grid:  { color: "rgba(42,61,46,0.5)" },
      },
    },
  };

  const chart = {
    instances: {},

    _destroy(id) {
      if (chart.instances[id]) {
        chart.instances[id].destroy();
        delete chart.instances[id];
      }
    },

    _deepMerge(base, override) {
      const result = { ...base };
      for (const key of Object.keys(override)) {
        if (override[key] && typeof override[key] === "object" && !Array.isArray(override[key])) {
          result[key] = chart._deepMerge(base[key] || {}, override[key]);
        } else {
          result[key] = override[key];
        }
      }
      return result;
    },

    create(canvasId, type, labels, datasets, overrides = {}) {
      chart._destroy(canvasId);
      const canvas = document.getElementById(canvasId);
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const opts = chart._deepMerge(CHART_DEFAULTS, overrides);
      chart.instances[canvasId] = new Chart(ctx, { type, data: { labels, datasets }, options: opts });
      return chart.instances[canvasId];
    },

    bar(canvasId, labels, datasets, overrides = {}) {
      return chart.create(canvasId, "bar", labels, datasets, overrides);
    },

    line(canvasId, labels, datasets, overrides = {}) {
      return chart.create(canvasId, "line", labels, datasets, overrides);
    },

    doughnut(canvasId, labels, datasets, overrides = {}) {
      const donutDefaults = {
        scales: {},
        plugins: {
          legend: { position: "bottom", labels: { color: "#A1C4A8", font: { size: 11 }, padding: 12, boxWidth: 12 } },
        },
      };
      return chart.create(canvasId, "doughnut", labels, datasets, chart._deepMerge(donutDefaults, overrides));
    },
  };

  // Chart color palette
  const COLORS = {
    green:      "#22C55E",
    greenDark:  "#16A34A",
    greenFade:  "rgba(34,197,94,0.15)",
    yellow:     "#FACC15",
    yellowFade: "rgba(250,204,21,0.15)",
    red:        "#EF4444",
    redFade:    "rgba(239,68,68,0.15)",
    blue:       "#38BDF8",
    purple:     "#A78BFA",
    teal:       "#2DD4BF",
    muted:      "#4B6B50",
  };

  // ── FAQ accordion ─────────────────────────────────────────────────────────
  function initFAQ() {
    document.querySelectorAll(".faq-question").forEach((btn) => {
      btn.addEventListener("click", () => {
        const answer = btn.nextElementSibling;
        const isOpen = answer.classList.contains("is-open");

        // Close all
        document.querySelectorAll(".faq-answer.is-open").forEach((a) => a.classList.remove("is-open"));
        document.querySelectorAll(".faq-question.is-open").forEach((b) => b.classList.remove("is-open"));

        if (!isOpen) {
          answer.classList.add("is-open");
          btn.classList.add("is-open");
        }
      });
    });
  }

  // ── Mobile nav ────────────────────────────────────────────────────────────
  function initNav() {
    const hamburger = document.querySelector(".nav__hamburger");
    const mobileMenu = document.querySelector(".nav__mobile-menu");
    if (!hamburger || !mobileMenu) return;
    hamburger.addEventListener("click", () => {
      mobileMenu.classList.toggle("is-open");
    });
    // Close on outside click
    document.addEventListener("click", (e) => {
      if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
        mobileMenu.classList.remove("is-open");
      }
    });
  }

  // ── Range input dual-display ──────────────────────────────────────────────
  function initRangeInputs() {
    document.querySelectorAll(".form-range[data-output]").forEach((range) => {
      const output = document.getElementById(range.dataset.output);
      if (!output) return;
      const update = () => { output.textContent = range.value + (range.dataset.suffix || ""); };
      range.addEventListener("input", update);
      update();
    });
  }

  // ── DOMContentLoaded ──────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    initFAQ();
    initNav();
    initRangeInputs();

    // Init calculator module based on body data attribute
    const page = document.body.dataset.calculator;
    if (page && window.FC.calculators && window.FC.calculators[page]) {
      window.FC.calculators[page].init();
    }
  });

  // ── Public API ────────────────────────────────────────────────────────────
  return { fmt, debounce, api, chart, COLORS, setLoading, showError, clearResults, setText, setHTML };
})();

// Placeholder namespace — calculators.js will populate this
window.FC.calculators = {};
