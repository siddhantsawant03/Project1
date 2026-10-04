const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

/* ================================================================
   FORMATTING
   ================================================================ */

const money = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value));
};

const fullMoney = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const pct = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return `${(Number(value) * 100).toFixed(1)}%`;
};

const number = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
};

const signedMoney = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  const n = Number(value);

  if (n > 0) {
    return `+${money(n)}`;
  }

  return money(n);
};

/* ================================================================
   PLOTLY BASE CONFIGURATION
   ================================================================ */

const plotBase = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",

  font: {
    color: "#697586",
    size: 10,
    family: "Inter, Segoe UI, Arial, sans-serif",
  },

  margin: {
    l: 48,
    r: 18,
    t: 10,
    b: 42,
  },

  xaxis: {
    gridcolor: "#edf0f4",
    zerolinecolor: "#edf0f4",
    linecolor: "#e2e7ee",
    tickfont: {
      size: 9,
    },
  },

  yaxis: {
    gridcolor: "#edf0f4",
    zerolinecolor: "#edf0f4",
    linecolor: "#e2e7ee",
    tickfont: {
      size: 9,
    },
  },

  legend: {
    orientation: "h",
    y: 1.12,
    x: 0,
    font: {
      size: 9,
    },
  },

  hoverlabel: {
    bgcolor: "#172033",
    bordercolor: "#172033",
    font: {
      color: "#ffffff",
      size: 10,
    },
  },
};

const plotConfig = {
  displayModeBar: false,
  responsive: true,
};

function plot(id, traces, layout = {}) {
  const element = document.getElementById(id);

  if (!element) {
    return;
  }

  Plotly.react(
    element,
    traces,
    {
      ...plotBase,
      ...layout,
    },
    plotConfig,
  );
}

/* ================================================================
   APPLICATION STATE
   ================================================================ */

let data = null;
let metadata = null;
let scenarioData = null;

let activeTab = "overview";

let loading = false;

/* ================================================================
   API
   ================================================================ */

async function get(url) {
  const response = await fetch(url, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return response.json();
}

/* ================================================================
   LOADING STATE
   ================================================================ */

function showLoading() {
  loading = true;

  const overlay = $("#loading");

  if (overlay) {
    overlay.classList.remove("hidden");
  }
}

function hideLoading() {
  loading = false;

  const overlay = $("#loading");

  if (overlay) {
    overlay.classList.add("hidden");
  }
}

/* ================================================================
   ERROR STATE
   ================================================================ */

function showError(message) {
  hideLoading();

  const main = $(".main");

  if (!main) {
    return;
  }

  const existing = $(".error-state");

  if (existing) {
    existing.remove();
  }

  const error = document.createElement("div");

  error.className = "error-state";

  error.textContent = `Unable to load the analytical model: ${message}`;

  main.prepend(error);
}

function clearError() {
  const existing = $(".error-state");

  if (existing) {
    existing.remove();
  }
}

/* ================================================================
   METADATA
   ================================================================ */

async function loadMetadata() {
  metadata = await get("/api/metadata");

  const companySelect = $("#company");
  const yearSelect = $("#year");

  companySelect.innerHTML = `<option value="ALL">All companies</option>`;

  metadata.companies.forEach((company) => {
    const option = document.createElement("option");

    option.value = company;
    option.textContent = company;

    companySelect.appendChild(option);
  });

  yearSelect.innerHTML = `<option value="ALL">All periods</option>`;

  metadata.years.forEach((year) => {
    const option = document.createElement("option");

    option.value = year;
    option.textContent = year;

    yearSelect.appendChild(option);
  });

  $("#periodLine").textContent = `${metadata.period_start.slice(
    0,
    7,
  )} — ${metadata.period_end.slice(0, 7)} · ${number(
    metadata.rows,
  )} analytical records`;
}

/* ================================================================
   LOAD MAIN DATA
   ================================================================ */

async function loadData() {
  showLoading();
  clearError();

  try {
    const company = $("#company").value || "ALL";

    const year = $("#year").value || "ALL";

    const params = new URLSearchParams({
      company,
      year,
    });

    data = await get(`/api/data?${params.toString()}`);

    if (data.empty) {
      showEmptyState();
      return;
    }

    render();
  } catch (error) {
    console.error(error);

    showError(error.message);
  } finally {
    hideLoading();
  }
}

function showEmptyState() {
  hideLoading();

  const sections = $$(".tab");

  sections.forEach((section) => {
    if (section.classList.contains("active")) {
      const target = section.querySelector(".page-intro");

      if (target) {
        const empty = document.createElement("div");

        empty.className = "empty-state";

        empty.textContent = "No records match the selected filters.";

        target.after(empty);
      }
    }
  });
}

/* ================================================================
   RENDER EVERYTHING
   ================================================================ */

function render() {
  renderKpis();

  renderOverview();

  renderPnl();

  renderVariance();

  renderDrivers();

  renderForecast();

  renderCost();

  renderQuality();

  renderScenario();

  renderMethodology();
}

/* ================================================================
   KPI CARDS
   ================================================================ */

function renderKpis() {
  const k = data.kpis;

  const cards = [
    {
      label: "Revenue",
      value: money(k.revenue),
      note: `Budget ${money(k.budget_revenue)}`,
    },

    {
      label: "Gross Profit",
      value: money(k.gross_profit),
      note: `Variance ${signedMoney(k.gross_profit_var)}`,
    },

    {
      label: "Operating Profit",
      value: money(k.operating_profit),
      note: `Budget ${money(k.budget_operating_profit)}`,
    },

    {
      label: "Operating Margin",
      value: pct(k.operating_margin),
      note: `Budget ${pct(k.budget_operating_margin)}`,
    },

    {
      label: "Revenue Variance",
      value: signedMoney(k.revenue_var),
      note: "Actual vs Budget",
    },

    {
      label: "Operating Profit Variance",
      value: signedMoney(k.op_profit_var),
      note: "Actual vs Budget",
    },

    {
      label: "Forecast Operating Profit",
      value: money(k.forecast_profit),
      note: "Forward analytical outlook",
    },

    {
      label: "Forecast vs Budget",
      value: signedMoney(k.forecast_gap),
      note: "Forward gap to budget",
    },
  ];

  $("#kpis").innerHTML = cards
    .map((card) => {
      return `
                <div class="card">

                    <span>${card.label}</span>

                    <b>${card.value}</b>

                    <small>${card.note}</small>

                </div>
            `;
    })
    .join("");
}

/* ================================================================
   EXECUTIVE OVERVIEW
   ================================================================ */

function renderOverview() {
  const monthly = data.monthly;

  plot(
    "trend",
    [
      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.revenue),
        name: "Actual Revenue",
        mode: "lines+markers",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },

      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.budget_revenue),
        name: "Budget Revenue",
        mode: "lines",
        line: {
          dash: "dot",
          width: 1.7,
        },
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "profit",
    [
      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.operating_profit),
        name: "Operating Profit",
        mode: "lines+markers",
        fill: "tozeroy",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  const categories = data.category.filter((x) =>
    ["Revenue", "COGS", "Personnel", "Opex", "Depreciation"].includes(
      x.category,
    ),
  );

  plot(
    "categoryVariance",
    [
      {
        x: categories.map((x) => x.category),
        y: categories.map((x) => x.variance),
        type: "bar",
        hovertemplate: "%{x}<br>Variance: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  $("#signals").innerHTML = data.signals
    .map((signal) => {
      return `
                <div class="signal">

                    <b>${signal.title}</b>

                    <span>${signal.text}</span>

                </div>
            `;
    })
    .join("");
}

/* ================================================================
   P&L
   ================================================================ */

function renderPnl() {
  const p = data.monthly;

  plot(
    "pnlChart",
    [
      {
        x: p.map((x) => x.month),
        y: p.map((x) => x.revenue),
        name: "Revenue",
        mode: "lines+markers",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },

      {
        x: p.map((x) => x.month),
        y: p.map((x) => x.operating_profit),
        name: "Operating Profit",
        mode: "lines+markers",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "marginChart",
    [
      {
        x: p.map((x) => x.month),
        y: p.map((x) => x.operating_margin),
        name: "Actual",
        mode: "lines+markers",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },

      {
        x: p.map((x) => x.month),
        y: p.map((x) => x.budget_operating_margin),
        name: "Budget",
        mode: "lines",
        line: {
          dash: "dot",
          width: 1.7,
        },
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: ".0%",
      },
    },
  );

  $("#pnlTable tbody").innerHTML = p
    .map((row) => {
      return `
                <tr>

                    <td>${row.month}</td>

                    <td>${money(row.revenue)}</td>

                    <td>${money(row.cogs)}</td>

                    <td>${money(row.gross_profit)}</td>

                    <td>${money(row.personnel)}</td>

                    <td>${money(row.opex)}</td>

                    <td>${money(row.depreciation)}</td>

                    <td class="${row.operating_profit >= 0 ? "good" : "bad"}">
                        ${money(row.operating_profit)}
                    </td>

                    <td>
                        ${pct(row.operating_margin)}
                    </td>

                </tr>
            `;
    })
    .join("");
}

/* ================================================================
   VARIANCE
   ================================================================ */

function renderVariance() {
  const monthly = data.monthly;
  const categories = data.category;

  plot(
    "varianceChart",
    [
      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.profit_variance),
        type: "bar",
        hovertemplate: "%{x}<br>OP variance: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "varianceCategory",
    [
      {
        x: categories.map((x) => x.category),
        y: categories.map((x) => x.variance),
        type: "bar",
        hovertemplate: "%{x}<br>Variance: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  $("#varianceTable tbody").innerHTML = categories
    .map((row) => {
      const assessmentClass = row.variance >= 0 ? "good" : "bad";

      return `
                <tr>

                    <td>${row.category}</td>

                    <td>${money(row.actual)}</td>

                    <td>${money(row.budget)}</td>

                    <td class="${assessmentClass}">
                        ${signedMoney(row.variance)}
                    </td>

                    <td>
                        ${pct(row.variance_pct)}
                    </td>

                    <td class="${assessmentClass}">
                        ${row.assessment}
                    </td>

                </tr>
            `;
    })
    .join("");
}

/* ================================================================
   DRIVER ANALYSIS
   ================================================================ */

function renderDrivers() {
  const drivers = data.driver || [];

  if (!drivers.length) {
    return;
  }

  const totalImpact = drivers.reduce(
    (sum, row) => sum + Number(row.management_impact || 0),
    0,
  );

  const favorable = drivers
    .filter((row) => Number(row.management_impact) >= 0)
    .reduce((sum, row) => sum + Number(row.management_impact || 0), 0);

  const unfavorable = drivers
    .filter((row) => Number(row.management_impact) < 0)
    .reduce((sum, row) => sum + Number(row.management_impact || 0), 0);

  $("#driverSummary").innerHTML = [
    {
      label: "Total OP variance",
      value: signedMoney(totalImpact),
      className: totalImpact >= 0 ? "good" : "bad",
    },

    {
      label: "Favorable contribution",
      value: signedMoney(favorable),
      className: "good",
    },

    {
      label: "Unfavorable contribution",
      value: signedMoney(unfavorable),
      className: "bad",
    },
  ]
    .map((card) => {
      return `
            <div class="driver-summary-card">

                <span>${card.label}</span>

                <b class="${card.className}">
                    ${card.value}
                </b>

            </div>
        `;
    })
    .join("");

  const sorted = [...drivers].sort(
    (a, b) =>
      Math.abs(Number(b.management_impact)) -
      Math.abs(Number(a.management_impact)),
  );

  plot(
    "driverChart",
    [
      {
        x: sorted.map((x) => x.category),
        y: sorted.map((x) => x.management_impact),
        type: "bar",
        hovertemplate: "%{x}<br>Impact: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "driverContribution",
    [
      {
        x: sorted.map((x) => x.category),
        y: sorted.map((x) => Math.abs(Number(x.management_impact))),
        type: "bar",
        hovertemplate: "%{x}<br>Absolute impact: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  $("#driverTable tbody").innerHTML = sorted
    .map((row) => {
      const impact = Number(row.management_impact);

      const cls = impact >= 0 ? "good" : "bad";

      return `
                <tr>

                    <td>${row.category}</td>

                    <td>${money(row.actual)}</td>

                    <td>${money(row.budget)}</td>

                    <td class="${cls}">
                        ${signedMoney(impact)}
                    </td>

                    <td class="${cls}">
                        ${row.direction}
                    </td>

                </tr>
            `;
    })
    .join("");
}

/* ================================================================
   FORECAST
   ================================================================ */

function renderForecast() {
  const monthly = data.monthly;

  plot(
    "forecastChart",
    [
      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.forecast_operating_profit),
        name: "Forecast",
        mode: "lines+markers",
        line: {
          width: 2,
        },
        marker: {
          size: 4,
        },
      },

      {
        x: monthly.map((x) => x.month),
        y: monthly.map((x) => x.budget_operating_profit),
        name: "Budget",
        mode: "lines",
        line: {
          dash: "dot",
          width: 1.7,
        },
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "forecastGap",
    [
      {
        x: monthly.map((x) => x.month),
        y: monthly.map(
          (x) => x.forecast_operating_profit - x.budget_operating_profit,
        ),
        type: "bar",
        hovertemplate: "%{x}<br>Forecast gap: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  $("#forecastCards").innerHTML = [
    {
      label: "Forecast operating profit",
      value: money(data.kpis.forecast_profit),
      note: "Forward analytical outlook",
    },

    {
      label: "Forecast vs Budget",
      value: signedMoney(data.kpis.forecast_gap),
      note: "Operating profit gap",
    },

    {
      label: "Forecast revenue",
      value: money(data.kpis.forecast_revenue),
      note: "Forward revenue outlook",
    },
  ]
    .map((card) => {
      return `
            <div class="card">

                <span>${card.label}</span>

                <b>${card.value}</b>

                <small>${card.note}</small>

            </div>
        `;
    })
    .join("");

  const backtest = data.backtest || [];

  $("#backtestTable tbody").innerHTML = backtest
    .map((row) => {
      return `
                <tr>

                    <td>${row.category}</td>

                    <td>${money(row.actual_total)}</td>

                    <td>${money(row.forecast_total)}</td>

                    <td>${money(row.mae)}</td>

                    <td>${pct(row.mape)}</td>

                    <td class="${Number(row.bias) >= 0 ? "good" : "bad"}">
                        ${signedMoney(row.bias)}
                    </td>

                </tr>
            `;
    })
    .join("");
}

/* ================================================================
   COST CENTRES
   ================================================================ */

function renderCost() {
  const cost = [...(data.cost || [])];

  const topActual = [...cost]
    .sort((a, b) => Number(b.actual) - Number(a.actual))
    .slice(0, 12);

  const largestVariance = [...cost]
    .sort((a, b) => Math.abs(Number(b.variance)) - Math.abs(Number(a.variance)))
    .slice(0, 12);

  plot(
    "ccChart",
    [
      {
        x: topActual.map((x) => String(x.cost_centre)),
        y: topActual.map((x) => x.actual),
        type: "bar",
        hovertemplate: "%{x}<br>Actual: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      xaxis: {
        ...plotBase.xaxis,
        tickangle: -35,
      },
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "ccVarChart",
    [
      {
        x: largestVariance.map((x) => String(x.cost_centre)),
        y: largestVariance.map((x) => x.variance),
        type: "bar",
        hovertemplate: "%{x}<br>Variance: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      xaxis: {
        ...plotBase.xaxis,
        tickangle: -35,
      },
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  $("#ccTable tbody").innerHTML = cost
    .map((row) => {
      const variance = Number(row.variance);

      return `
                <tr>

                    <td>${row.cost_centre}</td>

                    <td>${money(row.actual)}</td>

                    <td>${money(row.budget)}</td>

                    <td class="${variance >= 0 ? "good" : "bad"}">
                        ${signedMoney(variance)}
                    </td>

                    <td>
                        ${pct(row.variance_pct)}
                    </td>

                </tr>
            `;
    })
    .join("");
}

/* ================================================================
   DATA QUALITY
   ================================================================ */

function renderQuality() {
  const q = data.quality || {};

  const cards = [
    {
      label: "Analytical rows",
      value: number(q.rows),
      note: "Validated model records",
    },

    {
      label: "Reporting months",
      value: number(q.months),
      note: "Monthly periods",
    },

    {
      label: "Companies",
      value: number(q.companies),
      note: "Company codes",
    },

    {
      label: "Company-cost-centre combinations",
      value: number(q.cost_centres),
      note: "Populated combinations",
    },

    {
      label: "Null cells",
      value: number(q.null_cells),
      note: "Retained transparently",
    },

    {
      label: "Duplicate keys",
      value: number(q.duplicate_keys),
      note: "Expected control: 0",
    },
  ];

  $("#qualityCards").innerHTML = cards
    .map((card) => {
      return `
                <div class="card">

                    <span>${card.label}</span>

                    <b>${card.value}</b>

                    <small>${card.note}</small>

                </div>
            `;
    })
    .join("");

  const total = Number(q.rows || 0);

  const coverage = [
    {
      label: "Monthly coverage",
      value: Number(q.months || 0),
      max: 48,
    },

    {
      label: "Companies",
      value: Number(q.companies || 0),
      max: 3,
    },

    {
      label: "Cost-centre combinations",
      value: Number(q.cost_centres || 0),
      max: 72,
    },

    {
      label: "Duplicate keys",
      value: Number(q.duplicate_keys || 0),
      max: 1,
    },
  ];

  $("#coverageSummary").innerHTML = coverage
    .map((item) => {
      let percentage;

      if (item.label === "Duplicate keys") {
        percentage = item.value === 0 ? 100 : 0;
      } else {
        percentage = Math.min(100, (item.value / item.max) * 100);
      }

      return `
                <div class="coverage-item">

                    <span>${item.label}</span>

                    <div class="coverage-bar">

                        <div
                            style="width:${percentage}%"
                        ></div>

                    </div>

                    <b>${number(item.value)}</b>

                </div>
            `;
    })
    .join("");
}

/* ================================================================
   SCENARIOS
   ================================================================ */

async function loadScenarioData() {
  try {
    const response = await get("/api/scenario");

    scenarioData = response.records || [];
  } catch (error) {
    console.error("Scenario data could not be loaded.", error);

    scenarioData = [];
  }
}

function renderScenario() {
  if (!scenarioData || !scenarioData.length) {
    return;
  }

  updateScenarioCharts(scenarioData);

  const controls = ["rev", "cogs", "pers", "opex"];

  controls.forEach((id) => {
    const element = $(`#${id}`);

    if (!element) {
      return;
    }

    element.oninput = () => {
      updateScenarioLabels();

      updateInteractiveScenario();
    };
  });

  updateScenarioLabels();

  updateInteractiveScenario();
}

function updateScenarioLabels() {
  const mappings = [
    ["rev", "revv"],
    ["cogs", "cogsv"],
    ["pers", "persv"],
    ["opex", "opexv"],
  ];

  mappings.forEach(([input, output]) => {
    const source = $(`#${input}`);
    const target = $(`#${output}`);

    if (source && target) {
      target.textContent = `${source.value}%`;
    }
  });
}

function updateInteractiveScenario() {
  if (!scenarioData.length) {
    return;
  }

  const revenueGrowth = Number($("#rev").value) / 100;

  const cogsChange = Number($("#cogs").value) / 100;

  const personnelGrowth = Number($("#pers").value) / 100;

  const opexGrowth = Number($("#opex").value) / 100;

  /*
        The dashboard applies the user's assumptions to the
        Base forecast scenario.

        This mirrors the analytical scenario structure:
            Revenue
            COGS
            Personnel
            Opex
            Depreciation
    */

  const base = scenarioData.filter((x) => x.scenario === "Base");

  if (!base.length) {
    return;
  }

  const totals = base.reduce(
    (acc, row) => {
      acc.revenue += Number(row.revenue || 0);
      acc.cogs += Number(row.cogs || 0);
      acc.personnel += Number(row.personnel || 0);
      acc.opex += Number(row.opex || 0);
      acc.depreciation += Number(row.depreciation || 0);

      return acc;
    },
    {
      revenue: 0,
      cogs: 0,
      personnel: 0,
      opex: 0,
      depreciation: 0,
    },
  );

  const revenue = totals.revenue * (1 + revenueGrowth);

  const cogs = totals.cogs * (1 + cogsChange);

  const personnel = totals.personnel * (1 + personnelGrowth);

  const opex = totals.opex * (1 + opexGrowth);

  const depreciation = totals.depreciation;

  const grossProfit = revenue - cogs;

  const operatingProfit = grossProfit - personnel - opex - depreciation;

  const operatingExpenses = personnel + opex + depreciation;

  const grossMargin = revenue !== 0 ? grossProfit / revenue : null;

  const operatingMargin = revenue !== 0 ? operatingProfit / revenue : null;

  const output = {
    Revenue: revenue,

    COGS: cogs,

    "Gross Profit": grossProfit,

    Personnel: personnel,

    Opex: opex,

    Depreciation: depreciation,

    "Operating Expenses": operatingExpenses,

    "Operating Profit": operatingProfit,

    "Gross Margin": grossMargin,

    "Operating Margin": operatingMargin,
  };

  $("#scenarioOutput").innerHTML = Object.entries(output)
    .map(([key, value]) => {
      const isPercent = key === "Gross Margin" || key === "Operating Margin";

      const negative = !isPercent && Number(value) < 0;

      return `
                    <div class="scenario-metric">

                        <span>${key}</span>

                        <b class="${negative ? "bad" : ""}">
                            ${isPercent ? pct(value) : money(value)}
                        </b>

                    </div>
                `;
    })
    .join("");

  plot(
    "scenarioChart",
    [
      {
        x: ["Interactive Scenario"],
        y: [operatingProfit],
        type: "bar",
        hovertemplate: "Operating Profit: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "scenarioMarginChart",
    [
      {
        x: ["Gross Margin", "Operating Margin"],
        y: [grossMargin, operatingMargin],
        type: "bar",
        hovertemplate: "%{x}: %{y:.1%}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: ".0%",
      },
    },
  );
}

function updateScenarioCharts(records) {
  const summary = {};

  records.forEach((row) => {
    if (!summary[row.scenario]) {
      summary[row.scenario] = {
        operating_profit: 0,
        operating_margin: 0,
        count: 0,
      };
    }

    summary[row.scenario].operating_profit += Number(row.operating_profit || 0);

    summary[row.scenario].operating_margin += Number(
      row.operating_margin_pct || 0,
    );

    summary[row.scenario].count += 1;
  });

  const order = ["Base", "Upside", "Downside"];

  const available = order.filter((name) => summary[name]);

  plot(
    "scenarioChart",
    [
      {
        x: available,
        y: available.map((name) => summary[name].operating_profit),
        type: "bar",
        hovertemplate: "%{x}<br>Operating Profit: %{y:,.0f}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: "~s",
      },
    },
  );

  plot(
    "scenarioMarginChart",
    [
      {
        x: available,
        y: available.map(
          (name) => summary[name].operating_margin / summary[name].count,
        ),
        type: "bar",
        hovertemplate: "%{x}<br>Operating Margin: %{y:.1%}<extra></extra>",
      },
    ],
    {
      yaxis: {
        ...plotBase.yaxis,
        tickformat: ".0%",
      },
    },
  );
}

/* ================================================================
   METHODOLOGY
   ================================================================ */

async function renderMethodology() {
  let methodology;

  try {
    methodology = await get("/api/methodology");
  } catch (error) {
    console.error("Methodology could not be loaded.", error);

    return;
  }

  const container = $("#methodologySteps");

  if (!container) {
    return;
  }

  container.innerHTML = methodology.pipeline
    .map((step) => {
      return `
                    <div class="method-step">

                        <div class="method-step-number">
                            ${step.step}
                        </div>

                        <div>

                            <h3>
                                ${step.title}
                            </h3>

                            <p>
                                ${step.description}
                            </p>

                        </div>

                        <div class="method-tools">

                            ${step.tools
                              .map(
                                (tool) =>
                                  `<span class="method-tool">${tool}</span>`,
                              )
                              .join("")}

                        </div>

                    </div>
                `;
    })
    .join("");
}

/* ================================================================
   NAVIGATION
   ================================================================ */

const tabTitles = {
  overview: "Executive Summary",

  pnl: "P&L Performance",

  variance: "Budget vs Actual",

  drivers: "Driver Analysis",

  forecast: "Forecast & Outlook",

  cost: "Cost Centres",

  scenario: "Scenario Planning",

  quality: "Data Quality",

  methodology: "Methodology & Data Story",
};

function activateTab(tabName) {
  activeTab = tabName;

  $$(".nav").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });

  $$(".tab").forEach((section) => {
    section.classList.toggle("active", section.id === tabName);
  });

  $("#title").textContent = tabTitles[tabName] || "FP&A Analytics";

  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 80);
}

$$(".nav").forEach((button) => {
  button.addEventListener("click", () => {
    activateTab(button.dataset.tab);
  });
});

/* ================================================================
   FILTER EVENTS
   ================================================================ */

$("#company").addEventListener("change", async () => {
  await loadData();
});

$("#year").addEventListener("change", async () => {
  await loadData();
});

$("#refresh").addEventListener("click", async () => {
  await loadData();
});

/* ================================================================
   WINDOW RESIZE
   ================================================================ */

window.addEventListener("resize", () => {
  const chartIds = [
    "trend",
    "profit",
    "categoryVariance",
    "pnlChart",
    "marginChart",
    "varianceChart",
    "varianceCategory",
    "driverChart",
    "driverContribution",
    "forecastChart",
    "forecastGap",
    "ccChart",
    "ccVarChart",
    "scenarioChart",
    "scenarioMarginChart",
  ];

  chartIds.forEach((id) => {
    const element = document.getElementById(id);

    if (element) {
      try {
        Plotly.Plots.resize(element);
      } catch (error) {
        // Ignore charts that have not rendered yet.
      }
    }
  });
});

/* ================================================================
   INITIALIZE
   ================================================================ */

async function initialize() {
  showLoading();

  try {
    await loadMetadata();

    await loadScenarioData();

    await loadData();
  } catch (error) {
    console.error(error);

    showError(error.message);
  } finally {
    hideLoading();
  }
}

initialize();
