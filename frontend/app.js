/**
 * GIAMS — Green Integrated Agricultural Management System
 * app.js — Logica frontend SPA
 */

const API_URL = "/api";

// ---- Stato globale ----
let parcelleLista = [];
let parcellaInModifica = null;
let utenteInModifica = null;
let raccolteLista = [];
let raccoltaInModifica = null;
let lottiLista = [];
let lottoInModifica = null;
let confezionamentiLista = [];
let confezionamentoInModifica = null;
let produzioneTabAttiva = "raccolte";
let _produzioneReqId = 0;
let contenitoriLista = [];
let contenitoreInModifica = null;
let clientiLista = [];
let clienteInModifica = null;
let venditeLista = [];
let venditaInModifica = null;
let venditeConfezionamentiCache = [];

// ---- Dashboard ----
let dashboardCharts = [];

// ---- Utilita' ----
function debounceSearch(fn, delay = 400) {
  let timer;
  return () => { clearTimeout(timer); timer = setTimeout(fn, delay); };
}

// ---- Paginazione & CSV ----
function renderPaginazione(containerId, infoId, pagina, totalePages, totale, callback) {
  const container = document.getElementById(containerId);
  const info = document.getElementById(infoId);
  if (!container) return;

  if (info) {
    info.textContent = totale > 0
      ? `Pagina ${pagina} di ${totalePages} (${totale} risultati)`
      : "";
  }

  if (totalePages <= 1) { container.innerHTML = ""; return; }

  let html = "";
  html += `<button class="btn" ${pagina <= 1 ? "disabled" : ""} data-page="1">&laquo;</button>`;
  html += `<button class="btn" ${pagina <= 1 ? "disabled" : ""} data-page="${pagina - 1}">&lsaquo;</button>`;

  let start = Math.max(1, pagina - 2);
  let end = Math.min(totalePages, pagina + 2);
  if (end - start < 4) {
    if (start === 1) end = Math.min(totalePages, start + 4);
    else start = Math.max(1, end - 4);
  }

  for (let i = start; i <= end; i++) {
    html += `<button class="btn ${i === pagina ? "active" : ""}" data-page="${i}">${i}</button>`;
  }

  html += `<button class="btn" ${pagina >= totalePages ? "disabled" : ""} data-page="${pagina + 1}">&rsaquo;</button>`;
  html += `<button class="btn" ${pagina >= totalePages ? "disabled" : ""} data-page="${totalePages}">&raquo;</button>`;

  container.innerHTML = html;
  container.querySelectorAll(".btn:not(:disabled)").forEach(btn => {
    btn.addEventListener("click", () => callback(parseInt(btn.dataset.page)));
  });
}

async function scaricaCSV(endpoint, params, nomeFile) {
  try {
    const res = await apiFetch(`${API_URL}/${endpoint}/export/csv?${params}`);
    if (!res.ok) { alert("Errore export CSV"); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nomeFile;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error("Errore export CSV:", e);
    alert("Errore export CSV");
  }
}

// =============================================
// AUTH
// =============================================

function getToken() { return localStorage.getItem("giams_token"); }
function getCurrentUserName() { return localStorage.getItem("giams_user") || "Utente"; }

function checkAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

function logout() {
  localStorage.removeItem("giams_token");
  localStorage.removeItem("giams_token_type");
  localStorage.removeItem("giams_user");
  localStorage.removeItem("giams_is_admin");
  window.location.href = "login.html";
}

/**
 * Escape HTML per prevenire XSS quando si inseriscono stringhe utente in attributi HTML.
 */
function escapeHtml(text) {
  if (!text) return "";
  return String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

/**
 * Wrapper per fetch che aggiunge automaticamente il token JWT.
 * Gestisce 401 (token scaduto) con redirect a login.
 */
// Loading overlay — contatore chiamate attive + delay 200ms
let _apiFetchCount = 0;
let _apiFetchTimer = null;

function _showLoading() {
  const el = document.getElementById("loading-overlay");
  if (!el) return;
  el.style.display = "flex";
  requestAnimationFrame(() => el.classList.add("show"));
}
function _hideLoading() {
  const el = document.getElementById("loading-overlay");
  if (!el) return;
  el.classList.remove("show");
  setTimeout(() => { el.style.display = "none"; }, 150);
}

async function apiFetch(url, options = {}) {
  const token = getToken();
  if (token) {
    options.headers = {
      ...options.headers,
      "Authorization": `Bearer ${token}`,
    };
  }

  _apiFetchCount++;
  if (_apiFetchCount === 1) {
    _apiFetchTimer = setTimeout(_showLoading, 200);
  }

  try {
    const res = await fetch(url, options);
    if (res.status === 401) {
      logout();
      throw new Error("Sessione scaduta");
    }
    return res;
  } finally {
    _apiFetchCount--;
    if (_apiFetchCount === 0) {
      clearTimeout(_apiFetchTimer);
      _apiFetchTimer = null;
      _hideLoading();
    }
  }
}

async function getAppVersion() {
  try {
    const res = await fetch("version.json");
    const data = await res.json();
    return data.version || "1.0.0";
  } catch { return "1.0.0"; }
}

// =============================================
// SIDEBAR NAVIGATION
// =============================================

function setActiveMenu(id) {
  document.querySelectorAll(".sidebar-link").forEach(b => b.classList.remove("active"));
  const el = document.getElementById(id);
  if (el) el.classList.add("active");
  // Cleanup grafici dashboard quando si naviga via
  dashboardCharts.forEach(c => c.destroy());
  dashboardCharts = [];
}

// =============================================
// HOME
// =============================================

async function renderHome() {
  const main = document.getElementById("main-content");
  const version = await getAppVersion();
  const userName = getCurrentUserName();

  main.innerHTML = `
    <div class="d-flex flex-column align-items-center justify-content-center home-welcome"
         style="min-height: 60vh;">
      <h1 class="home-greeting mb-1">GIAMS</h1>
      <p class="home-acronym mb-4">Green Integrated Agricultural Management System</p>
      <img src="assets/LogoGiaMarHome.png" alt="Gia.Mar Green Farm" class="home-logo-img mb-3" />
      <p class="home-greeting-user mb-4">Benvenuto, <span>${userName}</span> &middot; Ver. ${version}</p>

      <div class="row g-3 w-100" style="max-width:750px;">
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-parcelle">
            <div class="quick-card-icon"><i class="fa-solid fa-seedling"></i></div>
            <div class="quick-card-title">Gestione Parcelle</div>
            <div class="quick-card-desc">Terreni e oliveti</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-produzione">
            <div class="quick-card-icon"><i class="fa-solid fa-oil-can"></i></div>
            <div class="quick-card-title">Produzione</div>
            <div class="quick-card-desc">Raccolta e lotti olio</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-contenitori">
            <div class="quick-card-icon"><i class="fa-solid fa-bottle-water"></i></div>
            <div class="quick-card-title">Contenitori</div>
            <div class="quick-card-desc">Tipologie e formati</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-clienti">
            <div class="quick-card-icon"><i class="fa-solid fa-address-book"></i></div>
            <div class="quick-card-title">Clienti</div>
            <div class="quick-card-desc">Anagrafica e contatti</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-fornitori">
            <div class="quick-card-icon"><i class="fa-solid fa-truck-field"></i></div>
            <div class="quick-card-title">Fornitori</div>
            <div class="quick-card-desc">Anagrafica e pagamenti</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-costi">
            <div class="quick-card-icon"><i class="fa-solid fa-file-invoice-dollar"></i></div>
            <div class="quick-card-title">Costi</div>
            <div class="quick-card-desc">Gestione spese e fatture</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-magazzino">
            <div class="quick-card-icon"><i class="fa-solid fa-warehouse"></i></div>
            <div class="quick-card-title">Magazzino</div>
            <div class="quick-card-desc">Giacenze e movimenti</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-vendite">
            <div class="quick-card-icon"><i class="fa-solid fa-cart-shopping"></i></div>
            <div class="quick-card-title">Vendite</div>
            <div class="quick-card-desc">Fatture, DDT, pagamenti</div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="quick-card" id="quick-utenti">
            <div class="quick-card-icon"><i class="fa-solid fa-user-gear"></i></div>
            <div class="quick-card-title">Gestione Utenti</div>
            <div class="quick-card-desc">Accessi piattaforma</div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("quick-parcelle")?.addEventListener("click", () => {
    setActiveMenu("menu-parcelle");
    renderParcelle();
  });
  document.getElementById("quick-produzione")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    renderProduzione();
  });
  document.getElementById("quick-contenitori")?.addEventListener("click", () => {
    setActiveMenu("menu-contenitori");
    renderContenitori();
  });
  document.getElementById("quick-clienti")?.addEventListener("click", () => {
    setActiveMenu("menu-clienti");
    renderClienti();
  });
  document.getElementById("quick-fornitori")?.addEventListener("click", () => {
    setActiveMenu("menu-fornitori");
    renderFornitori();
  });
  document.getElementById("quick-costi")?.addEventListener("click", () => {
    setActiveMenu("menu-costi");
    renderCosti();
  });
  document.getElementById("quick-magazzino")?.addEventListener("click", () => {
    setActiveMenu("menu-magazzino");
    renderMagazzino();
  });
  document.getElementById("quick-vendite")?.addEventListener("click", () => {
    setActiveMenu("menu-vendite");
    renderVendite();
  });
  document.getElementById("quick-utenti")?.addEventListener("click", () => {
    setActiveMenu("menu-utenti");
    renderUtenti();
  });
}

// =============================================
// DASHBOARD ANALITICA
// =============================================

const CHART_COLORS = {
  verde: "rgba(77, 124, 15, 0.85)",
  verdeChiaro: "rgba(134, 239, 172, 0.85)",
  arancio: "rgba(251, 146, 60, 0.85)",
  rosso: "rgba(248, 113, 113, 0.85)",
  blu: "rgba(96, 165, 250, 0.85)",
  giallo: "rgba(250, 204, 21, 0.85)",
  viola: "rgba(192, 132, 252, 0.85)",
  grigio: "rgba(156, 163, 175, 0.5)",
};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: "#d1d5db", font: { size: 11 } } },
  },
  scales: {
    x: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(75,85,99,0.3)" } },
    y: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(75,85,99,0.3)" } },
  },
};

function fmtNum(v, decimals = 0) {
  if (v == null) return "0";
  return Number(v).toLocaleString("it-IT", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

async function renderDashboard() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-dashboard");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  // Tab switching
  document.getElementById("dash-tabs")?.querySelectorAll(".dash-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".dash-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".dash-tab-content").forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const panel = document.getElementById(`dash-panel-${tab.dataset.tab}`);
      if (panel) panel.classList.add("active");
    });
  });

  // Popola selettore anni
  try {
    const resAnni = await apiFetch(`${API_URL}/lotti/anni`);
    const anni = await resAnni.json();
    const sel = document.getElementById("dashboard-anno");
    if (anni.length === 0) {
      sel.innerHTML = '<option value="">Nessun dato</option>';
      return;
    }
    sel.innerHTML = anni.map(a => `<option value="${a}">${a}</option>`).join("");

    // Carica dati con l'anno piu' recente selezionato per top-clienti/giacenza
    await loadDashboardData(anni);

    sel.addEventListener("change", async () => {
      const anno = parseInt(sel.value);
      await loadDashboardFilteredSections(anno);
    });
  } catch (e) {
    console.error("Errore caricamento dashboard:", e);
    main.innerHTML = '<div class="p-4 text-danger">Errore caricamento dashboard.</div>';
  }
}

async function loadDashboardData(anni) {
  // Fetch dati per TUTTI gli anni in parallelo (sezioni 1-4)
  const promises = anni.map(async (anno) => {
    const [lottiRes, costiCampRes, venditeRes, costiRes] = await Promise.all([
      apiFetch(`${API_URL}/lotti/stats?anno=${anno}`),
      apiFetch(`${API_URL}/costi/stats/campagna?anno=${anno}`),
      apiFetch(`${API_URL}/vendite/stats?anno=${anno}`),
      apiFetch(`${API_URL}/costi/stats?anno=${anno}`),
    ]);
    return {
      anno,
      lotti: await lottiRes.json(),
      costiCamp: await costiCampRes.json(),
      vendite: await venditeRes.json(),
      costi: await costiRes.json(),
    };
  });

  const allData = await Promise.all(promises);
  // Ordina per anno crescente
  allData.sort((a, b) => a.anno - b.anno);

  renderDashProduzione(allData);
  renderDashRese(allData);
  renderDashCostoLitro(allData);
  renderDashFatturatoCosti(allData);

  // Sezioni filtrate per anno (anno piu' recente)
  const annoCorrente = anni[0]; // gia' ordinati DESC dal backend
  await loadDashboardFilteredSections(annoCorrente);
}

async function loadDashboardFilteredSections(anno) {
  await Promise.all([
    renderDashTopClienti(anno),
    renderDashGiacenza(),
  ]);
}

// ---- Sezione 1: Andamento Produzione ----
function renderDashProduzione(allData) {
  const tbody = document.querySelector("#dash-table-produzione tbody");
  tbody.innerHTML = allData.map(d => `
    <tr>
      <td>${d.anno}</td>
      <td class="text-end">${fmtNum(d.lotti.totale_kg_olive)}</td>
      <td class="text-end">${fmtNum(d.lotti.totale_kg_olio)}</td>
      <td class="text-end">${fmtNum(d.lotti.totale_litri)}</td>
    </tr>
  `).join("");

  const ctx = document.getElementById("chart-produzione");
  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: allData.map(d => String(d.anno)),
      datasets: [
        { label: "KG Olive", data: allData.map(d => d.lotti.totale_kg_olive), backgroundColor: CHART_COLORS.verde },
        { label: "KG Olio", data: allData.map(d => d.lotti.totale_kg_olio), backgroundColor: CHART_COLORS.arancio },
        { label: "Litri Olio", data: allData.map(d => d.lotti.totale_litri), backgroundColor: CHART_COLORS.blu },
      ],
    },
    options: { ...CHART_DEFAULTS },
  });
  dashboardCharts.push(chart);
}

// ---- Sezione 2: Rese ----
function renderDashRese(allData) {
  const tbody = document.querySelector("#dash-table-rese tbody");
  tbody.innerHTML = allData.map(d => {
    const resaKg = d.lotti.totale_kg_olive > 0 ? (d.lotti.totale_kg_olio / d.lotti.totale_kg_olive * 100) : 0;
    const resaLt = d.lotti.totale_kg_olive > 0 ? (d.lotti.totale_litri / d.lotti.totale_kg_olive * 100) : 0;
    return `<tr>
      <td>${d.anno}</td>
      <td class="text-end">${fmtNum(resaKg, 1)}%</td>
      <td class="text-end">${fmtNum(resaLt, 1)}%</td>
    </tr>`;
  }).join("");

  const ctx = document.getElementById("chart-rese");
  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: allData.map(d => String(d.anno)),
      datasets: [
        {
          label: "Resa KG→KG (%)",
          data: allData.map(d => d.lotti.totale_kg_olive > 0 ? +(d.lotti.totale_kg_olio / d.lotti.totale_kg_olive * 100).toFixed(1) : 0),
          borderColor: CHART_COLORS.verde,
          backgroundColor: "rgba(77, 124, 15, 0.2)",
          fill: true, tension: 0.3,
        },
        {
          label: "Resa KG→LT (%)",
          data: allData.map(d => d.lotti.totale_kg_olive > 0 ? +(d.lotti.totale_litri / d.lotti.totale_kg_olive * 100).toFixed(1) : 0),
          borderColor: CHART_COLORS.blu,
          backgroundColor: "rgba(96, 165, 250, 0.2)",
          fill: true, tension: 0.3,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true, ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => v + "%" } },
      },
    },
  });
  dashboardCharts.push(chart);
}

// ---- Sezione 3: Costo al Litro vs Prezzo Vendita ----
function renderDashCostoLitro(allData) {
  const tbody = document.querySelector("#dash-table-costo-litro tbody");
  tbody.innerHTML = allData.map(d => {
    const litriProd = d.lotti.totale_litri || 0;
    const costoCamp = d.costiCamp.costo_totale_campagna || 0;
    const costoLt = litriProd > 0 ? costoCamp / litriProd : 0;
    const litriVend = d.vendite.litri_venduti || 0;
    const prezzoLt = litriVend > 0 ? d.vendite.fatturato / litriVend : 0;
    const margineLt = prezzoLt - costoLt;
    const cls = margineLt >= 0 ? "margine-positivo" : "margine-negativo";
    return `<tr>
      <td>${d.anno}</td>
      <td class="text-end">${fmtEuro(costoCamp)}</td>
      <td class="text-end">${fmtNum(litriProd)}</td>
      <td class="text-end">${fmtEuro(costoLt)}</td>
      <td class="text-end">${fmtEuro(prezzoLt)}</td>
      <td class="text-end ${cls}">${fmtEuro(margineLt)}</td>
    </tr>`;
  }).join("");

  const ctx = document.getElementById("chart-costo-litro");
  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: allData.map(d => String(d.anno)),
      datasets: [
        {
          label: "Costo/Lt",
          data: allData.map(d => {
            const lt = d.lotti.totale_litri || 0;
            return lt > 0 ? +((d.costiCamp.costo_totale_campagna || 0) / lt).toFixed(2) : 0;
          }),
          backgroundColor: CHART_COLORS.rosso,
        },
        {
          label: "Prezzo Vendita/Lt",
          data: allData.map(d => {
            const lt = d.vendite.litri_venduti || 0;
            return lt > 0 ? +(d.vendite.fatturato / lt).toFixed(2) : 0;
          }),
          backgroundColor: CHART_COLORS.verde,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true, ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => "€ " + v } },
      },
    },
  });
  dashboardCharts.push(chart);
}

// ---- Sezione 4: Fatturato vs Costi ----
function renderDashFatturatoCosti(allData) {
  const tbody = document.querySelector("#dash-table-fatturato tbody");
  tbody.innerHTML = allData.map(d => {
    const margine = d.vendite.fatturato - d.costi.totale_importo;
    const cls = margine >= 0 ? "margine-positivo" : "margine-negativo";
    return `<tr>
      <td>${d.anno}</td>
      <td class="text-end">${fmtEuro(d.vendite.fatturato)}</td>
      <td class="text-end">${fmtEuro(d.costi.totale_importo)}</td>
      <td class="text-end ${cls}">${fmtEuro(margine)}</td>
      <td class="text-end">${fmtEuro(d.vendite.incassato)}</td>
      <td class="text-end">${fmtEuro(d.vendite.da_incassare)}</td>
    </tr>`;
  }).join("");

  const ctx = document.getElementById("chart-fatturato");
  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: allData.map(d => String(d.anno)),
      datasets: [
        { label: "Fatturato", data: allData.map(d => d.vendite.fatturato), backgroundColor: CHART_COLORS.verde },
        { label: "Costi", data: allData.map(d => d.costi.totale_importo), backgroundColor: CHART_COLORS.rosso },
        {
          label: "Margine",
          data: allData.map(d => d.vendite.fatturato - d.costi.totale_importo),
          type: "line",
          borderColor: CHART_COLORS.giallo,
          backgroundColor: "rgba(250, 204, 21, 0.2)",
          fill: false, tension: 0.3, pointRadius: 5,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => "€ " + fmtNum(v) } },
      },
    },
  });
  dashboardCharts.push(chart);
}

// ---- Sezione 5: Top Clienti ----
async function renderDashTopClienti(anno) {
  const tbody = document.querySelector("#dash-table-top-clienti tbody");
  const label = document.getElementById("dash-top-clienti-anno");
  if (label) label.textContent = `(${anno})`;

  try {
    const res = await apiFetch(`${API_URL}/vendite/top-clienti?anno=${anno}&limit=10`);
    const data = await res.json();

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nessun dato</td></tr>';
      return;
    }

    tbody.innerHTML = data.map((c, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${c.denominazione || c.codice}</td>
        <td class="text-end">${c.num_vendite}</td>
        <td class="text-end">${fmtEuro(c.fatturato)}</td>
        <td class="text-end">${fmtEuro(c.incassato)}</td>
      </tr>
    `).join("");

    // Distruggi eventuale chart precedente
    const oldIdx = dashboardCharts.findIndex(c => c.canvas?.id === "chart-top-clienti");
    if (oldIdx >= 0) { dashboardCharts[oldIdx].destroy(); dashboardCharts.splice(oldIdx, 1); }

    const ctx = document.getElementById("chart-top-clienti");
    const chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map(c => c.denominazione || c.codice),
        datasets: [{
          label: "Fatturato",
          data: data.map(c => c.fatturato),
          backgroundColor: CHART_COLORS.verde,
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: "y",
        scales: {
          x: { ...CHART_DEFAULTS.scales.x, ticks: { ...CHART_DEFAULTS.scales.x.ticks, callback: v => "€ " + fmtNum(v) } },
          y: { ...CHART_DEFAULTS.scales.y, ticks: { ...CHART_DEFAULTS.scales.y.ticks, font: { size: 10 } } },
        },
      },
    });
    dashboardCharts.push(chart);
  } catch (e) {
    console.error("Errore top clienti:", e);
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Errore caricamento</td></tr>';
  }
}

// ---- Sezione 6: Giacenza Magazzino ----
async function renderDashGiacenza() {
  const tbody = document.querySelector("#dash-table-giacenza tbody");
  try {
    const res = await apiFetch(`${API_URL}/magazzino/giacenze`);
    const data = await res.json();

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Nessun dato</td></tr>';
      return;
    }

    tbody.innerHTML = data.map(g => `
      <tr>
        <td>${g.confezionamento_codice}</td>
        <td>${g.formato}</td>
        <td class="text-end">${fmtNum(g.capacita_litri, 2)}</td>
        <td class="text-end">${fmtNum(g.totale_carichi)}</td>
        <td class="text-end">${fmtNum(g.totale_scarichi)}</td>
        <td class="text-end fw-bold">${fmtNum(g.giacenza_unita)}</td>
        <td class="text-end fw-bold">${fmtNum(g.giacenza_litri, 1)}</td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Errore giacenza:", e);
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Errore caricamento</td></tr>';
  }
}

// =============================================
// PARCELLE — LISTA
// =============================================

async function renderParcelle() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-parcelle");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  initParcelleListUI();
  await caricaParcelleStats();
  await caricaParcelle();
}

function initParcelleListUI() {
  document.getElementById("btn-nuova-parcella")?.addEventListener("click", () => renderParcellaForm());
  document.getElementById("btn-filtra-parcelle")?.addEventListener("click", () => caricaParcelle());

  // Debounce ricerca testuale (300ms)
  let parcelleSearchTimer = null;
  document.getElementById("filtro-q")?.addEventListener("input", () => {
    clearTimeout(parcelleSearchTimer);
    parcelleSearchTimer = setTimeout(() => caricaParcelle(), 300);
  });
  document.getElementById("filtro-q")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { clearTimeout(parcelleSearchTimer); caricaParcelle(); }
  });

  // Filtro immediato al cambio select
  document.getElementById("filtro-varieta")?.addEventListener("change", () => caricaParcelle());
  document.getElementById("filtro-stato")?.addEventListener("change", () => caricaParcelle());
}

async function caricaParcelleStats() {
  try {
    const res = await apiFetch(`${API_URL}/parcelle/stats`);
    const stats = await res.json();
    document.getElementById("stat-parcelle").textContent = stats.totale_parcelle;
    document.getElementById("stat-ettari").textContent = parseFloat(stats.totale_ettari).toFixed(1);
    document.getElementById("stat-piante").textContent = stats.totale_piante.toLocaleString("it-IT");
    document.getElementById("stat-produttive").textContent = stats.per_stato?.produttivo || 0;
  } catch (err) {
    console.error("Errore caricamento stats:", err);
  }
}

async function caricaParcelle(page = 1) {
  const q = document.getElementById("filtro-q")?.value || "";
  const varieta = document.getElementById("filtro-varieta")?.value || "";
  const stato = document.getElementById("filtro-stato")?.value || "";

  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (varieta) params.append("varieta", varieta);
  if (stato) params.append("stato", stato);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/parcelle/?${params}`);
    const data = await res.json();
    parcelleLista = data.items;
    renderTabellaParcelle();
    renderPaginazione("parcelle-pagination", "parcelle-page-info", data.page, data.pages, data.total, caricaParcelle);
  } catch (err) {
    console.error("Errore caricamento parcelle:", err);
  }
}

const STATO_LABELS = {
  produttivo: "Produttivo",
  giovane: "Giovane",
  riposo: "In riposo",
  dismesso: "Dismesso",
};

function renderTabellaParcelle() {
  const tbody = document.getElementById("parcelle-tbody");
  if (!tbody) return;

  if (parcelleLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-secondary py-4">Nessuna parcella trovata</td></tr>`;
    return;
  }

  tbody.innerHTML = parcelleLista.map(p => `
    <tr>
      <td><strong>${p.codice}</strong></td>
      <td>${p.nome}</td>
      <td>${parseFloat(p.superficie_ettari).toFixed(2)}</td>
      <td>${p.varieta_principale}</td>
      <td>${p.num_piante}</td>
      <td>${p.anno_impianto || "—"}</td>
      <td><span class="badge-stato-${p.stato}">${STATO_LABELS[p.stato] || p.stato}</span></td>
      <td>
        <button class="btn-action btn-action-edit me-1" onclick="renderParcellaForm(${p.id})" title="Modifica">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="btn-action btn-action-delete" onclick="eliminaParcella(${p.id}, '${escapeHtml(p.nome)}')" title="Elimina">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

// =============================================
// PARCELLE — FORM
// =============================================

function renderParcellaForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-parcella-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  parcellaInModifica = id || null;

  if (id) {
    document.getElementById("form-parcella-titolo").textContent = "Modifica Parcella";
    popolaFormParcella(id);
  }

  initParcellaFormUI();
}

function initParcellaFormUI() {
  document.getElementById("btn-torna-lista")?.addEventListener("click", () => {
    setActiveMenu("menu-parcelle");
    renderParcelle();
  });

  document.getElementById("btn-annulla-form")?.addEventListener("click", () => {
    setActiveMenu("menu-parcelle");
    renderParcelle();
  });

  document.getElementById("parcella-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaParcella();
  });
}

async function popolaFormParcella(id) {
  try {
    const res = await apiFetch(`${API_URL}/parcelle/${id}`);
    const p = await res.json();

    document.getElementById("p-codice").value = p.codice || "";
    document.getElementById("p-nome").value = p.nome || "";
    document.getElementById("p-superficie").value = p.superficie_ettari || "";
    document.getElementById("p-num-piante").value = p.num_piante || "";
    document.getElementById("p-varieta-principale").value = p.varieta_principale || "";
    document.getElementById("p-varieta-secondaria").value = p.varieta_secondaria || "";
    document.getElementById("p-anno-impianto").value = p.anno_impianto || "";
    document.getElementById("p-stato").value = p.stato || "produttivo";
    document.getElementById("p-irrigazione").value = p.sistema_irrigazione || "";
    document.getElementById("p-tipo-terreno").value = p.tipo_terreno || "";
    document.getElementById("p-esposizione").value = p.esposizione || "";
    document.getElementById("p-altitudine").value = p.altitudine_m || "";
    document.getElementById("p-note").value = p.note || "";
  } catch (err) {
    console.error("Errore caricamento parcella:", err);
  }
}

async function salvaParcella() {
  const data = {
    codice: document.getElementById("p-codice").value.trim(),
    nome: document.getElementById("p-nome").value.trim(),
    superficie_ettari: parseFloat(document.getElementById("p-superficie").value) || 0,
    num_piante: parseInt(document.getElementById("p-num-piante").value) || 0,
    varieta_principale: document.getElementById("p-varieta-principale").value,
    varieta_secondaria: document.getElementById("p-varieta-secondaria").value || null,
    anno_impianto: parseInt(document.getElementById("p-anno-impianto").value) || null,
    stato: document.getElementById("p-stato").value,
    sistema_irrigazione: document.getElementById("p-irrigazione").value || null,
    tipo_terreno: document.getElementById("p-tipo-terreno").value || null,
    esposizione: document.getElementById("p-esposizione").value || null,
    altitudine_m: parseInt(document.getElementById("p-altitudine").value) || null,
    note: document.getElementById("p-note").value || null,
  };

  const method = parcellaInModifica ? "PUT" : "POST";
  const url = parcellaInModifica
    ? `${API_URL}/parcelle/${parcellaInModifica}`
    : `${API_URL}/parcelle/`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    setActiveMenu("menu-parcelle");
    renderParcelle();
  } catch (err) {
    console.error("Errore salvataggio:", err);
    alert("Errore di connessione.");
  }
}

// =============================================
// ELIMINAZIONE CON CONFERMA
// =============================================

function eliminaParcella(id, nome) {
  mostraConferma(`Eliminare la parcella "${nome}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/parcelle/${id}`, { method: "DELETE" });
      caricaParcelleStats();
      caricaParcelle();
    } catch (err) {
      console.error("Errore eliminazione:", err);
    }
  });
}

function mostraConferma(messaggio, onConfirm, labelConferma = "Elimina", classeConferma = "btn-danger") {
  const overlay = document.createElement("div");
  overlay.className = "modal-confirm-overlay";
  overlay.innerHTML = `
    <div class="modal-confirm-box">
      <h5>${messaggio}</h5>
      <div class="d-flex gap-2 justify-content-center mt-3">
        <button class="btn btn-outline-secondary" id="modal-annulla">Annulla</button>
        <button class="btn ${classeConferma}" id="modal-conferma">${labelConferma}</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector("#modal-annulla").addEventListener("click", () => overlay.remove());
  overlay.querySelector("#modal-conferma").addEventListener("click", () => {
    overlay.remove();
    onConfirm();
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });
}

function mostraDuplicato(messaggio, onForza) {
  const msgEl = document.getElementById("modal-duplicato-msg");
  msgEl.textContent = messaggio;
  const modal = new bootstrap.Modal(document.getElementById("modal-duplicato"));
  const btnForza = document.getElementById("modal-duplicato-forza");
  const handler = () => {
    modal.hide();
    btnForza.removeEventListener("click", handler);
    onForza();
  };
  btnForza.addEventListener("click", handler);
  modal.show();
}

// =============================================
// UTENTI
// =============================================

async function renderUtenti() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-utenti");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  initUtentiUI();
  await caricaUtenti();
}

function initUtentiUI() {
  document.getElementById("utente-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaUtente();
  });

  document.getElementById("btn-reset-utente")?.addEventListener("click", resetFormUtente);
}

async function caricaUtenti() {
  try {
    const res = await apiFetch(`${API_URL}/users/`);
    const utenti = await res.json();
    renderTabellaUtenti(utenti);
  } catch (err) {
    console.error("Errore caricamento utenti:", err);
  }
}

function renderTabellaUtenti(utenti) {
  const tbody = document.getElementById("utenti-tbody");
  if (!tbody) return;

  tbody.innerHTML = utenti.map(u => `
    <tr>
      <td>${u.id}</td>
      <td>${u.username}</td>
      <td>
        <span class="badge-stato-${u.is_admin ? 'produttivo' : 'attivo'}">
          ${u.is_admin ? "Admin" : "Operatore"}
        </span>
      </td>
      <td>
        <span class="badge-stato-${u.is_active ? 'produttivo' : 'dismesso'}">
          ${u.is_active ? "Attivo" : "Disattivato"}
        </span>
      </td>
      <td>
        <button class="btn-action btn-action-edit me-1" onclick="modificaUtente(${u.id}, '${escapeHtml(u.username)}', ${u.is_active}, ${u.is_admin})" title="Modifica">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="btn-action btn-action-delete" onclick="eliminaUtente(${u.id}, '${escapeHtml(u.username)}')" title="Elimina">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

function modificaUtente(id, username, isActive, isAdmin) {
  utenteInModifica = id;
  document.getElementById("form-utente-titolo").textContent = "Modifica Utente";
  document.getElementById("u-username").value = username;
  document.getElementById("u-password").value = "";
  document.getElementById("u-password").required = false;
  document.getElementById("u-attivo").checked = isActive;
  document.getElementById("u-admin").checked = isAdmin;
}

function resetFormUtente() {
  utenteInModifica = null;
  document.getElementById("form-utente-titolo").textContent = "Nuovo Utente";
  document.getElementById("u-username").value = "";
  document.getElementById("u-password").value = "";
  document.getElementById("u-password").required = true;
  document.getElementById("u-attivo").checked = true;
  document.getElementById("u-admin").checked = false;
}

async function salvaUtente() {
  const data = {
    username: document.getElementById("u-username").value.trim(),
    is_active: document.getElementById("u-attivo").checked,
    is_admin: document.getElementById("u-admin").checked,
  };
  const pwd = document.getElementById("u-password").value;
  if (pwd) data.password = pwd;

  const method = utenteInModifica ? "PUT" : "POST";
  const url = utenteInModifica
    ? `${API_URL}/users/${utenteInModifica}`
    : `${API_URL}/users/`;

  if (!utenteInModifica && !pwd) {
    alert("La password e' obbligatoria per un nuovo utente.");
    return;
  }

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore.");
      return;
    }

    resetFormUtente();
    caricaUtenti();
  } catch (err) {
    console.error("Errore:", err);
  }
}

function eliminaUtente(id, username) {
  mostraConferma(`Eliminare l'utente "${username}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/users/${id}`, { method: "DELETE" });
      caricaUtenti();
    } catch (err) {
      console.error("Errore eliminazione utente:", err);
    }
  });
}

// =============================================
// PRODUZIONE — VISTA PRINCIPALE CON TABS
// =============================================

async function renderProduzione() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-produzione");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("tab-raccolte")?.addEventListener("click", () => {
    produzioneTabAttiva = "raccolte";
    _produzioneReqId++;
    aggiornaTabProduzione();
    renderRaccolteLista();
  });
  document.getElementById("tab-lotti")?.addEventListener("click", () => {
    produzioneTabAttiva = "lotti";
    _produzioneReqId++;
    aggiornaTabProduzione();
    renderLottiLista();
  });
  document.getElementById("tab-confezionamento")?.addEventListener("click", () => {
    produzioneTabAttiva = "confezionamento";
    _produzioneReqId++;
    aggiornaTabProduzione();
    renderConfezionamentiLista();
  });

  aggiornaTabProduzione();
  if (produzioneTabAttiva === "raccolte") {
    await renderRaccolteLista();
  } else if (produzioneTabAttiva === "lotti") {
    await renderLottiLista();
  } else {
    await renderConfezionamentiLista();
  }
}

function aggiornaTabProduzione() {
  document.getElementById("tab-raccolte")?.classList.toggle("active", produzioneTabAttiva === "raccolte");
  document.getElementById("tab-lotti")?.classList.toggle("active", produzioneTabAttiva === "lotti");
  document.getElementById("tab-confezionamento")?.classList.toggle("active", produzioneTabAttiva === "confezionamento");
}

// =============================================
// RACCOLTE — LISTA
// =============================================

async function renderRaccolteLista() {
  const myReq = _produzioneReqId;
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-raccolte-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await popolaFiltroAnniRaccolte();
  if (_produzioneReqId !== myReq) return;
  await popolaFiltroParcelle();
  if (_produzioneReqId !== myReq) return;
  initRaccolteListUI();
  await caricaRaccolteStats();
  if (_produzioneReqId !== myReq) return;
  await caricaRaccolte();
}

async function popolaFiltroAnniRaccolte() {
  try {
    const res = await apiFetch(`${API_URL}/raccolte/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-raccolte-anno");
    if (sel) {
      sel.innerHTML = '<option value="">Tutti</option>';
      anni.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = a;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Errore caricamento anni raccolte:", err);
  }
}

function initRaccolteListUI() {
  document.getElementById("btn-nuova-raccolta")?.addEventListener("click", () => renderRaccoltaForm());
  document.getElementById("btn-filtra-raccolte")?.addEventListener("click", () => caricaRaccolte());
  document.getElementById("search-raccolte")?.addEventListener("input", debounceSearch(() => caricaRaccolte()));
}

async function popolaFiltroParcelle() {
  try {
    const res = await apiFetch(`${API_URL}/parcelle/?per_page=100`);
    const parcelle = (await res.json()).items;
    const sel = document.getElementById("filtro-raccolte-parcella");
    if (sel) {
      sel.innerHTML = '<option value="">Tutte</option>';
      parcelle.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.codice} — ${p.nome}`;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Errore caricamento parcelle per filtro:", err);
  }
}

async function caricaRaccolteStats() {
  const anno = document.getElementById("filtro-raccolte-anno")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);

  try {
    const res = await apiFetch(`${API_URL}/raccolte/stats?${params}`);
    const stats = await res.json();
    document.getElementById("stat-raccolte").textContent = stats.totale_raccolte;
    document.getElementById("stat-kg-olive").textContent = parseFloat(stats.totale_kg).toLocaleString("it-IT");
    document.getElementById("stat-media-kg").textContent = parseFloat(stats.media_kg).toFixed(1);
    const costo = parseFloat(stats.costo_totale);
    document.getElementById("stat-costo-raccolte").textContent = costo > 0 ? `€ ${costo.toLocaleString("it-IT")}` : "—";
  } catch (err) {
    console.error("Errore stats raccolte:", err);
  }
}

async function caricaRaccolte(page = 1) {
  const anno = document.getElementById("filtro-raccolte-anno")?.value || "";
  const parcella = document.getElementById("filtro-raccolte-parcella")?.value || "";
  const search = document.getElementById("search-raccolte")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (parcella) params.append("parcella_id", parcella);
  if (search) params.set("search", search);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/raccolte/?${params}`);
    const data = await res.json();
    raccolteLista = data.items;
    renderTabellaRaccolte();
    renderPaginazione("raccolte-pagination", "raccolte-page-info", data.page, data.pages, data.total, caricaRaccolte);
  } catch (err) {
    console.error("Errore caricamento raccolte:", err);
  }
}

const METODO_LABELS = { manuale: "Manuale", meccanico: "Meccanico", misto: "Misto" };
const MATURAZIONE_LABELS = { verde: "Verde", invaiato: "Invaiato", maturo: "Maturo" };

function renderTabellaRaccolte() {
  const tbody = document.getElementById("raccolte-tbody");
  if (!tbody) return;

  if (raccolteLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-secondary py-4">Nessuna raccolta trovata</td></tr>`;
    return;
  }

  tbody.innerHTML = raccolteLista.map(r => {
    const parcNomi = r.parcelle.map(p => `${p.parcella_codice} (${p.kg_olive} kg)`).join(", ") || "—";
    const costo = r.costo_totale_raccolta ? `€ ${parseFloat(r.costo_totale_raccolta).toFixed(0)}` : "—";
    const lottoIcon = r.ha_lotto
      ? `<span class="badge-stato-produttivo">Si</span>`
      : `<button class="btn btn-outline-accent btn-sm" onclick="renderLottoFormDaRaccolta(${r.id})" title="Crea lotto"><i class="fa-solid fa-plus"></i></button>`;
    const resaInfo = r.ha_lotto && r.lotto_resa
      ? `<span class="badge-resa">${parseFloat(r.lotto_resa).toFixed(1)}%</span>`
      : "—";
    return `
      <tr>
        <td><strong>${r.codice}</strong></td>
        <td>${r.data_raccolta}</td>
        <td class="small">${parcNomi}</td>
        <td>${parseFloat(r.kg_olive_totali).toFixed(1)}</td>
        <td>${METODO_LABELS[r.metodo_raccolta] || r.metodo_raccolta}</td>
        <td>${MATURAZIONE_LABELS[r.maturazione] || r.maturazione}</td>
        <td>${costo}</td>
        <td>${lottoIcon}</td>
        <td>${resaInfo}</td>
        <td>
          <button class="btn-action btn-action-edit me-1" onclick="renderRaccoltaForm(${r.id})" title="Modifica">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn-action btn-action-delete" onclick="eliminaRaccolta(${r.id}, '${escapeHtml(r.codice)}')" title="Elimina">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// =============================================
// RACCOLTE — FORM
// =============================================

async function renderRaccoltaForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-raccolta-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  raccoltaInModifica = id || null;

  await renderParcelleSelezione();

  initRaccoltaFormUI();
  initFlatpickr();

  if (id) {
    document.getElementById("form-raccolta-titolo").textContent = "Modifica Raccolta";
    await popolaFormRaccolta(id);
  } else {
    // Auto-genera codice per la nuova raccolta
    const anno = document.getElementById("r-anno").value;
    if (anno) await aggiornaCodicRaccolta(anno);
  }

  // Aggiorna codice quando cambia l'anno
  document.getElementById("r-anno")?.addEventListener("change", async () => {
    if (!raccoltaInModifica) {
      const anno = document.getElementById("r-anno").value;
      if (anno) await aggiornaCodicRaccolta(anno);
    }
  });
}

async function aggiornaCodicRaccolta(anno) {
  try {
    const res = await apiFetch(`${API_URL}/raccolte/next-codice?anno=${anno}`);
    const data = await res.json();
    document.getElementById("r-codice").value = data.codice;
  } catch (err) {
    console.error("Errore generazione codice raccolta:", err);
  }
}

async function renderParcelleSelezione() {
  const container = document.getElementById("raccolta-parcelle-container");
  if (!container) return;

  try {
    const res = await apiFetch(`${API_URL}/parcelle/?per_page=100`);
    const parcelle = (await res.json()).items;

    container.innerHTML = parcelle.map(p => `
      <div class="d-flex align-items-center gap-2 mb-2 raccolta-parcella-row">
        <input type="checkbox" class="form-check-input" id="rp-check-${p.id}" data-parcella-id="${p.id}" />
        <label class="form-check-label flex-grow-1" for="rp-check-${p.id}">
          <strong>${p.codice}</strong> — ${p.nome}
        </label>
        <input type="number" step="0.01" class="form-control form-control-sm" style="width:100px"
               id="rp-kg-${p.id}" placeholder="Kg" disabled />
      </div>
    `).join("");

    parcelle.forEach(p => {
      const check = document.getElementById(`rp-check-${p.id}`);
      const kgInput = document.getElementById(`rp-kg-${p.id}`);
      check?.addEventListener("change", () => {
        kgInput.disabled = !check.checked;
        if (!check.checked) kgInput.value = "";
      });
    });
  } catch (err) {
    console.error("Errore caricamento parcelle:", err);
  }
}

function initRaccoltaFormUI() {
  document.getElementById("btn-torna-raccolte")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    renderProduzione();
  });
  document.getElementById("btn-annulla-raccolta")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    renderProduzione();
  });
  document.getElementById("raccolta-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaRaccolta();
  });
}

async function popolaFormRaccolta(id) {
  try {
    const res = await apiFetch(`${API_URL}/raccolte/${id}`);
    const r = await res.json();

    document.getElementById("r-codice").value = r.codice || "";
    const rDataEl = document.getElementById("r-data");
    if (rDataEl._flatpickr) rDataEl._flatpickr.setDate(r.data_raccolta);
    else rDataEl.value = r.data_raccolta || "";
    document.getElementById("r-anno").value = r.anno_campagna || "";
    document.getElementById("r-kg-totali").value = r.kg_olive_totali || "";
    document.getElementById("r-metodo").value = r.metodo_raccolta || "";
    document.getElementById("r-maturazione").value = r.maturazione || "";
    document.getElementById("r-num-operai").value = r.num_operai || "";
    document.getElementById("r-ore-lavoro").value = r.ore_lavoro || "";
    document.getElementById("r-costo-manodopera").value = r.costo_manodopera || "";
    document.getElementById("r-costo-noleggio").value = r.costo_noleggio || "";
    document.getElementById("r-costo-totale").value = r.costo_totale_raccolta || "";
    document.getElementById("r-note").value = r.note || "";

    // Seleziona le parcelle
    if (r.parcelle) {
      r.parcelle.forEach(p => {
        const check = document.getElementById(`rp-check-${p.parcella_id}`);
        const kgInput = document.getElementById(`rp-kg-${p.parcella_id}`);
        if (check) { check.checked = true; }
        if (kgInput) { kgInput.disabled = false; kgInput.value = p.kg_olive; }
      });
    }
  } catch (err) {
    console.error("Errore caricamento raccolta:", err);
  }
}

async function salvaRaccolta() {
  const parcelle = [];
  document.querySelectorAll(".raccolta-parcella-row").forEach(row => {
    const check = row.querySelector("input[type=checkbox]");
    const kgInput = row.querySelector("input[type=number]");
    if (check?.checked && kgInput?.value) {
      parcelle.push({
        parcella_id: parseInt(check.dataset.parcellaId),
        kg_olive: parseFloat(kgInput.value),
      });
    }
  });

  const data = {
    codice: document.getElementById("r-codice").value.trim(),
    data_raccolta: document.getElementById("r-data").value,
    anno_campagna: parseInt(document.getElementById("r-anno").value),
    kg_olive_totali: parseFloat(document.getElementById("r-kg-totali").value) || 0,
    metodo_raccolta: document.getElementById("r-metodo").value,
    maturazione: document.getElementById("r-maturazione").value,
    num_operai: parseInt(document.getElementById("r-num-operai").value) || null,
    ore_lavoro: parseFloat(document.getElementById("r-ore-lavoro").value) || null,
    costo_manodopera: parseFloat(document.getElementById("r-costo-manodopera").value) || null,
    costo_noleggio: parseFloat(document.getElementById("r-costo-noleggio").value) || null,
    costo_totale_raccolta: parseFloat(document.getElementById("r-costo-totale").value) || null,
    note: document.getElementById("r-note").value || null,
    parcelle,
  };

  const method = raccoltaInModifica ? "PUT" : "POST";
  const url = raccoltaInModifica
    ? `${API_URL}/raccolte/${raccoltaInModifica}`
    : `${API_URL}/raccolte/`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "raccolte";
    renderProduzione();
  } catch (err) {
    console.error("Errore salvataggio raccolta:", err);
    alert("Errore di connessione.");
  }
}

function eliminaRaccolta(id, codice) {
  mostraConferma(`Eliminare la raccolta "${codice}"? Anche il lotto associato verra' eliminato.`, async () => {
    try {
      await apiFetch(`${API_URL}/raccolte/${id}`, { method: "DELETE" });
      caricaRaccolteStats();
      caricaRaccolte();
    } catch (err) {
      console.error("Errore eliminazione raccolta:", err);
    }
  });
}

// =============================================
// LOTTI OLIO — LISTA
// =============================================

async function renderLottiLista() {
  const myReq = _produzioneReqId;
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-lotti-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await popolaFiltroAnniLotti();
  if (_produzioneReqId !== myReq) return;
  initLottiListUI();
  await caricaLottiStats();
  if (_produzioneReqId !== myReq) return;
  await caricaLotti();
}

async function popolaFiltroAnniLotti() {
  try {
    const res = await apiFetch(`${API_URL}/lotti/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-lotti-anno");
    if (sel) {
      sel.innerHTML = '<option value="">Tutti</option>';
      anni.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = a;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Errore caricamento anni lotti:", err);
  }
}

function initLottiListUI() {
  document.getElementById("btn-nuovo-lotto")?.addEventListener("click", () => renderLottoForm());
  document.getElementById("btn-filtra-lotti")?.addEventListener("click", () => caricaLotti());
  document.getElementById("search-lotti")?.addEventListener("input", debounceSearch(() => caricaLotti()));
}

async function caricaLottiStats() {
  const anno = document.getElementById("filtro-lotti-anno")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);

  try {
    const res = await apiFetch(`${API_URL}/lotti/stats?${params}`);
    const stats = await res.json();
    document.getElementById("stat-lotti").textContent = stats.totale_lotti;
    document.getElementById("stat-kg-olive-lotti").textContent = parseFloat(stats.totale_kg_olive).toLocaleString("it-IT");
    document.getElementById("stat-litri").textContent = parseFloat(stats.totale_litri).toLocaleString("it-IT");
    document.getElementById("stat-kg-olio").textContent = parseFloat(stats.totale_kg_olio).toLocaleString("it-IT");
    document.getElementById("stat-resa").textContent = `${stats.resa_media}%`;
    const costo = parseFloat(stats.costo_totale);
    document.getElementById("stat-costo-lotti").textContent = costo > 0 ? `€ ${costo.toLocaleString("it-IT")}` : "—";
  } catch (err) {
    console.error("Errore stats lotti:", err);
  }
}

async function caricaLotti(page = 1) {
  const anno = document.getElementById("filtro-lotti-anno")?.value || "";
  const tipo = document.getElementById("filtro-lotti-tipo")?.value || "";
  const stato = document.getElementById("filtro-lotti-stato")?.value || "";
  const search = document.getElementById("search-lotti")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (tipo) params.append("tipo_olio", tipo);
  if (stato) params.append("stato", stato);
  if (search) params.set("search", search);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/lotti/?${params}`);
    const data = await res.json();
    lottiLista = data.items;
    renderTabellaLotti();
    renderPaginazione("lotti-pagination", "lotti-page-info", data.page, data.pages, data.total, caricaLotti);
  } catch (err) {
    console.error("Errore caricamento lotti:", err);
  }
}

const TIPO_OLIO_LABELS = { evo: "EVO", vergine: "Vergine", lampante: "Lampante" };
const STATO_LOTTO_LABELS = { disponibile: "Disponibile", in_vendita: "In vendita", esaurito: "Esaurito" };

function renderTabellaLotti() {
  const tbody = document.getElementById("lotti-tbody");
  if (!tbody) return;

  if (lottiLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-secondary py-4">Nessun lotto trovato</td></tr>`;
    return;
  }

  tbody.innerHTML = lottiLista.map(l => `
    <tr>
      <td><strong>${l.codice_lotto}</strong></td>
      <td>${l.data_molitura}</td>
      <td>${l.raccolta_codice || "—"}</td>
      <td>${parseFloat(l.kg_olive).toFixed(1)}</td>
      <td>${parseFloat(l.litri_olio).toFixed(1)}</td>
      <td>${l.kg_olio ? parseFloat(l.kg_olio).toFixed(1) : "—"}</td>
      <td>${l.resa_percentuale ? parseFloat(l.resa_percentuale).toFixed(1) + "%" : "—"}</td>
      <td>${TIPO_OLIO_LABELS[l.tipo_olio] || l.tipo_olio}</td>
      <td><span class="badge-stato-${l.stato}">${STATO_LOTTO_LABELS[l.stato] || l.stato}</span></td>
      <td>
        <button class="btn-action btn-action-edit me-1" onclick="renderLottoForm(${l.id})" title="Modifica">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="btn-action btn-action-delete" onclick="eliminaLotto(${l.id}, '${escapeHtml(l.codice_lotto)}')" title="Elimina">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

// =============================================
// LOTTI OLIO — FORM
// =============================================

async function renderLottoForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-lotto-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  lottoInModifica = id || null;

  await popolaSelectRaccolte();

  initLottoFormUI();
  initFlatpickr();

  if (id) {
    document.getElementById("form-lotto-titolo").textContent = "Modifica Lotto Olio";
    await popolaFormLotto(id);
  } else {
    const anno = document.getElementById("l-anno").value;
    if (anno) await aggiornaCodiceLotto(anno);
  }

  // Aggiorna codice quando cambia l'anno
  document.getElementById("l-anno")?.addEventListener("change", async () => {
    if (!lottoInModifica) {
      const anno = document.getElementById("l-anno").value;
      if (anno) await aggiornaCodiceLotto(anno);
    }
  });
}

async function renderLottoFormDaRaccolta(raccoltaId) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-lotto-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  lottoInModifica = null;

  await popolaSelectRaccolte();

  initLottoFormUI();
  initFlatpickr();

  // Pre-seleziona la raccolta e precompila i kg
  const selRaccolta = document.getElementById("l-raccolta");
  if (selRaccolta) selRaccolta.value = raccoltaId;

  try {
    const res = await apiFetch(`${API_URL}/raccolte/${raccoltaId}`);
    const r = await res.json();
    document.getElementById("l-kg").value = r.kg_olive_totali || "";
    document.getElementById("l-anno").value = r.anno_campagna || "2026";
    // Auto-genera codice con anno della raccolta
    await aggiornaCodiceLotto(r.anno_campagna || 2026);
  } catch (err) {
    console.error("Errore precompilazione:", err);
  }

  // Aggiorna codice quando cambia l'anno
  document.getElementById("l-anno")?.addEventListener("change", async () => {
    if (!lottoInModifica) {
      const anno = document.getElementById("l-anno").value;
      if (anno) await aggiornaCodiceLotto(anno);
    }
  });
}

async function aggiornaCodiceLotto(anno) {
  try {
    const res = await apiFetch(`${API_URL}/lotti/next-codice?anno=${anno}`);
    const data = await res.json();
    document.getElementById("l-codice").value = data.codice;
  } catch (err) {
    console.error("Errore generazione codice lotto:", err);
  }
}

async function popolaSelectRaccolte() {
  try {
    const res = await apiFetch(`${API_URL}/raccolte/?per_page=100`);
    const raccolte = (await res.json()).items;
    const sel = document.getElementById("l-raccolta");
    if (sel) {
      sel.innerHTML = '<option value="">Seleziona raccolta...</option>';
      raccolte.filter(r => !r.ha_lotto).forEach(r => {
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = `${r.codice} — ${r.data_raccolta} (${parseFloat(r.kg_olive_totali).toFixed(1)} kg)`;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Errore caricamento raccolte per select:", err);
  }
}

function initLottoFormUI() {
  document.getElementById("btn-torna-lotti")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "lotti";
    renderProduzione();
  });
  document.getElementById("btn-annulla-lotto")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "lotti";
    renderProduzione();
  });
  document.getElementById("lotto-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaLotto();
  });
}

async function popolaFormLotto(id) {
  try {
    const res = await apiFetch(`${API_URL}/lotti/${id}`);
    const l = await res.json();

    document.getElementById("l-codice").value = l.codice_lotto || "";

    // Per modifica, aggiungi la raccolta attuale al select anche se ha gia' lotto
    const sel = document.getElementById("l-raccolta");
    if (sel && l.raccolta_id) {
      let found = false;
      for (const opt of sel.options) {
        if (opt.value == l.raccolta_id) { found = true; break; }
      }
      if (!found) {
        const opt = document.createElement("option");
        opt.value = l.raccolta_id;
        opt.textContent = l.raccolta_codice || `Raccolta #${l.raccolta_id}`;
        sel.appendChild(opt);
      }
      sel.value = l.raccolta_id;
    }

    document.getElementById("l-anno").value = l.anno_campagna || "";
    const lDataEl = document.getElementById("l-data");
    if (lDataEl._flatpickr) lDataEl._flatpickr.setDate(l.data_molitura);
    else lDataEl.value = l.data_molitura || "";
    document.getElementById("l-frantoio").value = l.frantoio || "";
    document.getElementById("l-kg").value = l.kg_olive || "";
    document.getElementById("l-litri").value = l.litri_olio || "";
    document.getElementById("l-kg-olio").value = l.kg_olio || "";
    document.getElementById("l-tipo").value = l.tipo_olio || "";
    document.getElementById("l-certificazione").value = l.certificazione || "";
    document.getElementById("l-acidita").value = l.acidita || "";
    document.getElementById("l-perossidi").value = l.perossidi || "";
    document.getElementById("l-polifenoli").value = l.polifenoli || "";
    document.getElementById("l-costo-frantoio").value = l.costo_frantoio || "";
    document.getElementById("l-costo-trasporto").value = l.costo_trasporto || "";
    document.getElementById("l-costo-totale").value = l.costo_totale_molitura || "";
    document.getElementById("l-stato").value = l.stato || "disponibile";
    document.getElementById("l-note").value = l.note || "";
  } catch (err) {
    console.error("Errore caricamento lotto:", err);
  }
}

async function salvaLotto() {
  const data = {
    codice_lotto: document.getElementById("l-codice").value.trim(),
    raccolta_id: parseInt(document.getElementById("l-raccolta").value),
    anno_campagna: parseInt(document.getElementById("l-anno").value),
    data_molitura: document.getElementById("l-data").value,
    frantoio: document.getElementById("l-frantoio").value.trim(),
    kg_olive: parseFloat(document.getElementById("l-kg").value) || 0,
    litri_olio: parseFloat(document.getElementById("l-litri").value) || 0,
    kg_olio: parseFloat(document.getElementById("l-kg-olio").value) || null,
    tipo_olio: document.getElementById("l-tipo").value,
    certificazione: document.getElementById("l-certificazione").value || null,
    acidita: parseFloat(document.getElementById("l-acidita").value) || null,
    perossidi: parseFloat(document.getElementById("l-perossidi").value) || null,
    polifenoli: parseInt(document.getElementById("l-polifenoli").value) || null,
    costo_frantoio: parseFloat(document.getElementById("l-costo-frantoio").value) || null,
    costo_trasporto: parseFloat(document.getElementById("l-costo-trasporto").value) || null,
    costo_totale_molitura: parseFloat(document.getElementById("l-costo-totale").value) || null,
    stato: document.getElementById("l-stato").value,
    note: document.getElementById("l-note").value || null,
  };

  const method = lottoInModifica ? "PUT" : "POST";
  const url = lottoInModifica
    ? `${API_URL}/lotti/${lottoInModifica}`
    : `${API_URL}/lotti/`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "lotti";
    renderProduzione();
  } catch (err) {
    console.error("Errore salvataggio lotto:", err);
    alert("Errore di connessione.");
  }
}

function eliminaLotto(id, codice) {
  mostraConferma(`Eliminare il lotto "${codice}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/lotti/${id}`, { method: "DELETE" });
      caricaLottiStats();
      caricaLotti();
    } catch (err) {
      console.error("Errore eliminazione lotto:", err);
    }
  });
}

// =============================================
// CONFEZIONAMENTO — LISTA
// =============================================

// Contenitori caricati dinamicamente dal backend
let contenitoriCache = [];

async function caricaContenitoriCache() {
  try {
    const res = await apiFetch(`${API_URL}/contenitori/?per_page=100`);
    const data = await res.json();
    contenitoriCache = data.items || data;
  } catch (err) {
    console.error("Errore caricamento contenitori:", err);
    contenitoriCache = [];
  }
  return contenitoriCache;
}

function getContenitoreLabel(codice) {
  const c = contenitoriCache.find(ct => ct.codice === codice);
  return c ? c.descrizione : codice;
}

function getContenitoreCapacita(codice) {
  const c = contenitoriCache.find(ct => ct.codice === codice);
  return c ? c.capacita_litri : 0;
}

function getContenitoreById(id) {
  return contenitoriCache.find(ct => ct.id === id);
}

async function renderConfezionamentiLista() {
  const myReq = _produzioneReqId;
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-confezionamenti-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await caricaContenitoriCache();
  if (_produzioneReqId !== myReq) return;
  await popolaFiltroAnniConf();
  if (_produzioneReqId !== myReq) return;
  popolaFiltroContenitori();
  initConfListUI();
  await caricaConfStats();
  if (_produzioneReqId !== myReq) return;
  await caricaConfezionamenti();
}

function popolaFiltroContenitori() {
  const sel = document.getElementById("filtro-conf-formato");
  if (!sel) return;
  sel.innerHTML = '<option value="">Tutti</option>';
  contenitoriCache.forEach(ct => {
    const opt = document.createElement("option");
    opt.value = ct.codice;
    opt.textContent = ct.descrizione;
    sel.appendChild(opt);
  });
}

async function popolaFiltroAnniConf() {
  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-conf-anno");
    if (sel) {
      sel.innerHTML = '<option value="">Tutti</option>';
      anni.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = a;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Errore caricamento anni confezionamenti:", err);
  }
}

function initConfListUI() {
  document.getElementById("btn-nuovo-conf")?.addEventListener("click", () => renderConfezionamentoForm());
  document.getElementById("btn-filtra-conf")?.addEventListener("click", () => {
    caricaConfStats();
    caricaConfezionamenti();
  });
  document.getElementById("search-confezionamenti")?.addEventListener("input", debounceSearch(() => caricaConfezionamenti()));
}

async function caricaConfStats() {
  const anno = document.getElementById("filtro-conf-anno")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);

  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/stats?${params}`);
    const stats = await res.json();
    document.getElementById("stat-conf-totale").textContent = stats.totale_confezionamenti;
    document.getElementById("stat-conf-unita").textContent = stats.totale_unita.toLocaleString("it-IT");
    document.getElementById("stat-conf-litri").textContent = parseFloat(stats.totale_litri).toLocaleString("it-IT");
    const costo = parseFloat(stats.costo_totale);
    document.getElementById("stat-conf-costo").textContent = costo > 0 ? `€ ${costo.toLocaleString("it-IT")}` : "—";
  } catch (err) {
    console.error("Errore stats confezionamenti:", err);
  }
}

async function caricaConfezionamenti(page = 1) {
  const anno = document.getElementById("filtro-conf-anno")?.value || "";
  const formato = document.getElementById("filtro-conf-formato")?.value || "";
  const search = document.getElementById("search-confezionamenti")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (formato) params.append("formato", formato);
  if (search) params.set("search", search);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/?${params}`);
    const data = await res.json();
    confezionamentiLista = data.items;
    renderTabellaConf();
    renderPaginazione("conf-pagination", "conf-page-info", data.page, data.pages, data.total, caricaConfezionamenti);
  } catch (err) {
    console.error("Errore caricamento confezionamenti:", err);
  }
}

function renderTabellaConf() {
  const tbody = document.getElementById("conf-tbody");
  if (!tbody) return;

  if (confezionamentiLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-secondary py-4">Nessun confezionamento trovato</td></tr>`;
    return;
  }

  tbody.innerHTML = confezionamentiLista.map(c => {
    const lottiNomi = c.lotti.map(l => `${l.lotto_codice} (${l.litri_utilizzati}L)`).join(", ") || "—";
    const costo = c.costo_totale ? `€ ${parseFloat(c.costo_totale).toFixed(0)}` : "—";
    const prezzo = c.prezzo_unitario ? `€ ${parseFloat(c.prezzo_unitario).toFixed(2)}` : "—";
    const desc = c.contenitore_descrizione || getContenitoreLabel(c.formato);
    return `
      <tr>
        <td><strong>${c.codice}</strong></td>
        <td>${c.data_confezionamento}</td>
        <td><span class="badge-contenitore">${desc}</span></td>
        <td>${c.num_unita}</td>
        <td>${parseFloat(c.litri_totali).toFixed(1)}</td>
        <td class="small">${lottiNomi}</td>
        <td>${costo}</td>
        <td class="text-end">${prezzo}</td>
        <td>
          <button class="btn-action btn-action-edit me-1" onclick="renderConfezionamentoForm(${c.id})" title="Modifica">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn-action btn-action-delete" onclick="eliminaConfezionamento(${c.id}, '${escapeHtml(c.codice)}')" title="Elimina">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// =============================================
// CONFEZIONAMENTO — FORM
// =============================================

async function renderConfezionamentoForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-confezionamento-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  confezionamentoInModifica = id || null;

  await caricaContenitoriCache();
  popolaContenitoriSelect();
  await renderLottiSelezione();
  initConfFormCalcolo();
  initConfFormUI();
  initFlatpickr();

  if (id) {
    document.getElementById("form-conf-titolo").textContent = "Modifica Confezionamento";
    await popolaFormConf(id);
  }
}

function popolaContenitoriSelect() {
  const sel = document.getElementById("cf-formato");
  if (!sel) return;
  sel.innerHTML = '<option value="">Seleziona...</option>';
  contenitoriCache.forEach(ct => {
    const opt = document.createElement("option");
    opt.value = ct.id;
    opt.textContent = ct.descrizione;
    opt.dataset.cap = ct.capacita_litri;
    opt.dataset.codice = ct.codice;
    sel.appendChild(opt);
  });
}

async function renderLottiSelezione() {
  const container = document.getElementById("conf-lotti-container");
  if (!container) return;

  try {
    const res = await apiFetch(`${API_URL}/lotti/?per_page=100`);
    const lotti = (await res.json()).items;

    container.innerHTML = lotti.map(l => `
      <div class="d-flex align-items-center gap-2 mb-2 conf-lotto-row">
        <input type="checkbox" class="form-check-input" id="cl-check-${l.id}" data-lotto-id="${l.id}" />
        <label class="form-check-label flex-grow-1" for="cl-check-${l.id}">
          <strong>${l.codice_lotto}</strong> — ${parseFloat(l.litri_olio).toFixed(1)}L
        </label>
        <input type="number" step="0.01" class="form-control form-control-sm" style="width:100px"
               id="cl-litri-${l.id}" placeholder="Litri" disabled />
      </div>
    `).join("");

    lotti.forEach(l => {
      const check = document.getElementById(`cl-check-${l.id}`);
      const litriInput = document.getElementById(`cl-litri-${l.id}`);
      check?.addEventListener("change", () => {
        litriInput.disabled = !check.checked;
        if (!check.checked) litriInput.value = "";
      });
    });
  } catch (err) {
    console.error("Errore caricamento lotti per selezione:", err);
  }
}

function initConfFormCalcolo() {
  const formatoSel = document.getElementById("cf-formato");
  const numInput = document.getElementById("cf-num-unita");
  const litriOutput = document.getElementById("cf-litri-totali");

  function ricalcola() {
    const selectedOpt = formatoSel?.selectedOptions[0];
    const num = parseInt(numInput?.value) || 0;
    const cap = parseFloat(selectedOpt?.dataset.cap) || 0;
    if (litriOutput) litriOutput.value = (num * cap).toFixed(2);
  }

  formatoSel?.addEventListener("change", ricalcola);
  numInput?.addEventListener("input", ricalcola);
}

function initConfFormUI() {
  document.getElementById("btn-torna-conf")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "confezionamento";
    renderProduzione();
  });
  document.getElementById("btn-annulla-conf")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "confezionamento";
    renderProduzione();
  });
  document.getElementById("conf-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaConfezionamento();
  });
}

async function popolaFormConf(id) {
  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/${id}`);
    const c = await res.json();

    document.getElementById("cf-codice").value = c.codice || "";
    const cfDataEl = document.getElementById("cf-data");
    if (cfDataEl._flatpickr) cfDataEl._flatpickr.setDate(c.data_confezionamento);
    else cfDataEl.value = c.data_confezionamento || "";
    document.getElementById("cf-anno").value = c.anno_campagna || "";
    document.getElementById("cf-formato").value = c.contenitore_id || "";
    document.getElementById("cf-num-unita").value = c.num_unita || "";
    document.getElementById("cf-litri-totali").value = c.litri_totali || "";
    document.getElementById("cf-costo").value = c.costo_totale || "";
    document.getElementById("cf-prezzo-unitario").value = c.prezzo_unitario || "";
    document.getElementById("cf-note").value = c.note || "";

    if (c.lotti) {
      c.lotti.forEach(l => {
        const check = document.getElementById(`cl-check-${l.lotto_id}`);
        const litriInput = document.getElementById(`cl-litri-${l.lotto_id}`);
        if (check) { check.checked = true; }
        if (litriInput) { litriInput.disabled = false; litriInput.value = l.litri_utilizzati; }
      });
    }
  } catch (err) {
    console.error("Errore caricamento confezionamento:", err);
  }
}

async function salvaConfezionamento() {
  const lotti = [];
  document.querySelectorAll(".conf-lotto-row").forEach(row => {
    const check = row.querySelector("input[type=checkbox]");
    const litriInput = row.querySelector("input[type=number]");
    if (check?.checked && litriInput?.value) {
      lotti.push({
        lotto_id: parseInt(check.dataset.lottoId),
        litri_utilizzati: parseFloat(litriInput.value),
      });
    }
  });

  const formatoSel = document.getElementById("cf-formato");
  const selectedOpt = formatoSel?.selectedOptions[0];
  const contenitoreId = parseInt(formatoSel.value) || 0;
  const cap = parseFloat(selectedOpt?.dataset.cap) || 0;
  const codice_cont = selectedOpt?.dataset.codice || "";
  const numUnita = parseInt(document.getElementById("cf-num-unita").value) || 0;

  const data = {
    codice: document.getElementById("cf-codice").value.trim(),
    data_confezionamento: document.getElementById("cf-data").value,
    anno_campagna: parseInt(document.getElementById("cf-anno").value),
    contenitore_id: contenitoreId,
    formato: codice_cont,
    capacita_litri: cap,
    num_unita: numUnita,
    litri_totali: numUnita * cap,
    costo_totale: parseFloat(document.getElementById("cf-costo").value) || null,
    prezzo_unitario: parseFloat(document.getElementById("cf-prezzo-unitario").value) || null,
    note: document.getElementById("cf-note").value || null,
    lotti,
  };

  const method = confezionamentoInModifica ? "PUT" : "POST";
  const url = confezionamentoInModifica
    ? `${API_URL}/confezionamenti/${confezionamentoInModifica}`
    : `${API_URL}/confezionamenti/`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    setActiveMenu("menu-produzione");
    produzioneTabAttiva = "confezionamento";
    renderProduzione();
  } catch (err) {
    console.error("Errore salvataggio confezionamento:", err);
    alert("Errore di connessione.");
  }
}

function eliminaConfezionamento(id, codice) {
  mostraConferma(`Eliminare il confezionamento "${codice}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/confezionamenti/${id}`, { method: "DELETE" });
      caricaConfStats();
      caricaConfezionamenti();
    } catch (err) {
      console.error("Errore eliminazione confezionamento:", err);
    }
  });
}

// =============================================
// CONTENITORI — LISTA
// =============================================

let contenitoriPage = 1;
let contenitoriSearch = "";
let contenitoriTutti = false;

async function renderContenitori() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-contenitori");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-nuovo-contenitore")?.addEventListener("click", () => renderContenitoreForm());

  const searchInput = document.getElementById("contenitori-search");
  let searchTimer = null;
  searchInput?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      contenitoriSearch = searchInput.value.trim();
      contenitoriPage = 1;
      caricaContenitori();
    }, 300);
  });

  const chkTutti = document.getElementById("contenitori-mostra-tutti");
  chkTutti?.addEventListener("change", () => {
    contenitoriTutti = chkTutti.checked;
    contenitoriPage = 1;
    caricaContenitori();
  });

  contenitoriPage = 1;
  contenitoriSearch = "";
  contenitoriTutti = false;
  await caricaContenitori();
}

async function caricaContenitori() {
  try {
    let url = `${API_URL}/contenitori/?page=${contenitoriPage}&per_page=10`;
    if (contenitoriTutti) url += "&tutti=true";
    if (contenitoriSearch) url += `&q=${encodeURIComponent(contenitoriSearch)}`;
    const res = await apiFetch(url);
    const data = await res.json();
    renderContenitoriGrid(data);
  } catch (err) {
    console.error("Errore caricamento contenitori:", err);
  }
}

function renderContenitoriGrid(data) {
  const grid = document.getElementById("contenitori-grid");
  if (!grid) return;

  const items = data.items || [];

  if (items.length === 0) {
    grid.innerHTML = `<div class="text-center text-secondary py-5">Nessun contenitore trovato</div>`;
    document.getElementById("contenitori-paginazione").innerHTML = "";
    return;
  }

  grid.innerHTML = `<div class="row g-3">${items.map(ct => {
    const fotoHtml = ct.foto
      ? `<img src="/uploads/${ct.foto}" alt="${ct.descrizione}" class="ct-card-img" />`
      : `<div class="ct-card-placeholder"><i class="fa-solid fa-bottle-water fa-2x"></i></div>`;
    const badgeAttivo = ct.attivo
      ? `<span class="badge bg-success">Attivo</span>`
      : `<span class="badge bg-secondary">Inattivo</span>`;

    return `
      <div class="col-md-6 col-lg-4">
        <div class="card ct-card ${!ct.attivo ? 'ct-card-inattivo' : ''}">
          <div class="ct-card-body">
            <div class="ct-card-title">${ct.descrizione}</div>
            <div class="ct-card-info">
              <span class="ct-card-cap">${ct.capacita_litri}L</span>
              ${badgeAttivo}
            </div>
            <div class="ct-card-code small text-secondary">${ct.codice}</div>
            <div class="ct-card-actions">
              <button class="btn-action btn-action-edit me-1" onclick="renderContenitoreForm(${ct.id})" title="Modifica">
                <i class="fa-solid fa-pen-to-square"></i>
              </button>
              <button class="btn-action btn-action-delete" onclick="eliminaContenitore(${ct.id}, '${escapeHtml(ct.descrizione)}')" title="Elimina">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
          </div>
          <div class="ct-card-img-wrap">${fotoHtml}</div>
        </div>
      </div>
    `;
  }).join("")}</div>`;

  renderPaginazione("contenitori-paginazione", null, data.page, data.pages, data.total, (p) => {
    contenitoriPage = p;
    caricaContenitori();
  });
}

// =============================================
// CONTENITORI — FORM
// =============================================

async function renderContenitoreForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-contenitore-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  contenitoreInModifica = id || null;

  if (id) {
    document.getElementById("form-contenitore-titolo").textContent = "Modifica Contenitore";
    await popolaFormContenitore(id);
  }

  // Preview foto su selezione file
  document.getElementById("ct-foto-input")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        document.getElementById("ct-foto-preview").innerHTML = `<img src="${ev.target.result}" class="ct-foto-preview-img" />`;
      };
      reader.readAsDataURL(file);
    }
  });

  document.getElementById("btn-torna-contenitori")?.addEventListener("click", () => {
    setActiveMenu("menu-contenitori");
    renderContenitori();
  });
  document.getElementById("btn-annulla-contenitore")?.addEventListener("click", () => {
    setActiveMenu("menu-contenitori");
    renderContenitori();
  });
  document.getElementById("contenitore-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaContenitore();
  });
}

async function popolaFormContenitore(id) {
  try {
    const res = await apiFetch(`${API_URL}/contenitori/${id}`);
    const ct = await res.json();

    document.getElementById("ct-codice").value = ct.codice || "";
    document.getElementById("ct-descrizione").value = ct.descrizione || "";
    document.getElementById("ct-capacita").value = ct.capacita_litri || "";
    document.getElementById("ct-attivo").checked = ct.attivo !== false;

    if (ct.foto) {
      document.getElementById("ct-foto-preview").innerHTML = `<img src="/uploads/${ct.foto}" class="ct-foto-preview-img" />`;
    }
  } catch (err) {
    console.error("Errore caricamento contenitore:", err);
  }
}

async function salvaContenitore() {
  const payload = {
    codice: document.getElementById("ct-codice").value.trim(),
    descrizione: document.getElementById("ct-descrizione").value.trim(),
    capacita_litri: parseFloat(document.getElementById("ct-capacita").value) || 0,
    attivo: document.getElementById("ct-attivo").checked,
  };

  const method = contenitoreInModifica ? "PUT" : "POST";
  const url = contenitoreInModifica
    ? `${API_URL}/contenitori/${contenitoreInModifica}`
    : `${API_URL}/contenitori/`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    const saved = await res.json();

    // Upload foto se selezionata
    const fotoInput = document.getElementById("ct-foto-input");
    if (fotoInput?.files.length > 0) {
      const formData = new FormData();
      formData.append("file", fotoInput.files[0]);
      await apiFetch(`${API_URL}/contenitori/${saved.id}/foto`, {
        method: "POST",
        body: formData,
      });
    }

    setActiveMenu("menu-contenitori");
    renderContenitori();
  } catch (err) {
    console.error("Errore salvataggio contenitore:", err);
    alert("Errore di connessione.");
  }
}

function eliminaContenitore(id, descrizione, force = false) {
  const doDelete = async () => {
    try {
      const forceParam = force ? "?force=true" : "";
      const res = await apiFetch(`${API_URL}/contenitori/${id}${forceParam}`, { method: "DELETE" });
      if (res.status === 409) {
        const conflict = await res.json();
        mostraDuplicato(conflict.detail, () => eliminaContenitore(id, descrizione, true));
        return;
      }
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore durante l'eliminazione.");
        return;
      }
      caricaContenitori();
    } catch (err) {
      console.error("Errore eliminazione contenitore:", err);
    }
  };

  if (force) {
    doDelete();
  } else {
    mostraConferma(`Eliminare il contenitore "${descrizione}"?`, doDelete);
  }
}

// =============================================
// CLIENTI — LISTA
// =============================================

async function renderClienti() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-clienti");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  initClientiListUI();
  await caricaClientiStats();
  await caricaClienti();
}

function initClientiListUI() {
  document.getElementById("btn-nuovo-cliente")?.addEventListener("click", () => renderClienteForm());
  document.getElementById("btn-filtra-clienti")?.addEventListener("click", () => {
    caricaClientiStats();
    caricaClienti();
  });
  document.getElementById("filtro-clienti-q")?.addEventListener("keyup", (e) => {
    if (e.key === "Enter") { caricaClientiStats(); caricaClienti(); }
  });
  document.getElementById("btn-export-clienti-csv")?.addEventListener("click", () => {
    const params = new URLSearchParams();
    const q = document.getElementById("filtro-clienti-q")?.value;
    const tipo = document.getElementById("filtro-clienti-tipo")?.value;
    const tutti = document.getElementById("filtro-clienti-tutti")?.checked;
    if (q) params.set("q", q);
    if (tipo) params.set("tipo", tipo);
    if (tutti) params.set("tutti", "true");
    scaricaCSV("clienti", params.toString(), "Clienti.csv");
  });
}

async function caricaClientiStats() {
  try {
    const res = await apiFetch(`${API_URL}/clienti/stats`);
    const s = await res.json();
    document.getElementById("stat-clienti-totale").textContent = s.totale;
    document.getElementById("stat-clienti-attivi").textContent = s.attivi;
    document.getElementById("stat-clienti-privati").textContent = s.privati;
    document.getElementById("stat-clienti-aziende").textContent = s.aziende;
  } catch (err) {
    console.error("Errore stats clienti:", err);
  }
}

async function caricaClienti(page = 1) {
  const q = document.getElementById("filtro-clienti-q")?.value || "";
  const tipo = document.getElementById("filtro-clienti-tipo")?.value || "";
  const tutti = document.getElementById("filtro-clienti-tutti")?.checked || false;
  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (tipo) params.append("tipo", tipo);
  if (tutti) params.append("tutti", "true");
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/clienti/?${params}`);
    const data = await res.json();
    clientiLista = data.items;
    renderTabellaClienti();
    renderPaginazione("clienti-pagination", "clienti-page-info", data.page, data.pages, data.total, caricaClienti);
  } catch (err) {
    console.error("Errore caricamento clienti:", err);
  }
}

function renderTabellaClienti() {
  const tbody = document.getElementById("clienti-tbody");
  if (!tbody) return;

  if (clientiLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-secondary py-4">Nessun cliente trovato</td></tr>`;
    return;
  }

  tbody.innerHTML = clientiLista.map(c => {
    const tipoBadge = c.tipo_cliente === "azienda"
      ? `<span class="badge-tipo-azienda">Azienda</span>`
      : `<span class="badge-tipo-privato">Privato</span>`;
    const statoBadge = c.attivo
      ? `<span class="badge bg-success">Attivo</span>`
      : `<span class="badge bg-secondary">Inattivo</span>`;
    const sconto = c.sconto_default ? `${c.sconto_default}%` : "—";
    const citta = c.citta ? `${c.citta} (${c.provincia || ""})` : "—";

    return `
      <tr>
        <td><strong>${c.codice}</strong></td>
        <td>${tipoBadge}</td>
        <td>${c.denominazione || "—"}</td>
        <td>${citta}</td>
        <td>${c.telefono || "—"}</td>
        <td>${c.email || "—"}</td>
        <td>${sconto}</td>
        <td>${statoBadge}</td>
        <td>
          <button class="btn-action btn-action-edit me-1" onclick="renderClienteForm(${c.id})" title="Modifica">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn-action btn-action-delete" onclick="eliminaCliente(${c.id}, '${escapeHtml(c.denominazione || c.codice)}')" title="Elimina">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// =============================================
// CLIENTI — FORM
// =============================================

async function renderClienteForm(id) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-cliente-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  clienteInModifica = id || null;

  initClienteFormUI();

  if (id) {
    document.getElementById("form-cliente-titolo").textContent = "Modifica Cliente";
    await popolaFormCliente(id);
  }
}

function initClienteFormUI() {
  // Toggle sezioni privato/azienda
  const tipoSel = document.getElementById("cli-tipo");
  tipoSel?.addEventListener("change", () => toggleSezioniCliente(tipoSel.value));

  // Copia indirizzo fatturazione -> consegna
  document.getElementById("btn-copia-indirizzo")?.addEventListener("click", () => {
    document.getElementById("cli-cons-indirizzo").value = document.getElementById("cli-indirizzo").value;
    document.getElementById("cli-cons-cap").value = document.getElementById("cli-cap").value;
    document.getElementById("cli-cons-citta").value = document.getElementById("cli-citta").value;
    document.getElementById("cli-cons-provincia").value = document.getElementById("cli-provincia").value;
  });

  document.getElementById("btn-torna-clienti")?.addEventListener("click", () => {
    setActiveMenu("menu-clienti");
    renderClienti();
  });
  document.getElementById("btn-annulla-cliente")?.addEventListener("click", () => {
    setActiveMenu("menu-clienti");
    renderClienti();
  });
  document.getElementById("cliente-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await salvaCliente();
  });
}

function toggleSezioniCliente(tipo) {
  const privato = document.getElementById("cli-sezione-privato");
  const azienda = document.getElementById("cli-sezione-azienda");
  if (privato) privato.style.display = tipo === "privato" ? "block" : "none";
  if (azienda) azienda.style.display = tipo === "azienda" ? "block" : "none";
}

async function popolaFormCliente(id) {
  try {
    const res = await apiFetch(`${API_URL}/clienti/${id}`);
    const c = await res.json();

    document.getElementById("cli-codice").value = c.codice || "";
    document.getElementById("cli-tipo").value = c.tipo_cliente || "";
    toggleSezioniCliente(c.tipo_cliente);

    // Privato
    document.getElementById("cli-nome").value = c.nome || "";
    document.getElementById("cli-cognome").value = c.cognome || "";
    document.getElementById("cli-cf").value = c.codice_fiscale || "";

    // Azienda
    document.getElementById("cli-ragione").value = c.ragione_sociale || "";
    document.getElementById("cli-piva").value = c.partita_iva || "";
    document.getElementById("cli-sdi").value = c.codice_sdi || "0000000";
    document.getElementById("cli-pec").value = c.pec || "";
    document.getElementById("cli-ref-nome").value = c.referente_nome || "";
    document.getElementById("cli-ref-tel").value = c.referente_telefono || "";

    // Contatti
    document.getElementById("cli-email").value = c.email || "";
    document.getElementById("cli-telefono").value = c.telefono || "";

    // Indirizzo fatturazione
    document.getElementById("cli-indirizzo").value = c.indirizzo || "";
    document.getElementById("cli-cap").value = c.cap || "";
    document.getElementById("cli-citta").value = c.citta || "";
    document.getElementById("cli-provincia").value = c.provincia || "";

    // Indirizzo consegna
    document.getElementById("cli-cons-indirizzo").value = c.consegna_indirizzo || "";
    document.getElementById("cli-cons-cap").value = c.consegna_cap || "";
    document.getElementById("cli-cons-citta").value = c.consegna_citta || "";
    document.getElementById("cli-cons-provincia").value = c.consegna_provincia || "";

    // Commerciale
    document.getElementById("cli-sconto").value = c.sconto_default || "";
    document.getElementById("cli-attivo").checked = c.attivo !== false;
    document.getElementById("cli-note").value = c.note || "";
  } catch (err) {
    console.error("Errore caricamento cliente:", err);
  }
}

async function salvaCliente(force = false) {
  const tipo = document.getElementById("cli-tipo").value;

  const data = {
    codice: document.getElementById("cli-codice").value.trim(),
    tipo_cliente: tipo,

    nome: document.getElementById("cli-nome").value.trim() || null,
    cognome: document.getElementById("cli-cognome").value.trim() || null,
    codice_fiscale: document.getElementById("cli-cf").value.trim().toUpperCase() || null,

    ragione_sociale: document.getElementById("cli-ragione").value.trim() || null,
    partita_iva: document.getElementById("cli-piva").value.trim() || null,
    codice_sdi: document.getElementById("cli-sdi").value.trim().toUpperCase() || null,
    pec: document.getElementById("cli-pec").value.trim() || null,
    referente_nome: document.getElementById("cli-ref-nome").value.trim() || null,
    referente_telefono: document.getElementById("cli-ref-tel").value.trim() || null,

    email: document.getElementById("cli-email").value.trim() || null,
    telefono: document.getElementById("cli-telefono").value.trim() || null,

    indirizzo: document.getElementById("cli-indirizzo").value.trim() || null,
    cap: document.getElementById("cli-cap").value.trim() || null,
    citta: document.getElementById("cli-citta").value.trim() || null,
    provincia: document.getElementById("cli-provincia").value.trim().toUpperCase() || null,

    consegna_indirizzo: document.getElementById("cli-cons-indirizzo").value.trim() || null,
    consegna_cap: document.getElementById("cli-cons-cap").value.trim() || null,
    consegna_citta: document.getElementById("cli-cons-citta").value.trim() || null,
    consegna_provincia: document.getElementById("cli-cons-provincia").value.trim().toUpperCase() || null,

    sconto_default: parseFloat(document.getElementById("cli-sconto").value) || null,
    attivo: document.getElementById("cli-attivo").checked,
    note: document.getElementById("cli-note").value || null,
  };

  const method = clienteInModifica ? "PUT" : "POST";
  const forceParam = force ? "?force=true" : "";
  const url = clienteInModifica
    ? `${API_URL}/clienti/${clienteInModifica}${forceParam}`
    : `${API_URL}/clienti/${forceParam}`;

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (res.status === 409) {
      const conflict = await res.json();
      mostraDuplicato(conflict.detail, () => salvaCliente(true));
      return;
    }

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore durante il salvataggio.");
      return;
    }

    setActiveMenu("menu-clienti");
    renderClienti();
  } catch (err) {
    console.error("Errore salvataggio cliente:", err);
    alert("Errore di connessione.");
  }
}

function eliminaCliente(id, nome) {
  mostraConferma(`Eliminare il cliente "${nome}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/clienti/${id}`, { method: "DELETE" });
      caricaClientiStats();
      caricaClienti();
    } catch (err) {
      console.error("Errore eliminazione cliente:", err);
    }
  });
}

// =============================================
// FORNITORI
// =============================================

let fornitoriLista = [];
let fornitoreInModifica = null;

const CATEGORIA_LABELS = {
  agricoltura: "Agricoltura",
  materiali: "Materiali",
  servizi: "Servizi",
  trasporti: "Trasporti",
  manutenzione: "Manutenzione",
  altro: "Altro",
};

async function renderFornitori() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-fornitori");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  caricaFornitoriStats();
  caricaFornitori();

  document.getElementById("btn-nuovo-fornitore").addEventListener("click", () => {
    fornitoreInModifica = null;
    renderFornitoreForm();
  });

  document.getElementById("btn-filtra-fornitori").addEventListener("click", () => caricaFornitori());

  document.getElementById("filtro-fornitori-q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); caricaFornitori(); }
  });

  document.getElementById("btn-export-fornitori-csv")?.addEventListener("click", () => {
    const params = new URLSearchParams();
    const q = document.getElementById("filtro-fornitori-q")?.value;
    const tipo = document.getElementById("filtro-fornitori-tipo")?.value;
    const categoria = document.getElementById("filtro-fornitori-categoria")?.value;
    const tutti = document.getElementById("filtro-fornitori-tutti")?.checked;
    if (q) params.set("q", q);
    if (tipo) params.set("tipo", tipo);
    if (categoria) params.set("categoria", categoria);
    if (tutti) params.set("tutti", "true");
    scaricaCSV("fornitori", params.toString(), "Fornitori.csv");
  });
}

async function caricaFornitoriStats() {
  try {
    const res = await apiFetch(`${API_URL}/fornitori/stats`);
    const data = await res.json();
    document.getElementById("stat-fornitori-totale").textContent = data.totale;
    document.getElementById("stat-fornitori-attivi").textContent = data.attivi;
    document.getElementById("stat-fornitori-privati").textContent = data.privati;
    document.getElementById("stat-fornitori-aziende").textContent = data.aziende;
  } catch (err) {
    console.error("Errore caricamento stats fornitori:", err);
  }
}

async function caricaFornitori(page = 1) {
  const q = document.getElementById("filtro-fornitori-q")?.value || "";
  const tipo = document.getElementById("filtro-fornitori-tipo")?.value || "";
  const categoria = document.getElementById("filtro-fornitori-categoria")?.value || "";
  const tutti = document.getElementById("filtro-fornitori-tutti")?.checked || false;

  const params = new URLSearchParams();
  params.set("tutti", tutti);
  if (q) params.set("q", q);
  if (tipo) params.set("tipo", tipo);
  if (categoria) params.set("categoria", categoria);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/fornitori/?${params}`);
    const data = await res.json();
    fornitoriLista = data.items;
    renderTabellaFornitori();
    renderPaginazione("fornitori-pagination", "fornitori-page-info", data.page, data.pages, data.total, caricaFornitori);
  } catch (err) {
    console.error("Errore caricamento fornitori:", err);
  }
}

function renderTabellaFornitori() {
  const tbody = document.getElementById("fornitori-tbody");
  if (!tbody) return;

  if (fornitoriLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">Nessun fornitore trovato</td></tr>`;
    return;
  }

  tbody.innerHTML = fornitoriLista.map(f => {
    const tipoBadge = f.tipo_fornitore === "azienda"
      ? `<span class="badge badge-tipo-azienda">Azienda</span>`
      : `<span class="badge badge-tipo-privato">Privato</span>`;
    const catLabel = f.categoria_merceologica ? (CATEGORIA_LABELS[f.categoria_merceologica] || f.categoria_merceologica) : "-";
    const statoBadge = f.attivo
      ? `<span class="badge bg-success">Attivo</span>`
      : `<span class="badge bg-secondary">Inattivo</span>`;

    return `<tr>
      <td>${f.codice}</td>
      <td>${tipoBadge}</td>
      <td>${f.denominazione || "-"}</td>
      <td>${catLabel}</td>
      <td>${f.citta || "-"}</td>
      <td>${f.telefono || "-"}</td>
      <td>${statoBadge}</td>
      <td>
        <button class="btn btn-sm btn-outline-light me-1" onclick="editFornitore(${f.id})"><i class="fa-solid fa-pen-to-square"></i></button>
        <button class="btn btn-sm btn-outline-danger" onclick="eliminaFornitore(${f.id}, '${escapeHtml(f.denominazione || f.codice)}')"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>`;
  }).join("");
}

async function editFornitore(id) {
  try {
    const res = await apiFetch(`${API_URL}/fornitori/${id}`);
    fornitoreInModifica = await res.json();
    renderFornitoreForm();
  } catch (err) {
    console.error("Errore caricamento fornitore:", err);
  }
}

function renderFornitoreForm() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-fornitore-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  const tipoSelect = document.getElementById("forn-tipo");
  tipoSelect.addEventListener("change", toggleSezioniForn);

  document.getElementById("btn-torna-fornitori").addEventListener("click", renderFornitori);
  document.getElementById("btn-annulla-fornitore").addEventListener("click", renderFornitori);
  document.getElementById("fornitore-form").addEventListener("submit", salvaFornitore);

  if (fornitoreInModifica) {
    document.getElementById("form-fornitore-titolo").textContent = "Modifica Fornitore";
    popolaFormFornitore(fornitoreInModifica);
  } else {
    // Carica prossimo codice automatico
    apiFetch(`${API_URL}/fornitori/next-codice`)
      .then(r => r.json())
      .then(d => { document.getElementById("forn-codice").value = d.codice; })
      .catch(() => {});
  }
}

function toggleSezioniForn() {
  const tipo = document.getElementById("forn-tipo").value;
  document.getElementById("forn-sezione-privato").style.display = tipo === "privato" ? "block" : "none";
  document.getElementById("forn-sezione-azienda").style.display = tipo === "azienda" ? "block" : "none";
}

function popolaFormFornitore(f) {
  document.getElementById("forn-codice").value = f.codice || "";
  document.getElementById("forn-tipo").value = f.tipo_fornitore || "";
  toggleSezioniForn();

  document.getElementById("forn-nome").value = f.nome || "";
  document.getElementById("forn-cognome").value = f.cognome || "";
  document.getElementById("forn-cf").value = f.codice_fiscale || "";

  document.getElementById("forn-ragione").value = f.ragione_sociale || "";
  document.getElementById("forn-piva").value = f.partita_iva || "";
  document.getElementById("forn-sdi").value = f.codice_sdi || "";
  document.getElementById("forn-pec").value = f.pec || "";
  document.getElementById("forn-ref-nome").value = f.referente_nome || "";
  document.getElementById("forn-ref-tel").value = f.referente_telefono || "";

  document.getElementById("forn-email").value = f.email || "";
  document.getElementById("forn-telefono").value = f.telefono || "";

  document.getElementById("forn-indirizzo").value = f.indirizzo || "";
  document.getElementById("forn-cap").value = f.cap || "";
  document.getElementById("forn-citta").value = f.citta || "";
  document.getElementById("forn-provincia").value = f.provincia || "";

  document.getElementById("forn-iban").value = f.iban || "";
  document.getElementById("forn-banca").value = f.banca || "";

  document.getElementById("forn-categoria").value = f.categoria_merceologica || "";
  document.getElementById("forn-pagamento").value = f.condizioni_pagamento || "";
  document.getElementById("forn-attivo").checked = f.attivo;
  document.getElementById("forn-note").value = f.note || "";
}

async function salvaFornitore(e, force = false) {
  if (e && e.preventDefault) e.preventDefault();

  const body = {
    codice: document.getElementById("forn-codice").value.trim() || null,
    tipo_fornitore: document.getElementById("forn-tipo").value,
    nome: document.getElementById("forn-nome").value.trim() || null,
    cognome: document.getElementById("forn-cognome").value.trim() || null,
    codice_fiscale: document.getElementById("forn-cf").value.trim() || null,
    ragione_sociale: document.getElementById("forn-ragione").value.trim() || null,
    partita_iva: document.getElementById("forn-piva").value.trim() || null,
    codice_sdi: document.getElementById("forn-sdi").value.trim() || null,
    pec: document.getElementById("forn-pec").value.trim() || null,
    referente_nome: document.getElementById("forn-ref-nome").value.trim() || null,
    referente_telefono: document.getElementById("forn-ref-tel").value.trim() || null,
    email: document.getElementById("forn-email").value.trim() || null,
    telefono: document.getElementById("forn-telefono").value.trim() || null,
    indirizzo: document.getElementById("forn-indirizzo").value.trim() || null,
    cap: document.getElementById("forn-cap").value.trim() || null,
    citta: document.getElementById("forn-citta").value.trim() || null,
    provincia: document.getElementById("forn-provincia").value.trim() || null,
    iban: document.getElementById("forn-iban").value.trim() || null,
    banca: document.getElementById("forn-banca").value.trim() || null,
    categoria_merceologica: document.getElementById("forn-categoria").value || null,
    condizioni_pagamento: document.getElementById("forn-pagamento").value || null,
    attivo: document.getElementById("forn-attivo").checked,
    note: document.getElementById("forn-note").value.trim() || null,
  };

  const isEdit = !!fornitoreInModifica;
  const forceParam = force ? "?force=true" : "";
  const url = isEdit ? `${API_URL}/fornitori/${fornitoreInModifica.id}${forceParam}` : `${API_URL}/fornitori/${forceParam}`;
  const method = isEdit ? "PUT" : "POST";

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (res.status === 409) {
      const conflict = await res.json();
      mostraDuplicato(conflict.detail, () => salvaFornitore(null, true));
      return;
    }

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore nel salvataggio.");
      return;
    }

    renderFornitori();
  } catch (err) {
    console.error("Errore salvataggio fornitore:", err);
    alert("Errore di connessione.");
  }
}

function eliminaFornitore(id, nome) {
  mostraConferma(`Eliminare il fornitore "${nome}"?`, async () => {
    try {
      await apiFetch(`${API_URL}/fornitori/${id}`, { method: "DELETE" });
      caricaFornitoriStats();
      caricaFornitori();
    } catch (err) {
      console.error("Errore eliminazione fornitore:", err);
    }
  });
}

// =============================================
// FLATPICKR — Inizializzazione globale
// =============================================

function initFlatpickr(container) {
  const els = (container || document).querySelectorAll(".flatpickr-date");
  els.forEach(el => {
    if (el._flatpickr) return;
    flatpickr(el, {
      locale: "it",
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d/m/Y",
      allowInput: true,
      theme: "dark",
    });
  });
}

// =============================================
// COSTI — Stato
// =============================================

let costiLista = [];
let costoInModifica = null;
let categorieCostoLista = [];
let catSortBy = "nome";
let catSortDir = "asc";
let catPage = 1;

const STATO_PAGAMENTO_LABELS = {
  pagato: "Pagato",
  da_pagare: "Da pagare",
  parziale: "Parziale",
};

const STATO_PAGAMENTO_BADGE = {
  pagato: "bg-success",
  da_pagare: "bg-danger",
  parziale: "bg-warning text-dark",
};

const TIPO_DOC_LABELS = {
  fattura: "Fattura",
  ricevuta: "Ricevuta",
  nota_credito: "Nota credito",
  scontrino: "Scontrino",
};

const MODALITA_PAG_LABELS = {
  bonifico: "Bonifico",
  contanti: "Contanti",
  carta: "Carta",
  assegno: "Assegno",
  riba: "Ri.Ba",
};

// =============================================
// COSTI — Lista
// =============================================

async function renderCosti() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-costi");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-nuovo-costo")?.addEventListener("click", () => renderCostoForm());
  document.getElementById("btn-gestisci-categorie")?.addEventListener("click", () => renderCategorieCosto());
  document.getElementById("btn-export-costi-csv")?.addEventListener("click", () => {
    const params = new URLSearchParams();
    const anno = document.getElementById("filtro-costi-anno")?.value;
    const tipo = document.getElementById("filtro-costi-tipo")?.value;
    const cat = document.getElementById("filtro-costi-categoria")?.value;
    const stato = document.getElementById("filtro-costi-stato")?.value;
    const forn = document.getElementById("filtro-costi-fornitore")?.value;
    if (anno) params.set("anno", anno);
    if (tipo) params.set("tipo", tipo);
    if (cat) params.set("categoria_id", cat);
    if (stato) params.set("stato", stato);
    if (forn) params.set("fornitore_id", forn);
    scaricaCSV("costi", params.toString(), "Costi.csv");
  });

  // Filtri
  document.getElementById("filtro-costi-anno")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-tipo")?.addEventListener("change", () => {
    aggiornaFiltroCategorie();
    caricaCosti();
  });
  document.getElementById("filtro-costi-categoria")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-stato")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-fornitore")?.addEventListener("change", () => caricaCosti());
  document.getElementById("search-costi")?.addEventListener("input", debounceSearch(() => caricaCosti()));

  await caricaCategorieCosto();
  await popolaFiltroCosti();
  await caricaCostiStats();
  await caricaCosti();
}

async function caricaCategorieCosto() {
  try {
    const res = await apiFetch(`${API_URL}/categorie-costo/?per_page=100`);
    const data = await res.json();
    categorieCostoLista = data.items || [];
  } catch (err) {
    console.error("Errore caricamento categorie:", err);
  }
}

async function popolaFiltroCosti() {
  // Anni
  try {
    const res = await apiFetch(`${API_URL}/costi/anni`);
    const anni = await res.json();
    const selAnno = document.getElementById("filtro-costi-anno");
    if (selAnno) {
      selAnno.innerHTML = '<option value="">Tutti gli anni</option>';
      anni.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = a;
        selAnno.appendChild(opt);
      });
    }
  } catch (err) { /* ignore */ }

  // Categorie
  aggiornaFiltroCategorie();

  // Fornitori
  try {
    const res = await apiFetch(`${API_URL}/fornitori/?tutti=false&per_page=100`);
    const fornitori = (await res.json()).items;
    const selForn = document.getElementById("filtro-costi-fornitore");
    if (selForn) {
      selForn.innerHTML = '<option value="">Tutti i fornitori</option>';
      fornitori.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = f.denominazione || f.codice;
        selForn.appendChild(opt);
      });
    }
  } catch (err) { /* ignore */ }
}

function aggiornaFiltroCategorie() {
  const tipoFiltro = document.getElementById("filtro-costi-tipo")?.value || "";
  const selCat = document.getElementById("filtro-costi-categoria");
  if (!selCat) return;
  selCat.innerHTML = '<option value="">Tutte le categorie</option>';
  const filtered = tipoFiltro ? categorieCostoLista.filter(c => c.tipo_costo === tipoFiltro) : categorieCostoLista;
  filtered.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.nome;
    selCat.appendChild(opt);
  });
}

async function caricaCostiStats() {
  try {
    const anno = document.getElementById("filtro-costi-anno")?.value || "";
    const url = anno ? `${API_URL}/costi/stats?anno=${anno}` : `${API_URL}/costi/stats`;
    const res = await apiFetch(url);
    const s = await res.json();

    const fmt = (v) => "\u20AC " + Number(v).toLocaleString("it-IT", {minimumFractionDigits:2});

    document.getElementById("stat-costi-count").textContent = s.totale_count;
    document.getElementById("stat-costi-totale").textContent = fmt(s.totale_importo);
    document.getElementById("stat-costi-pagati").textContent = fmt(s.totale_pagati);
    document.getElementById("stat-costi-da-pagare").textContent = fmt(s.totale_da_pagare);
    document.getElementById("stat-costi-campagna").textContent = fmt(s.totale_campagna);
    document.getElementById("stat-costi-strutturale").textContent = fmt(s.totale_strutturale);
  } catch (err) {
    console.error("Errore stats costi:", err);
  }
}

async function caricaCosti(page = 1) {
  try {
    const params = new URLSearchParams();
    const anno = document.getElementById("filtro-costi-anno")?.value;
    const tipo = document.getElementById("filtro-costi-tipo")?.value;
    const cat = document.getElementById("filtro-costi-categoria")?.value;
    const stato = document.getElementById("filtro-costi-stato")?.value;
    const forn = document.getElementById("filtro-costi-fornitore")?.value;

    const search = document.getElementById("search-costi")?.value?.trim() || "";
    if (anno) params.set("anno", anno);
    if (tipo) params.set("tipo", tipo);
    if (cat) params.set("categoria_id", cat);
    if (stato) params.set("stato", stato);
    if (forn) params.set("fornitore_id", forn);
    if (search) params.set("search", search);
    params.set("page", page);
    params.set("per_page", 10);

    const res = await apiFetch(`${API_URL}/costi/?${params.toString()}`);
    const data = await res.json();
    costiLista = data.items;
    renderTabellaCosti();
    renderPaginazione("costi-pagination", "costi-page-info", data.page, data.pages, data.total, caricaCosti);
  } catch (err) {
    console.error("Errore caricamento costi:", err);
  }
}

function renderTabellaCosti() {
  const tbody = document.getElementById("costi-tbody");
  if (!tbody) return;

  if (costiLista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Nessun costo trovato</td></tr>';
    return;
  }

  tbody.innerHTML = costiLista.map(c => `
    <tr>
      <td><code>${c.codice || "—"}</code></td>
      <td>${c.data_fattura || "—"}</td>
      <td>
        <span class="badge ${c.categoria_tipo === "campagna" ? "bg-info text-dark" : "bg-secondary"}">${c.categoria_tipo || ""}</span>
        ${c.categoria_nome || "—"}
      </td>
      <td>${c.descrizione || "—"} ${c.documento ? '<i class="fa-solid fa-paperclip text-secondary ms-1" title="Documento allegato"></i>' : ""}</td>
      <td>${c.fornitore_denominazione || "—"}</td>
      <td class="text-end fw-bold">&euro; ${Number(c.importo_totale).toLocaleString("it-IT", {minimumFractionDigits:2})}</td>
      <td class="text-center">
        <span class="badge ${STATO_PAGAMENTO_BADGE[c.stato_pagamento] || "bg-secondary"}">
          ${STATO_PAGAMENTO_LABELS[c.stato_pagamento] || c.stato_pagamento}
        </span>
      </td>
      <td class="text-center">
        <button class="btn-action btn-action-edit" onclick="editCosto(${c.id})" title="Modifica">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

async function editCosto(id) {
  try {
    const res = await apiFetch(`${API_URL}/costi/${id}`);
    costoInModifica = await res.json();
    renderCostoForm();
  } catch (err) {
    console.error("Errore caricamento costo:", err);
  }
}

// =============================================
// COSTI — Form
// =============================================

function _mostraCostoDocPreview(tipo, url, filename) {
  // Aggiorna info file
  const icon = document.getElementById("costo-doc-icon");
  const fnEl = document.getElementById("costo-doc-filename");
  const hint = document.getElementById("costo-doc-hint");
  if (tipo === "pdf") {
    icon.className = "fa-solid fa-file-pdf fa-2x";
    icon.style.color = "#e74c3c";
  } else {
    icon.className = "fa-solid fa-file-image fa-2x";
    icon.style.color = "#3498db";
  }
  fnEl.textContent = filename || "Documento";
  hint.textContent = "File caricato";

  // Mostra viewer, nascondi placeholder
  document.getElementById("costo-doc-viewer").style.display = "";
  document.getElementById("costo-doc-placeholder").style.display = "none";

  const iframe = document.getElementById("costo-doc-iframe");
  const img = document.getElementById("costo-doc-img");
  if (tipo === "pdf") {
    iframe.src = url;
    iframe.style.display = "";
    img.style.display = "none";
  } else {
    img.src = url;
    img.style.display = "";
    iframe.style.display = "none";
  }

  // Mostra pulsanti
  const btnApri = document.getElementById("btn-apri-doc");
  btnApri.href = url;
  btnApri.style.display = "";
  document.getElementById("btn-rimuovi-doc").style.display = "";

  // Badge verde nel tab
  document.getElementById("costo-doc-badge").style.display = "";
}

function _resetCostoDocViewer() {
  document.getElementById("costo-doc-icon").className = "fa-solid fa-file-circle-plus fa-2x text-secondary";
  document.getElementById("costo-doc-icon").style.color = "";
  document.getElementById("costo-doc-filename").textContent = "Nessun documento allegato";
  document.getElementById("costo-doc-hint").textContent = "Carica un file JPG, PNG o PDF";
  document.getElementById("costo-doc-viewer").style.display = "none";
  document.getElementById("costo-doc-placeholder").style.display = "";
  document.getElementById("costo-doc-iframe").src = "";
  document.getElementById("costo-doc-iframe").style.display = "none";
  document.getElementById("costo-doc-img").src = "";
  document.getElementById("costo-doc-img").style.display = "none";
  document.getElementById("btn-apri-doc").style.display = "none";
  document.getElementById("btn-rimuovi-doc").style.display = "none";
  document.getElementById("costo-doc-badge").style.display = "none";
}

async function renderCostoForm() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-costo-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-torna-costi")?.addEventListener("click", () => {
    costoInModifica = null;
    renderCosti();
  });

  // Radio tipo -> filtra categorie + mostra/nascondi ammortamento
  document.querySelectorAll('input[name="costo-tipo"]').forEach(r => {
    r.addEventListener("change", () => {
      aggiornaSelectCategorieCosto();
      toggleAmmortamento();
    });
  });

  // Calcolo IVA
  document.getElementById("costo-imponibile")?.addEventListener("input", calcolaImportiCosto);
  document.getElementById("costo-iva")?.addEventListener("change", calcolaImportiCosto);

  // Calcolo quota ammortamento
  document.getElementById("costo-anni-ammortamento")?.addEventListener("change", calcolaQuotaAmmortamento);

  // Form submit
  document.getElementById("form-costo")?.addEventListener("submit", salvaCosto);

  // Carica categorie e fornitori per i dropdown
  await caricaCategorieCosto();
  await popolaSelectFornitoriCosto();

  // Anno default
  if (!costoInModifica) {
    document.getElementById("costo-anno").value = new Date().getFullYear();
  }

  aggiornaSelectCategorieCosto();

  // Init flatpickr sui campi data (PRIMA di popolare il form)
  initFlatpickr();

  // Popola form se modifica
  if (costoInModifica) {
    popolaFormCosto(costoInModifica);
  }

  // Tab switch: Dati Fattura <-> Documento
  document.getElementById("costo-tab-dati")?.addEventListener("click", () => {
    document.getElementById("costo-tab-dati").classList.add("active");
    document.getElementById("costo-tab-doc").classList.remove("active");
    document.getElementById("costo-content-dati").style.display = "";
    document.getElementById("costo-content-doc").style.display = "none";
  });
  document.getElementById("costo-tab-doc")?.addEventListener("click", () => {
    document.getElementById("costo-tab-doc").classList.add("active");
    document.getElementById("costo-tab-dati").classList.remove("active");
    document.getElementById("costo-content-doc").style.display = "";
    document.getElementById("costo-content-dati").style.display = "none";
  });

  // Preview documento su selezione file
  document.getElementById("costo-doc-input")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    _mostraCostoDocPreview(file.type === "application/pdf" ? "pdf" : "image", URL.createObjectURL(file), file.name);
  });

  // Rimuovi documento allegato
  document.getElementById("btn-rimuovi-doc")?.addEventListener("click", async () => {
    const costoId = document.getElementById("costo-id")?.value;
    if (!costoId) return;
    try {
      const res = await apiFetch(`${API_URL}/costi/${costoId}/documento`, { method: "DELETE" });
      if (res.ok) {
        _resetCostoDocViewer();
        document.getElementById("costo-doc-input").value = "";
      }
    } catch (err) {
      console.error("Errore rimozione documento:", err);
    }
  });

  // Auto-codice
  aggiornaCodiciCosto();
  document.getElementById("costo-anno")?.addEventListener("change", aggiornaCodiciCosto);
}

function aggiornaSelectCategorieCosto() {
  const tipo = document.querySelector('input[name="costo-tipo"]:checked')?.value || "campagna";
  const sel = document.getElementById("costo-categoria");
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = "";
  const filtered = categorieCostoLista.filter(c => c.tipo_costo === tipo && c.attiva !== false);
  filtered.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.nome;
    sel.appendChild(opt);
  });
  // Ripristina selezione se possibile
  if (currentVal && [...sel.options].some(o => o.value === currentVal)) {
    sel.value = currentVal;
  }
}

function toggleAmmortamento() {
  const tipo = document.querySelector('input[name="costo-tipo"]:checked')?.value;
  const section = document.getElementById("costo-ammortamento-section");
  if (section) {
    section.style.display = tipo === "strutturale" ? "block" : "none";
  }
  if (tipo !== "strutturale") {
    const sel = document.getElementById("costo-anni-ammortamento");
    if (sel) sel.value = "0";
    const quota = document.getElementById("costo-quota-annua");
    if (quota) quota.value = "";
  }
}

async function popolaSelectFornitoriCosto() {
  try {
    const res = await apiFetch(`${API_URL}/fornitori/?tutti=false&per_page=100`);
    const fornitori = (await res.json()).items;
    const sel = document.getElementById("costo-fornitore");
    if (!sel) return;
    sel.innerHTML = '<option value="">\u2014 Nessuno \u2014</option>';
    fornitori.forEach(f => {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = f.denominazione || f.codice;
      sel.appendChild(opt);
    });
  } catch (err) { /* ignore */ }
}

function calcolaImportiCosto() {
  const imponibile = parseFloat(document.getElementById("costo-imponibile")?.value) || 0;
  const ivaPct = parseFloat(document.getElementById("costo-iva")?.value) || 0;
  const importoIva = Math.round(imponibile * ivaPct / 100 * 100) / 100;
  const totale = Math.round((imponibile + importoIva) * 100) / 100;

  document.getElementById("costo-importo-iva").value = importoIva.toFixed(2);
  document.getElementById("costo-importo-totale").value = totale.toFixed(2);

  calcolaQuotaAmmortamento();
}

function calcolaQuotaAmmortamento() {
  const anni = parseInt(document.getElementById("costo-anni-ammortamento")?.value) || 0;
  const totale = parseFloat(document.getElementById("costo-importo-totale")?.value) || 0;
  const quota = anni > 0 ? (totale / anni).toFixed(2) : "";
  document.getElementById("costo-quota-annua").value = quota;
}

async function aggiornaCodiciCosto() {
  const anno = document.getElementById("costo-anno")?.value;
  if (!anno || costoInModifica) return;
  try {
    const res = await apiFetch(`${API_URL}/costi/next-codice?anno=${anno}`);
    const data = await res.json();
    document.getElementById("costo-codice").value = data.codice;
  } catch (err) { /* ignore */ }
}

function popolaFormCosto(c) {
  document.getElementById("costo-form-title").textContent = "Modifica Costo";
  document.getElementById("costo-id").value = c.id;
  document.getElementById("costo-codice").value = c.codice || "";
  document.getElementById("costo-anno").value = c.anno_campagna;
  document.getElementById("costo-descrizione").value = c.descrizione || "";

  // Tipo radio
  if (c.categoria_tipo === "strutturale") {
    document.getElementById("costo-tipo-strutturale").checked = true;
  } else {
    document.getElementById("costo-tipo-campagna").checked = true;
  }
  aggiornaSelectCategorieCosto();
  document.getElementById("costo-categoria").value = c.categoria_id;
  toggleAmmortamento();

  // Fornitore
  if (c.fornitore_id) {
    document.getElementById("costo-fornitore").value = c.fornitore_id;
  }

  // Fattura
  document.getElementById("costo-data-fattura")._flatpickr?.setDate(c.data_fattura);
  document.getElementById("costo-numero-fattura").value = c.numero_fattura || "";
  document.getElementById("costo-tipo-documento").value = c.tipo_documento || "fattura";

  // Importi
  document.getElementById("costo-imponibile").value = c.imponibile;
  document.getElementById("costo-iva").value = c.iva_percentuale;
  calcolaImportiCosto();

  // Pagamento
  document.getElementById("costo-stato-pagamento").value = c.stato_pagamento || "da_pagare";
  if (c.data_pagamento) {
    document.getElementById("costo-data-pagamento")._flatpickr?.setDate(c.data_pagamento);
  }
  document.getElementById("costo-modalita-pagamento").value = c.modalita_pagamento || "";
  document.getElementById("costo-riferimento-pagamento").value = c.riferimento_pagamento || "";

  // Ammortamento
  document.getElementById("costo-anni-ammortamento").value = c.anni_ammortamento || 0;
  calcolaQuotaAmmortamento();

  // Note
  document.getElementById("costo-note").value = c.note || "";

  // Documento allegato
  if (c.documento) {
    const isImage = /\.(jpe?g|png|webp)$/i.test(c.documento);
    const url = `/uploads/${c.documento}`;
    const filename = c.documento.split("/").pop();
    _mostraCostoDocPreview(isImage ? "image" : "pdf", url, filename);
  }

  // Bottone elimina
  document.getElementById("btn-elimina-costo").style.display = "inline-block";
  document.getElementById("btn-elimina-costo").addEventListener("click", () => eliminaCosto(c.id));
}

async function salvaCosto(e) {
  e.preventDefault();

  const id = document.getElementById("costo-id")?.value;
  const tipo = document.querySelector('input[name="costo-tipo"]:checked')?.value;

  const payload = {
    categoria_id: parseInt(document.getElementById("costo-categoria").value),
    anno_campagna: parseInt(document.getElementById("costo-anno").value),
    descrizione: document.getElementById("costo-descrizione").value.trim(),
    fornitore_id: document.getElementById("costo-fornitore").value ? parseInt(document.getElementById("costo-fornitore").value) : null,
    data_fattura: document.getElementById("costo-data-fattura").value,
    numero_fattura: document.getElementById("costo-numero-fattura").value.trim() || null,
    tipo_documento: document.getElementById("costo-tipo-documento").value,
    imponibile: parseFloat(document.getElementById("costo-imponibile").value),
    iva_percentuale: parseFloat(document.getElementById("costo-iva").value),
    stato_pagamento: document.getElementById("costo-stato-pagamento").value,
    data_pagamento: document.getElementById("costo-data-pagamento").value || null,
    modalita_pagamento: document.getElementById("costo-modalita-pagamento").value || null,
    riferimento_pagamento: document.getElementById("costo-riferimento-pagamento").value.trim() || null,
    anni_ammortamento: tipo === "strutturale" ? parseInt(document.getElementById("costo-anni-ammortamento").value) : 0,
    note: document.getElementById("costo-note").value.trim() || null,
  };

  try {
    const method = id ? "PUT" : "POST";
    const url = id ? `${API_URL}/costi/${id}` : `${API_URL}/costi/`;
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore nel salvataggio.");
      return;
    }

    const saved = await res.json();

    // Upload documento se selezionato
    const docInput = document.getElementById("costo-doc-input");
    if (docInput?.files.length > 0) {
      const formData = new FormData();
      formData.append("file", docInput.files[0]);
      await apiFetch(`${API_URL}/costi/${saved.id}/documento`, {
        method: "POST",
        body: formData,
      });
    }

    costoInModifica = null;
    renderCosti();
  } catch (err) {
    console.error("Errore salvataggio costo:", err);
    alert("Errore di rete.");
  }
}

function eliminaCosto(id) {
  mostraConferma("Eliminare questo costo?", async () => {
    try {
      await apiFetch(`${API_URL}/costi/${id}`, { method: "DELETE" });
      costoInModifica = null;
      renderCosti();
    } catch (err) {
      console.error("Errore eliminazione costo:", err);
    }
  });
}

// =============================================
// CATEGORIE COSTO — Gestione
// =============================================

async function renderCategorieCosto() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-categorie-costo");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-torna-costi-da-cat")?.addEventListener("click", () => renderCosti());
  document.getElementById("btn-annulla-cat")?.addEventListener("click", () => resetFormCategoria());
  document.getElementById("form-categoria")?.addEventListener("submit", salvaCategoria);

  document.getElementById("search-categorie")?.addEventListener("input", debounceSearch(() => {
    catPage = 1;
    caricaCategorieCostoTabella();
  }));

  // Sortable column headers
  document.querySelectorAll(".sortable-th").forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.sort;
      if (catSortBy === col) {
        catSortDir = catSortDir === "asc" ? "desc" : "asc";
      } else {
        catSortBy = col;
        catSortDir = "asc";
      }
      catPage = 1;
      caricaCategorieCostoTabella();
    });
  });

  catPage = 1;
  catSortBy = "nome";
  catSortDir = "asc";
  await caricaCategorieCosto();
  await caricaCategorieCostoTabella();
}

function mostraFormCategoria(cat) {
  const titolo = document.getElementById("cat-form-titolo");
  if (cat) {
    titolo.innerHTML = '<i class="fa-solid fa-pen-to-square me-2"></i>Modifica Categoria';
    document.getElementById("cat-id").value = cat.id;
    document.getElementById("cat-codice").value = cat.codice;
    document.getElementById("cat-nome").value = cat.nome;
    document.getElementById("cat-tipo").value = cat.tipo_costo;
  } else {
    resetFormCategoria();
  }
}

function resetFormCategoria() {
  const titolo = document.getElementById("cat-form-titolo");
  if (titolo) titolo.innerHTML = '<i class="fa-solid fa-plus me-2"></i>Nuova Categoria';
  document.getElementById("cat-id").value = "";
  document.getElementById("cat-codice").value = "";
  document.getElementById("cat-nome").value = "";
  document.getElementById("cat-tipo").value = "campagna";
}

async function caricaCategorieCostoTabella(page) {
  if (page) catPage = page;
  const search = document.getElementById("search-categorie")?.value || "";
  const params = new URLSearchParams({
    page: catPage,
    per_page: 13,
    sort_by: catSortBy,
    sort_dir: catSortDir,
  });
  if (search) params.set("search", search);

  try {
    const res = await apiFetch(`${API_URL}/categorie-costo/?${params}`);
    const data = await res.json();
    renderTabellaCategorie(data.items || []);
    renderPaginazione("categorie-pagination", "categorie-page-info", data.page, data.pages, data.total, caricaCategorieCostoTabella);
    aggiornaSortIcons();
  } catch (err) {
    console.error("Errore caricamento tabella categorie:", err);
  }
}

function aggiornaSortIcons() {
  document.querySelectorAll(".sortable-th").forEach(th => {
    const icon = th.querySelector(".sort-icon");
    if (!icon) return;
    const col = th.dataset.sort;
    if (col === catSortBy) {
      icon.className = `fa-solid fa-sort-${catSortDir === "asc" ? "up" : "down"} sort-icon active`;
    } else {
      icon.className = "fa-solid fa-sort sort-icon";
    }
  });
}

function renderTabellaCategorie(items) {
  const tbody = document.getElementById("categorie-tbody");
  if (!tbody) return;

  tbody.innerHTML = items.map(c => `
    <tr>
      <td><code>${c.codice}</code></td>
      <td>${c.nome}</td>
      <td><span class="badge ${c.tipo_costo === "campagna" ? "bg-info text-dark" : "bg-secondary"}">${c.tipo_costo}</span></td>
      <td class="text-center">
        <span class="badge ${c.attiva ? "bg-success" : "bg-danger"}">${c.attiva ? "Si" : "No"}</span>
      </td>
      <td class="text-center">
        <button class="btn btn-sm btn-outline-light me-1" onclick="editCategoriaCosto(${c.id})">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="btn btn-sm ${c.attiva ? "btn-outline-warning" : "btn-outline-success"}" onclick="toggleCategoriaCosto(${c.id}, ${!c.attiva})">
          <i class="fa-solid ${c.attiva ? "fa-eye-slash" : "fa-eye"}"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="eliminaCategoriaCosto(${c.id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

async function editCategoriaCosto(id) {
  let cat = categorieCostoLista.find(c => c.id === id);
  if (!cat) {
    try {
      const res = await apiFetch(`${API_URL}/categorie-costo/${id}`);
      if (res.ok) cat = await res.json();
    } catch (err) {
      console.error("Errore caricamento categoria:", err);
    }
  }
  if (cat) mostraFormCategoria(cat);
}

async function toggleCategoriaCosto(id, nuovoStato) {
  try {
    await apiFetch(`${API_URL}/categorie-costo/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attiva: nuovoStato }),
    });
    await caricaCategorieCosto();
    await caricaCategorieCostoTabella();
  } catch (err) {
    console.error("Errore toggle categoria:", err);
  }
}

async function eliminaCategoriaCosto(id) {
  mostraConferma("Eliminare questa categoria?", async () => {
    try {
      const res = await apiFetch(`${API_URL}/categorie-costo/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore eliminazione.");
        return;
      }
      await caricaCategorieCosto();
      await caricaCategorieCostoTabella();
    } catch (err) {
      console.error("Errore eliminazione categoria:", err);
    }
  });
}

async function salvaCategoria(e) {
  e.preventDefault();
  const id = document.getElementById("cat-id")?.value;
  const payload = {
    codice: document.getElementById("cat-codice").value.trim().toUpperCase(),
    nome: document.getElementById("cat-nome").value.trim(),
    tipo_costo: document.getElementById("cat-tipo").value,
  };

  try {
    const method = id ? "PUT" : "POST";
    const url = id ? `${API_URL}/categorie-costo/${id}` : `${API_URL}/categorie-costo/`;
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore salvataggio.");
      return;
    }

    resetFormCategoria();
    await caricaCategorieCosto();
    await caricaCategorieCostoTabella();
  } catch (err) {
    console.error("Errore salvataggio categoria:", err);
  }
}

// =============================================
// MAGAZZINO — Stato
// =============================================

let movimentiLista = [];
let movimentoInModifica = null;
let giacenzeLista = [];
let magazzinoTabAttiva = "giacenze";

const TIPO_MOV_LABELS = {
  carico: "Carico",
  scarico: "Scarico",
};
const TIPO_MOV_BADGE = {
  carico: "bg-success",
  scarico: "bg-danger",
};
const CAUSALE_MOV_LABELS = {
  produzione: "Produzione",
  omaggio: "Omaggio / Degustazione",
  pubblicita: "Pubblicita'",
  scarto: "Scarto / Rottura",
  vendita: "Vendita",
};


// =============================================
// MAGAZZINO — Lista
// =============================================

async function renderMagazzino() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-magazzino");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  // Tab switching
  document.getElementById("mag-tab-giacenze")?.addEventListener("click", () => {
    magazzinoTabAttiva = "giacenze";
    aggiornaTabMagazzino();
  });
  document.getElementById("mag-tab-movimenti")?.addEventListener("click", () => {
    magazzinoTabAttiva = "movimenti";
    aggiornaTabMagazzino();
  });

  // Filtri
  document.getElementById("filtro-mag-anno")?.addEventListener("change", () => {
    caricaMagStats();
    if (magazzinoTabAttiva === "giacenze") caricaGiacenze();
    else caricaMovimenti();
  });
  document.getElementById("filtro-mag-tipo")?.addEventListener("change", () => caricaMovimenti());
  document.getElementById("filtro-mag-causale")?.addEventListener("change", () => caricaMovimenti());
  document.getElementById("search-movimenti")?.addEventListener("input", debounceSearch(() => caricaMovimenti()));

  // Bottoni
  document.getElementById("btn-nuovo-carico")?.addEventListener("click", () => renderMovimentoForm(null, "carico"));
  document.getElementById("btn-nuovo-scarico")?.addEventListener("click", () => renderMovimentoForm(null, "scarico"));
  document.getElementById("btn-sincronizza-mag")?.addEventListener("click", sincronizzaMagazzino);
  document.getElementById("btn-export-movimenti-csv")?.addEventListener("click", () => {
    const params = new URLSearchParams();
    const anno = document.getElementById("filtro-mag-anno")?.value;
    const tipo = document.getElementById("filtro-mag-tipo")?.value;
    const causale = document.getElementById("filtro-mag-causale")?.value;
    if (anno) params.set("anno", anno);
    if (tipo) params.set("tipo", tipo);
    if (causale) params.set("causale", causale);
    scaricaCSV("magazzino", params.toString(), "Movimenti.csv");
  });

  // Popola filtro anni
  try {
    const res = await apiFetch(`${API_URL}/magazzino/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-mag-anno");
    if (sel) {
      sel.innerHTML = '<option value="">Tutti gli anni</option>';
      anni.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.textContent = a;
        sel.appendChild(opt);
      });
    }
  } catch (e) { /* nessun anno ancora */ }

  caricaMagStats();
  aggiornaTabMagazzino();
}

function aggiornaTabMagazzino() {
  const tabG = document.getElementById("mag-tab-giacenze");
  const tabM = document.getElementById("mag-tab-movimenti");
  const contentG = document.getElementById("mag-content-giacenze");
  const contentM = document.getElementById("mag-content-movimenti");
  const filtroTipo = document.getElementById("filtro-mag-tipo-wrap");
  const filtroCausale = document.getElementById("filtro-mag-causale-wrap");

  if (magazzinoTabAttiva === "giacenze") {
    tabG?.classList.add("active");
    tabM?.classList.remove("active");
    if (contentG) contentG.style.display = "";
    if (contentM) contentM.style.display = "none";
    if (filtroTipo) filtroTipo.style.display = "none";
    if (filtroCausale) filtroCausale.style.display = "none";
    caricaGiacenze();
  } else {
    tabG?.classList.remove("active");
    tabM?.classList.add("active");
    if (contentG) contentG.style.display = "none";
    if (contentM) contentM.style.display = "";
    if (filtroTipo) filtroTipo.style.display = "";
    if (filtroCausale) filtroCausale.style.display = "";
    caricaMovimenti();
  }
}

async function caricaMagStats() {
  try {
    const anno = document.getElementById("filtro-mag-anno")?.value || "";
    const qs = anno ? `?anno=${anno}` : "";
    const [resStats, resGiac] = await Promise.all([
      apiFetch(`${API_URL}/magazzino/stats${qs}`),
      apiFetch(`${API_URL}/magazzino/giacenze${qs}`),
    ]);
    const s = await resStats.json();
    const giacenze = await resGiac.json();
    document.getElementById("stat-mag-movimenti").textContent = s.totale_movimenti || 0;
    document.getElementById("stat-mag-carichi").textContent = s.totale_carichi || 0;
    document.getElementById("stat-mag-scarichi").textContent = s.totale_scarichi || 0;
    document.getElementById("stat-mag-giacenza").textContent = s.giacenza_totale_unita || 0;
    // Calcola litri totali in giacenza
    const litriTotali = giacenze.reduce((sum, g) => sum + (g.giacenza_litri || 0), 0);
    document.getElementById("stat-mag-giacenza-litri").textContent = `${litriTotali.toFixed(1)} L`;
  } catch (e) {
    console.error("Errore caricamento stats magazzino", e);
  }
}


// =============================================
// MAGAZZINO — Giacenze
// =============================================

async function caricaGiacenze() {
  try {
    const anno = document.getElementById("filtro-mag-anno")?.value || "";
    const qs = anno ? `?anno=${anno}` : "";
    const res = await apiFetch(`${API_URL}/magazzino/giacenze${qs}`);
    giacenzeLista = await res.json();
    renderTabellaGiacenze();
  } catch (e) {
    console.error("Errore caricamento giacenze", e);
  }
}

function renderTabellaGiacenze() {
  const tbody = document.getElementById("giacenze-tbody");
  if (!tbody) return;

  if (giacenzeLista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-4">Nessuna giacenza registrata</td></tr>';
    return;
  }

  tbody.innerHTML = giacenzeLista.map(g => {
    const cls = g.giacenza_unita > 0 ? "text-success" : (g.giacenza_unita === 0 ? "text-secondary" : "text-danger");
    return `<tr>
      <td>${g.confezionamento_codice || ""}</td>
      <td>${g.contenitore_descrizione || "—"}</td>
      <td class="text-end">${g.capacita_litri} L</td>
      <td class="text-end text-success">${g.totale_carichi}</td>
      <td class="text-end text-danger">${g.totale_scarichi}</td>
      <td class="text-end fw-bold ${cls}">${g.giacenza_unita}</td>
      <td class="text-end">${g.giacenza_litri} L</td>
    </tr>`;
  }).join("");
}


// =============================================
// MAGAZZINO — Movimenti
// =============================================

async function caricaMovimenti(page = 1) {
  try {
    const anno = document.getElementById("filtro-mag-anno")?.value || "";
    const tipo = document.getElementById("filtro-mag-tipo")?.value || "";
    const causale = document.getElementById("filtro-mag-causale")?.value || "";
    const search = document.getElementById("search-movimenti")?.value?.trim() || "";

    const params = new URLSearchParams();
    if (anno) params.set("anno", anno);
    if (tipo) params.set("tipo", tipo);
    if (causale) params.set("causale", causale);
    if (search) params.set("search", search);
    params.set("page", page);
    params.set("per_page", 10);

    const res = await apiFetch(`${API_URL}/magazzino/?${params}`);
    const data = await res.json();
    movimentiLista = data.items;
    renderTabellaMovimenti();
    renderPaginazione("movimenti-pagination", "movimenti-page-info", data.page, data.pages, data.total, caricaMovimenti);
  } catch (e) {
    console.error("Errore caricamento movimenti", e);
  }
}

function renderTabellaMovimenti() {
  const tbody = document.getElementById("movimenti-tbody");
  if (!tbody) return;

  if (movimentiLista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4">Nessun movimento registrato</td></tr>';
    return;
  }

  tbody.innerHTML = movimentiLista.map(m => {
    const badgeCls = TIPO_MOV_BADGE[m.tipo_movimento] || "bg-secondary";
    const tipoLabel = TIPO_MOV_LABELS[m.tipo_movimento] || m.tipo_movimento;
    const causaleLabel = CAUSALE_MOV_LABELS[m.causale] || m.causale;
    const isVendita = m.causale === "vendita";
    const clienteNote = m.cliente_denominazione || m.note || "—";

    return `<tr>
      <td>${m.codice}</td>
      <td>${m.data_movimento || ""}</td>
      <td class="text-center"><span class="badge ${badgeCls}">${tipoLabel}</span></td>
      <td>${causaleLabel}</td>
      <td>${m.confezionamento_codice || ""} <span class="text-secondary small">${m.confezionamento_formato || ""}</span></td>
      <td class="text-end fw-bold">${m.quantita}</td>
      <td class="small">${clienteNote}</td>
      <td class="text-center">
        ${isVendita ? '<span class="text-secondary small">da vendita</span>' : `
          <button class="btn btn-sm btn-outline-light me-1" onclick="editMovimento(${m.id})">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger" onclick="eliminaMovimento(${m.id}, '${escapeHtml(m.codice)}')">
            <i class="fa-solid fa-trash"></i>
          </button>
        `}
      </td>
    </tr>`;
  }).join("");
}


// =============================================
// MAGAZZINO — Form Movimento
// =============================================

async function renderMovimentoForm(id, tipoDefault) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-magazzino-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  // Bottone indietro
  document.getElementById("btn-torna-magazzino")?.addEventListener("click", renderMagazzino);

  // Init flatpickr
  initFlatpickr(main);

  // Popola select confezionamenti
  await popolaSelectConfezionamenti();

  // Popola select clienti
  await popolaSelectClientiMov();

  // Anno default
  const annoEl = document.getElementById("mov-anno");
  if (annoEl && !id) annoEl.value = new Date().getFullYear();

  // Tipo default
  const tipoEl = document.getElementById("mov-tipo");
  if (tipoEl && tipoDefault && !id) {
    tipoEl.value = tipoDefault;
    aggiornaCausaliPerTipo(tipoDefault);
  }

  // Aggiorna causali quando cambia tipo
  tipoEl?.addEventListener("change", () => aggiornaCausaliPerTipo(tipoEl.value));

  // Mostra giacenza quando cambia confezionamento
  document.getElementById("mov-confezionamento")?.addEventListener("change", aggiornaGiacenzaInfo);

  // Aggiorna codice quando cambia anno
  annoEl?.addEventListener("change", async () => {
    if (!id) await aggiornaCodiceMovimento(annoEl.value);
  });

  // Auto-genera codice
  if (!id && annoEl?.value) {
    await aggiornaCodiceMovimento(annoEl.value);
  }

  // Se modifica, popola
  if (id) {
    movimentoInModifica = id;
    document.getElementById("mag-form-title").textContent = "Modifica Movimento";
    document.getElementById("btn-elimina-movimento").style.display = "";
    document.getElementById("btn-elimina-movimento").addEventListener("click", () => eliminaMovimento(id));
    await popolaFormMovimento(id);
  } else {
    movimentoInModifica = null;
  }

  // Submit
  document.getElementById("form-movimento")?.addEventListener("submit", salvaMovimento);
}

function aggiornaCausaliPerTipo(tipo) {
  const causaleEl = document.getElementById("mov-causale");
  if (!causaleEl) return;

  causaleEl.innerHTML = "";

  if (tipo === "carico") {
    causaleEl.innerHTML = '<option value="produzione">Produzione</option>';
  } else {
    causaleEl.innerHTML = `
      <option value="omaggio">Omaggio / Degustazione</option>
      <option value="pubblicita">Pubblicita</option>
      <option value="scarto">Scarto / Rottura</option>
    `;
  }
}

async function aggiornaCodiceMovimento(anno) {
  try {
    const res = await apiFetch(`${API_URL}/magazzino/next-codice?anno=${anno}`);
    const data = await res.json();
    const el = document.getElementById("mov-codice");
    if (el) el.value = data.codice;
  } catch (e) {
    console.error("Errore generazione codice movimento", e);
  }
}

async function popolaSelectConfezionamenti() {
  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/?per_page=100`);
    const lista = (await res.json()).items;
    const sel = document.getElementById("mov-confezionamento");
    if (!sel) return;
    sel.innerHTML = '<option value="">\u2014 Seleziona confezionamento \u2014</option>';
    lista.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.codice} — ${c.formato} (${c.num_unita} x ${c.capacita_litri}L)`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error("Errore caricamento confezionamenti", e);
  }
}

async function popolaSelectClientiMov() {
  try {
    const res = await apiFetch(`${API_URL}/clienti/?per_page=100`);
    const lista = (await res.json()).items;
    const sel = document.getElementById("mov-cliente");
    if (!sel) return;
    sel.innerHTML = '<option value="">\u2014 Nessun cliente \u2014</option>';
    lista.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      const nome = c.tipo_cliente === "azienda"
        ? (c.ragione_sociale || "")
        : `${c.nome || ""} ${c.cognome || ""}`.trim();
      opt.textContent = `${c.codice} — ${nome}`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error("Errore caricamento clienti", e);
  }
}

async function aggiornaGiacenzaInfo() {
  const confId = document.getElementById("mov-confezionamento")?.value;
  const infoEl = document.getElementById("mov-giacenza-info");
  if (!confId || !infoEl) {
    if (infoEl) infoEl.textContent = "";
    return;
  }
  try {
    const res = await apiFetch(`${API_URL}/magazzino/giacenze`);
    const giacenze = await res.json();
    const g = giacenze.find(x => x.confezionamento_id === parseInt(confId));
    if (g) {
      infoEl.innerHTML = `Giacenza attuale: <strong class="text-info">${g.giacenza_unita} unita</strong> (${g.giacenza_litri} L)`;
    } else {
      infoEl.textContent = "Giacenza: 0 unita (nessun movimento registrato)";
    }
  } catch (e) {
    infoEl.textContent = "";
  }
}

async function popolaFormMovimento(id) {
  try {
    const res = await apiFetch(`${API_URL}/magazzino/${id}`);
    const m = await res.json();

    document.getElementById("mov-id").value = m.id;
    document.getElementById("mov-codice").value = m.codice || "";
    document.getElementById("mov-anno").value = m.anno_campagna || "";
    document.getElementById("mov-tipo").value = m.tipo_movimento || "carico";
    aggiornaCausaliPerTipo(m.tipo_movimento);
    document.getElementById("mov-causale").value = m.causale || "";
    document.getElementById("mov-quantita").value = m.quantita || "";
    document.getElementById("mov-confezionamento").value = m.confezionamento_id || "";
    document.getElementById("mov-cliente").value = m.cliente_id || "";
    document.getElementById("mov-riferimento").value = m.riferimento_documento || "";
    document.getElementById("mov-note").value = m.note || "";

    // Data
    const dataInput = document.getElementById("mov-data");
    if (dataInput && dataInput._flatpickr && m.data_movimento) {
      dataInput._flatpickr.setDate(m.data_movimento, true);
    } else if (dataInput) {
      dataInput.value = m.data_movimento || "";
    }

    aggiornaGiacenzaInfo();
  } catch (e) {
    console.error("Errore caricamento movimento", e);
  }
}

async function salvaMovimento(e) {
  e.preventDefault();

  const id = document.getElementById("mov-id")?.value;
  const data = {
    confezionamento_id: parseInt(document.getElementById("mov-confezionamento").value),
    tipo_movimento: document.getElementById("mov-tipo").value,
    causale: document.getElementById("mov-causale").value,
    quantita: parseInt(document.getElementById("mov-quantita").value),
    data_movimento: document.getElementById("mov-data").value,
    anno_campagna: parseInt(document.getElementById("mov-anno").value),
    cliente_id: document.getElementById("mov-cliente").value ? parseInt(document.getElementById("mov-cliente").value) : null,
    riferimento_documento: document.getElementById("mov-riferimento").value || null,
    note: document.getElementById("mov-note").value || null,
  };

  if (!id) {
    data.codice = document.getElementById("mov-codice").value || "";
  }

  const url = id ? `${API_URL}/magazzino/${id}` : `${API_URL}/magazzino/`;
  const method = id ? "PUT" : "POST";

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore salvataggio");
      return;
    }
    renderMagazzino();
  } catch (e) {
    console.error("Errore salvataggio movimento", e);
    alert("Errore di rete");
  }
}

function editMovimento(id) {
  renderMovimentoForm(id);
}

async function sincronizzaMagazzino() {
  const anno = document.getElementById("filtro-mag-anno")?.value || "";
  const qs = anno ? `?anno=${anno}` : "";
  try {
    const res = await apiFetch(`${API_URL}/magazzino/sincronizza${qs}`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Errore sincronizzazione");
      return;
    }
    alert(data.messaggio || `${data.sincronizzati} confezionamenti sincronizzati.`);
    caricaMagStats();
    if (magazzinoTabAttiva === "giacenze") caricaGiacenze();
    else caricaMovimenti();
  } catch (e) {
    console.error("Errore sincronizzazione magazzino", e);
    alert("Errore di rete");
  }
}

function eliminaMovimento(id, codice) {
  const msg = codice ? `Eliminare il movimento ${codice}?` : "Eliminare questo movimento?";
  mostraConferma(msg, async () => {
    try {
      const res = await apiFetch(`${API_URL}/magazzino/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore eliminazione");
        return;
      }
      renderMagazzino();
    } catch (e) {
      console.error("Errore eliminazione movimento", e);
    }
  });
}


// =============================================
// VENDITE
// =============================================

function fmtEuro(v) {
  if (v == null) return "€ 0,00";
  return "€ " + Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statoBadge(stato) {
  const map = {
    bozza: '<span class="badge bg-warning text-dark">Bozza</span>',
    confermata: '<span class="badge bg-info">Confermata</span>',
    spedita: '<span class="badge bg-primary">Spedita</span>',
    pagata: '<span class="badge bg-success">Pagata</span>',
  };
  return map[stato] || `<span class="badge bg-secondary">${stato}</span>`;
}

// ---- LISTA VENDITE ----

async function renderVendite() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-vendite");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-nuova-vendita")?.addEventListener("click", () => renderVenditaForm());

  // Carica anni
  try {
    const res = await apiFetch(`${API_URL}/vendite/anni`);
    const anni = await res.json();
    const selAnno = document.getElementById("filtro-vendite-anno");
    const currentYear = new Date().getFullYear();
    const anniSet = new Set([...anni, currentYear]);
    const anniOrd = [...anniSet].sort((a, b) => b - a);
    selAnno.innerHTML = '<option value="" selected>Tutti</option>' + anniOrd.map(a => `<option value="${a}">${a}</option>`).join("");
  } catch (e) { console.error(e); }

  // Carica clienti per filtro
  try {
    const res = await apiFetch(`${API_URL}/clienti/?per_page=100`);
    const clienti = (await res.json()).items;
    const selCli = document.getElementById("filtro-vendite-cliente");
    selCli.innerHTML = '<option value="">Tutti</option>' + clienti.map(c => {
      const nome = c.tipo_cliente === "azienda" ? (c.ragione_sociale || "") : `${c.nome || ""} ${c.cognome || ""}`.trim();
      return `<option value="${c.id}">${nome}</option>`;
    }).join("");
  } catch (e) { console.error(e); }

  // Event filtri
  document.getElementById("filtro-vendite-anno")?.addEventListener("change", () => { caricaVenditeStats(); caricaVendite(); });
  document.getElementById("filtro-vendite-stato")?.addEventListener("change", () => caricaVendite());
  document.getElementById("filtro-vendite-cliente")?.addEventListener("change", () => caricaVendite());
  document.getElementById("search-vendite")?.addEventListener("input", debounceSearch(() => caricaVendite()));
  document.getElementById("btn-export-vendite-csv")?.addEventListener("click", () => {
    const params = new URLSearchParams();
    const anno = document.getElementById("filtro-vendite-anno")?.value;
    const stato = document.getElementById("filtro-vendite-stato")?.value;
    const clienteId = document.getElementById("filtro-vendite-cliente")?.value;
    if (anno) params.set("anno", anno);
    if (stato) params.set("stato", stato);
    if (clienteId) params.set("cliente_id", clienteId);
    scaricaCSV("vendite", params.toString(), "Vendite.csv");
  });

  await caricaVenditeStats();
  await caricaVendite();
}

async function caricaVenditeStats() {
  const anno = document.getElementById("filtro-vendite-anno")?.value || "";
  try {
    const url = anno ? `${API_URL}/vendite/stats?anno=${anno}` : `${API_URL}/vendite/stats`;
    const res = await apiFetch(url);
    const s = await res.json();
    document.getElementById("stat-vendite-totale").textContent = s.totale || 0;
    document.getElementById("stat-vendite-fatturato").textContent = fmtEuro(s.fatturato);
    document.getElementById("stat-vendite-bozze").textContent = s.bozze || 0;
    document.getElementById("stat-vendite-da-incassare").textContent = fmtEuro(s.da_incassare);
    document.getElementById("stat-vendite-incassato").textContent = fmtEuro(s.incassato);
  } catch (e) { console.error(e); }
}

async function caricaVendite(page = 1) {
  const anno = document.getElementById("filtro-vendite-anno")?.value || "";
  const stato = document.getElementById("filtro-vendite-stato")?.value || "";
  const clienteId = document.getElementById("filtro-vendite-cliente")?.value || "";
  const search = document.getElementById("search-vendite")?.value?.trim() || "";

  const params = new URLSearchParams();
  if (anno) params.set("anno", anno);
  if (stato) params.set("stato", stato);
  if (clienteId) params.set("cliente_id", clienteId);
  if (search) params.set("search", search);
  params.set("page", page);
  params.set("per_page", 10);

  try {
    const res = await apiFetch(`${API_URL}/vendite/?${params}`);
    const data = await res.json();
    venditeLista = data.items;
    renderTabellaVendite();
    renderPaginazione("vendite-pagination", "vendite-page-info", data.page, data.pages, data.total, caricaVendite);
  } catch (e) { console.error(e); }
}

function renderTabellaVendite() {
  const tbody = document.getElementById("vendite-tbody");
  if (!tbody) return;
  if (!venditeLista.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Nessuna vendita trovata.</td></tr>';
    return;
  }
  tbody.innerHTML = venditeLista.map(v => `
    <tr>
      <td><strong>${v.codice}</strong></td>
      <td>${v.data_vendita || "—"}</td>
      <td>${v.cliente_denominazione || "—"}</td>
      <td>${statoBadge(v.stato)}</td>
      <td>${v.numero_fattura || "—"}</td>
      <td class="text-end">${fmtEuro(v.importo_totale)}</td>
      <td class="text-center text-nowrap">
        ${v.stato === "bozza"
          ? `<button class="btn btn-sm btn-outline-light me-1" onclick="renderVenditaDettaglio(${v.id})" title="Dettaglio"><i class="fa-solid fa-eye"></i></button>
             <button class="btn btn-sm btn-outline-light me-1" onclick="renderVenditaForm(${v.id})" title="Modifica"><i class="fa-solid fa-pen"></i></button>
             <button class="btn btn-sm btn-success me-1" onclick="confermaVendita(${v.id})" title="Conferma"><i class="fa-solid fa-check"></i></button>
             <button class="btn btn-sm btn-outline-danger" onclick="eliminaVendita(${v.id}, '${escapeHtml(v.codice)}')" title="Elimina"><i class="fa-solid fa-trash"></i></button>`
          : `<button class="btn btn-sm btn-outline-light me-1" onclick="renderVenditaDettaglio(${v.id})" title="Dettaglio"><i class="fa-solid fa-eye"></i></button>${v.stato === "confermata" ? `<button class="btn btn-sm btn-info me-1" onclick="spedisciVendita(${v.id}, ${v.anno_campagna})" title="Spedisci"><i class="fa-solid fa-truck"></i></button><button class="btn btn-sm btn-accent" onclick="pagaVendita(${v.id})" title="Paga"><i class="fa-solid fa-money-bill"></i></button>` : ""}${v.stato === "spedita" ? `<button class="btn btn-sm btn-accent" onclick="pagaVendita(${v.id})" title="Paga"><i class="fa-solid fa-money-bill"></i></button>` : ""}`
        }
      </td>
    </tr>
  `).join("");
}


// ---- FORM VENDITA (bozza) ----

async function renderVenditaForm(venditaId = null) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-vendita-form");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  venditaInModifica = null;

  // Carica confezionamenti per select righe
  try {
    const res = await apiFetch(`${API_URL}/confezionamenti/?per_page=100`);
    venditeConfezionamentiCache = (await res.json()).items;
  } catch (e) { venditeConfezionamentiCache = []; }

  // Carica clienti
  let clientiOptions = '<option value="">— Seleziona —</option>';
  try {
    const res = await apiFetch(`${API_URL}/clienti/?per_page=100`);
    const clienti = (await res.json()).items;
    clientiOptions += clienti.map(c => {
      const nome = c.tipo_cliente === "azienda" ? (c.ragione_sociale || "") : `${c.nome || ""} ${c.cognome || ""}`.trim();
      return `<option value="${c.id}" data-sconto="${c.sconto_default || 0}" data-sped-ind="${c.consegna_indirizzo || c.indirizzo || ""}" data-sped-cap="${c.consegna_cap || c.cap || ""}" data-sped-citta="${c.consegna_citta || c.citta || ""}" data-sped-prov="${c.consegna_provincia || c.provincia || ""}">${nome}</option>`;
    }).join("");
  } catch (e) { console.error(e); }
  document.getElementById("vf-cliente").innerHTML = clientiOptions;

  const currentYear = new Date().getFullYear();
  document.getElementById("vf-anno").value = currentYear;

  // Flatpickr sulla data
  const fpData = flatpickr("#vf-data", { locale: "it", dateFormat: "Y-m-d", defaultDate: "today" });

  // Auto-genera codice
  async function aggiornaCodiceDaAnno(anno) {
    try {
      const res = await apiFetch(`${API_URL}/vendite/next-codice?anno=${anno}`);
      const data = await res.json();
      document.getElementById("vf-codice").value = data.codice;
    } catch (e) { console.error(e); }
  }
  await aggiornaCodiceDaAnno(currentYear);

  // Quando cambia anno → rigenera codice
  document.getElementById("vf-anno").addEventListener("change", (e) => {
    const anno = parseInt(e.target.value);
    if (anno) aggiornaCodiceDaAnno(anno);
  });

  // Quando cambia cliente → auto-compila sconto e indirizzo spedizione
  document.getElementById("vf-cliente").addEventListener("change", (e) => {
    const opt = e.target.selectedOptions[0];
    if (opt && opt.value) {
      document.getElementById("vf-sconto").value = opt.dataset.sconto || 0;
      document.getElementById("vf-sped-indirizzo").value = opt.dataset.spedInd || "";
      document.getElementById("vf-sped-cap").value = opt.dataset.spedCap || "";
      document.getElementById("vf-sped-citta").value = opt.dataset.spedCitta || "";
      document.getElementById("vf-sped-provincia").value = opt.dataset.spedProv || "";
      ricalcolaTotaliVendita();
    }
  });

  // Sconto e IVA → ricalcola
  document.getElementById("vf-sconto").addEventListener("input", ricalcolaTotaliVendita);
  document.getElementById("vf-iva").addEventListener("input", ricalcolaTotaliVendita);

  // Aggiungi riga
  document.getElementById("btn-aggiungi-riga").addEventListener("click", () => aggiungiRigaVendita());

  // Torna alla lista
  document.getElementById("btn-torna-vendite").addEventListener("click", renderVendite);

  // Submit
  document.getElementById("vendita-form").addEventListener("submit", salvaVendita);

  // Se modifica, carica dati
  if (venditaId) {
    try {
      const res = await apiFetch(`${API_URL}/vendite/${venditaId}`);
      const v = await res.json();
      venditaInModifica = v;
      document.getElementById("vendita-form-title").textContent = `Modifica Vendita ${v.codice}`;
      document.getElementById("vf-id").value = v.id;
      document.getElementById("vf-codice").value = v.codice;
      document.getElementById("vf-data").value = v.data_vendita;
      document.getElementById("vf-data")._flatpickr?.setDate(v.data_vendita);
      document.getElementById("vf-anno").value = v.anno_campagna;
      document.getElementById("vf-cliente").value = v.cliente_id;
      document.getElementById("vf-sconto").value = v.sconto_percentuale || 0;
      document.getElementById("vf-iva").value = v.iva_percentuale || 4;
      document.getElementById("vf-sped-indirizzo").value = v.spedizione_indirizzo || "";
      document.getElementById("vf-sped-cap").value = v.spedizione_cap || "";
      document.getElementById("vf-sped-citta").value = v.spedizione_citta || "";
      document.getElementById("vf-sped-provincia").value = v.spedizione_provincia || "";
      document.getElementById("vf-note").value = v.note || "";

      // Carica righe
      for (const r of v.righe) {
        aggiungiRigaVendita(r);
      }
      ricalcolaTotaliVendita();

      // Mostra bottone elimina
      const btnElim = document.getElementById("btn-elimina-vendita");
      btnElim.style.display = "";
      btnElim.addEventListener("click", () => eliminaVendita(v.id, v.codice));
    } catch (e) { console.error(e); }
  } else {
    // Nuova: aggiungi una riga vuota
    aggiungiRigaVendita();
  }
}

function aggiungiRigaVendita(rigaData = null) {
  const tbody = document.getElementById("vendita-righe-tbody");
  const tr = document.createElement("tr");

  let confOptions = '<option value="">— Seleziona —</option>';
  confOptions += venditeConfezionamentiCache.map(c => {
    const label = `${c.codice} — ${c.formato} (${c.contenitore_descrizione || "N/A"})`;
    return `<option value="${c.id}" data-prezzo="${c.prezzo_unitario || 0}">${label}</option>`;
  }).join("");

  tr.innerHTML = `
    <td>
      <select class="form-select form-select-sm riga-conf" required>${confOptions}</select>
    </td>
    <td><input type="number" class="form-control form-control-sm text-center riga-qty" min="1" value="${rigaData ? rigaData.quantita : 1}" required /></td>
    <td><input type="number" class="form-control form-control-sm text-end riga-prezzo" step="0.01" min="0" value="${rigaData ? rigaData.prezzo_unitario : 0}" required /></td>
    <td><input type="text" class="form-control form-control-sm text-end riga-importo" readonly value="${rigaData ? Number(rigaData.importo_riga).toFixed(2) : '0.00'}" /></td>
    <td class="text-center">
      <button type="button" class="btn btn-sm btn-outline-danger btn-rimuovi-riga"><i class="fa-solid fa-times"></i></button>
    </td>
  `;

  if (rigaData && rigaData.confezionamento_id) {
    tr.querySelector(".riga-conf").value = rigaData.confezionamento_id;
  }

  // Quando si seleziona un confezionamento → auto-compila prezzo listino
  tr.querySelector(".riga-conf").addEventListener("change", (e) => {
    const opt = e.target.selectedOptions[0];
    const prezzo = parseFloat(opt?.dataset.prezzo || 0);
    tr.querySelector(".riga-prezzo").value = prezzo.toFixed(2);
    calcolaImportoRiga(tr);
  });

  tr.querySelector(".riga-qty").addEventListener("input", () => calcolaImportoRiga(tr));
  tr.querySelector(".riga-prezzo").addEventListener("input", () => calcolaImportoRiga(tr));

  tr.querySelector(".btn-rimuovi-riga").addEventListener("click", () => {
    tr.remove();
    ricalcolaTotaliVendita();
  });

  tbody.appendChild(tr);
}

function calcolaImportoRiga(tr) {
  const qty = parseInt(tr.querySelector(".riga-qty").value) || 0;
  const prezzo = parseFloat(tr.querySelector(".riga-prezzo").value) || 0;
  const importo = qty * prezzo;
  tr.querySelector(".riga-importo").value = importo.toFixed(2);
  ricalcolaTotaliVendita();
}

function ricalcolaTotaliVendita() {
  const righe = document.querySelectorAll("#vendita-righe-tbody tr");
  let imponibile = 0;
  righe.forEach(tr => {
    imponibile += parseFloat(tr.querySelector(".riga-importo")?.value || 0);
  });

  const sconto = parseFloat(document.getElementById("vf-sconto")?.value || 0);
  const ivaPct = parseFloat(document.getElementById("vf-iva")?.value || 4);

  const scontoVal = imponibile * (sconto / 100);
  const imponibileScontato = imponibile - scontoVal;
  const importoIva = imponibileScontato * (ivaPct / 100);
  const totale = imponibileScontato + importoIva;

  document.getElementById("vf-imponibile").value = imponibile.toFixed(2);
  document.getElementById("vf-imponibile-scontato").value = imponibileScontato.toFixed(2);
  document.getElementById("vf-importo-iva").value = importoIva.toFixed(2);
  document.getElementById("vf-totale").value = totale.toFixed(2);
}

async function salvaVendita(e) {
  e.preventDefault();

  // Raccogli righe
  const righe = [];
  document.querySelectorAll("#vendita-righe-tbody tr").forEach(tr => {
    const confId = parseInt(tr.querySelector(".riga-conf").value);
    const qty = parseInt(tr.querySelector(".riga-qty").value) || 0;
    const prezzo = parseFloat(tr.querySelector(".riga-prezzo").value) || 0;
    const importo = parseFloat(tr.querySelector(".riga-importo").value) || 0;
    if (confId && qty > 0) {
      righe.push({
        confezionamento_id: confId,
        quantita: qty,
        prezzo_unitario: prezzo,
        importo_riga: importo,
      });
    }
  });

  if (!righe.length) {
    alert("Aggiungi almeno una riga prodotto.");
    return;
  }

  const payload = {
    codice: document.getElementById("vf-codice").value,
    cliente_id: parseInt(document.getElementById("vf-cliente").value),
    data_vendita: document.getElementById("vf-data").value,
    anno_campagna: parseInt(document.getElementById("vf-anno").value),
    imponibile: parseFloat(document.getElementById("vf-imponibile").value) || 0,
    sconto_percentuale: parseFloat(document.getElementById("vf-sconto").value) || 0,
    imponibile_scontato: parseFloat(document.getElementById("vf-imponibile-scontato").value) || 0,
    iva_percentuale: parseFloat(document.getElementById("vf-iva").value) || 4,
    importo_iva: parseFloat(document.getElementById("vf-importo-iva").value) || 0,
    importo_totale: parseFloat(document.getElementById("vf-totale").value) || 0,
    spedizione_indirizzo: document.getElementById("vf-sped-indirizzo").value || null,
    spedizione_cap: document.getElementById("vf-sped-cap").value || null,
    spedizione_citta: document.getElementById("vf-sped-citta").value || null,
    spedizione_provincia: document.getElementById("vf-sped-provincia").value || null,
    note: document.getElementById("vf-note").value || null,
    righe,
  };

  const id = document.getElementById("vf-id")?.value;
  const isEdit = !!id;

  try {
    const res = await apiFetch(`${API_URL}/vendite/${isEdit ? id : ""}`, {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore salvataggio vendita");
      return;
    }

    const saved = await res.json();
    // Dopo il salvataggio vai al dettaglio se confermata, altrimenti torna alla lista
    renderVendite();
  } catch (e) {
    console.error("Errore salvataggio vendita:", e);
    alert("Errore di connessione");
  }
}

function eliminaVendita(id, codice) {
  mostraConferma(`Eliminare la vendita "${codice}"?`, async () => {
    try {
      const res = await apiFetch(`${API_URL}/vendite/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore eliminazione");
        return;
      }
      renderVendite();
    } catch (e) {
      console.error("Errore eliminazione vendita", e);
    }
  });
}


// ---- DETTAGLIO VENDITA ----

async function renderVenditaDettaglio(venditaId) {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-vendita-dettaglio");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-torna-vendite-det")?.addEventListener("click", renderVendite);

  try {
    const res = await apiFetch(`${API_URL}/vendite/${venditaId}`);
    if (!res.ok) { alert("Vendita non trovata"); renderVendite(); return; }
    const v = await res.json();

    document.getElementById("vd-titolo").textContent = `Vendita ${v.codice}`;
    document.getElementById("vd-sottotitolo").textContent = `${v.cliente_denominazione || ""} — ${v.stato.toUpperCase()}`;
    document.getElementById("vd-codice").textContent = v.codice;
    document.getElementById("vd-data").textContent = v.data_vendita || "—";
    document.getElementById("btn-modifica-data").addEventListener("click", () => modificaDataVendita(v.id, v.data_vendita));
    document.getElementById("vd-cliente").textContent = v.cliente_denominazione || "—";
    document.getElementById("vd-stato-badge").innerHTML = statoBadge(v.stato);
    document.getElementById("vd-fattura").textContent = v.numero_fattura || "—";
    document.getElementById("vd-ddt").textContent = v.numero_ddt || "—";
    document.getElementById("vd-data-conferma").textContent = v.data_conferma || "—";
    document.getElementById("vd-data-spedizione").textContent = v.data_spedizione || "—";

    // Indirizzo spedizione
    const spedParts = [v.spedizione_indirizzo, [v.spedizione_cap, v.spedizione_citta, v.spedizione_provincia ? `(${v.spedizione_provincia})` : ""].filter(Boolean).join(" ")].filter(Boolean);
    document.getElementById("vd-sped-indirizzo").textContent = spedParts.join(" — ") || "Non specificato";

    // Righe
    const righeHtml = v.righe.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${r.confezionamento_codice || "—"}</td>
        <td>${r.confezionamento_formato || "—"}</td>
        <td>${r.contenitore_descrizione || "—"}</td>
        <td class="text-center">${r.quantita}</td>
        <td class="text-end">${fmtEuro(r.prezzo_unitario)}</td>
        <td class="text-end">${fmtEuro(r.importo_riga)}</td>
      </tr>
    `).join("");
    document.getElementById("vd-righe-tbody").innerHTML = righeHtml;

    // Totali
    document.getElementById("vd-imponibile").textContent = fmtEuro(v.imponibile);
    if (v.sconto_percentuale && v.sconto_percentuale > 0) {
      document.getElementById("vd-sconto-pct").textContent = v.sconto_percentuale;
      document.getElementById("vd-sconto-val").textContent = "- " + fmtEuro(v.imponibile - v.imponibile_scontato);
    } else {
      document.getElementById("vd-sconto-row").style.display = "none";
    }
    document.getElementById("vd-imponibile-scontato").textContent = fmtEuro(v.imponibile_scontato);
    document.getElementById("vd-iva-pct").textContent = v.iva_percentuale || 4;
    document.getElementById("vd-importo-iva").textContent = fmtEuro(v.importo_iva);
    document.getElementById("vd-totale").textContent = fmtEuro(v.importo_totale);

    // Pagamento
    if (v.stato === "pagata") {
      document.getElementById("vd-pagamento-card").style.display = "";
      document.getElementById("vd-pag-data").textContent = v.data_pagamento || "—";
      document.getElementById("vd-pag-modalita").textContent = v.modalita_pagamento || "—";
      document.getElementById("vd-pag-riferimento").textContent = v.riferimento_pagamento || "—";
    }

    // Note
    if (v.note) {
      document.getElementById("vd-note-card").style.display = "";
      document.getElementById("vd-note").textContent = v.note;
    }

    // Azioni basate sullo stato
    if (v.stato === "bozza") {
      const btnModifica = document.getElementById("btn-modifica-vendita");
      btnModifica.style.display = "";
      btnModifica.addEventListener("click", () => renderVenditaForm(v.id));

      const btnConferma = document.getElementById("btn-conferma-vendita");
      btnConferma.style.display = "";
      btnConferma.addEventListener("click", () => confermaVendita(v.id));
    }

    if (v.stato === "confermata") {
      document.getElementById("btn-spedisci-vendita").style.display = "";
      document.getElementById("btn-spedisci-vendita").addEventListener("click", () => spedisciVendita(v.id, v.anno_campagna));

      document.getElementById("btn-paga-vendita").style.display = "";
      document.getElementById("btn-paga-vendita").addEventListener("click", () => pagaVendita(v.id));
    }

    if (v.stato === "spedita") {
      document.getElementById("btn-paga-vendita").style.display = "";
      document.getElementById("btn-paga-vendita").addEventListener("click", () => pagaVendita(v.id));
    }

    // PDF sempre disponibili per confermata+
    if (v.stato !== "bozza") {
      document.getElementById("btn-download-fattura").style.display = "";
      document.getElementById("btn-download-fattura").addEventListener("click", () => scaricaFatturaPdf(v.id));

      document.getElementById("btn-download-ddt").style.display = "";
      document.getElementById("btn-download-ddt").addEventListener("click", () => scaricaDdtPdf(v.id));
    }

  } catch (e) {
    console.error("Errore caricamento dettaglio vendita:", e);
  }
}


// ---- TRANSIZIONI DI STATO ----

function _afterVenditaTransition(id) {
  // Se siamo nella lista vendite, aggiorna la lista; altrimenti vai al dettaglio
  if (document.getElementById("vendite-tbody")) {
    caricaVenditeStats();
    caricaVendite();
  } else {
    renderVenditaDettaglio(id);
  }
}

function modificaDataVendita(id, dataAttuale) {
  const overlay = document.createElement("div");
  overlay.className = "modal-confirm-overlay";
  overlay.innerHTML = `
    <div class="modal-confirm-box" style="max-width:350px;">
      <h5 class="mb-3">Modifica Data Vendita</h5>
      <div class="mb-3">
        <label class="form-label form-label-sm">Nuova data</label>
        <input type="text" id="modal-nuova-data" class="form-control form-control-sm" />
      </div>
      <div class="d-flex gap-2 justify-content-end">
        <button class="btn btn-outline-secondary btn-sm" id="modal-data-annulla">Annulla</button>
        <button class="btn btn-primary btn-sm" id="modal-data-salva">Salva</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  flatpickr("#modal-nuova-data", { locale: "it", dateFormat: "Y-m-d", defaultDate: dataAttuale || "today" });

  overlay.querySelector("#modal-data-annulla").addEventListener("click", () => overlay.remove());
  overlay.querySelector("#modal-data-salva").addEventListener("click", async () => {
    const nuovaData = document.getElementById("modal-nuova-data").value;
    if (!nuovaData) { alert("Inserire una data"); return; }

    try {
      const res = await apiFetch(`${API_URL}/vendite/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data_vendita: nuovaData }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore modifica data");
        return;
      }
      overlay.remove();
      renderVenditaDettaglio(id);
    } catch (e) {
      console.error("Errore modifica data vendita:", e);
    }
  });
}

function confermaVendita(id) {
  mostraConferma("Confermare la vendita? Il magazzino verra' scalato automaticamente.", async () => {
    try {
      const res = await apiFetch(`${API_URL}/vendite/${id}/conferma`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore conferma");
        return;
      }
      _afterVenditaTransition(id);
    } catch (e) {
      console.error("Errore conferma vendita:", e);
    }
  }, "Conferma e Scarica Magazzino", "btn-success");
}

function spedisciVendita(id, anno) {
  // Modal per inserire dati spedizione
  const overlay = document.createElement("div");
  overlay.className = "modal-confirm-overlay";
  overlay.innerHTML = `
    <div class="modal-confirm-box" style="max-width:450px;">
      <h5 class="mb-3">Segna come Spedita</h5>
      <div class="mb-2">
        <label class="form-label form-label-sm">Data Spedizione *</label>
        <input type="text" id="modal-sped-data" class="form-control form-control-sm" required />
      </div>
      <div class="mb-2">
        <label class="form-label form-label-sm">Numero DDT (auto se vuoto)</label>
        <input type="text" id="modal-sped-ddt" class="form-control form-control-sm" />
      </div>
      <div class="mb-3">
        <label class="form-label form-label-sm">Note Spedizione</label>
        <textarea id="modal-sped-note" class="form-control form-control-sm" rows="2"></textarea>
      </div>
      <div class="d-flex gap-2 justify-content-end">
        <button class="btn btn-outline-secondary btn-sm" id="modal-sped-annulla">Annulla</button>
        <button class="btn btn-info btn-sm" id="modal-sped-conferma">Conferma Spedizione</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  flatpickr("#modal-sped-data", { locale: "it", dateFormat: "Y-m-d", defaultDate: "today" });

  overlay.querySelector("#modal-sped-annulla").addEventListener("click", () => overlay.remove());
  overlay.querySelector("#modal-sped-conferma").addEventListener("click", async () => {
    const dataSped = document.getElementById("modal-sped-data").value;
    if (!dataSped) { alert("Inserire la data di spedizione"); return; }

    const payload = {
      data_spedizione: dataSped,
      numero_ddt: document.getElementById("modal-sped-ddt").value || null,
      note_spedizione: document.getElementById("modal-sped-note").value || null,
    };

    try {
      const res = await apiFetch(`${API_URL}/vendite/${id}/spedisci`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore spedizione");
        return;
      }
      overlay.remove();
      _afterVenditaTransition(id);
    } catch (e) {
      console.error("Errore spedizione:", e);
    }
  });
}

function pagaVendita(id) {
  const overlay = document.createElement("div");
  overlay.className = "modal-confirm-overlay";
  overlay.innerHTML = `
    <div class="modal-confirm-box" style="max-width:450px;">
      <h5 class="mb-3">Registra Pagamento</h5>
      <div class="mb-2">
        <label class="form-label form-label-sm">Data Pagamento *</label>
        <input type="text" id="modal-pag-data" class="form-control form-control-sm" required />
      </div>
      <div class="mb-2">
        <label class="form-label form-label-sm">Modalita'</label>
        <select id="modal-pag-modalita" class="form-select form-select-sm">
          <option value="">— Seleziona —</option>
          <option value="Bonifico">Bonifico</option>
          <option value="Contanti">Contanti</option>
          <option value="Assegno">Assegno</option>
          <option value="Carta di credito">Carta di credito</option>
          <option value="Altro">Altro</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label form-label-sm">Riferimento</label>
        <input type="text" id="modal-pag-rif" class="form-control form-control-sm" placeholder="N. bonifico, CRO, ecc." />
      </div>
      <div class="d-flex gap-2 justify-content-end">
        <button class="btn btn-outline-secondary btn-sm" id="modal-pag-annulla">Annulla</button>
        <button class="btn btn-accent btn-sm" id="modal-pag-conferma">Registra Pagamento</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  flatpickr("#modal-pag-data", { locale: "it", dateFormat: "Y-m-d", defaultDate: "today" });

  overlay.querySelector("#modal-pag-annulla").addEventListener("click", () => overlay.remove());
  overlay.querySelector("#modal-pag-conferma").addEventListener("click", async () => {
    const dataPag = document.getElementById("modal-pag-data").value;
    if (!dataPag) { alert("Inserire la data di pagamento"); return; }

    const payload = {
      data_pagamento: dataPag,
      modalita_pagamento: document.getElementById("modal-pag-modalita").value || null,
      riferimento_pagamento: document.getElementById("modal-pag-rif").value || null,
    };

    try {
      const res = await apiFetch(`${API_URL}/vendite/${id}/paga`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore pagamento");
        return;
      }
      overlay.remove();
      _afterVenditaTransition(id);
    } catch (e) {
      console.error("Errore pagamento:", e);
    }
  });
}


// ---- DOWNLOAD PDF ----

async function scaricaFatturaPdf(id) {
  try {
    const res = await apiFetch(`${API_URL}/vendite/${id}/fattura/pdf`);
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore download fattura");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Fattura_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error("Errore download fattura:", e);
  }
}

async function scaricaDdtPdf(id) {
  try {
    const res = await apiFetch(`${API_URL}/vendite/${id}/ddt/pdf`);
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore download DDT");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `DDT_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error("Errore download DDT:", e);
  }
}


// =============================================
// INIT
// =============================================

document.addEventListener("DOMContentLoaded", () => {
  if (!checkAuth()) return;

  // Mostra username nella sidebar
  const usernameEl = document.getElementById("current-username");
  if (usernameEl) usernameEl.textContent = getCurrentUserName();

  // Render home
  renderHome();

  // Sidebar navigation
  document.getElementById("menu-home")?.addEventListener("click", () => {
    setActiveMenu("menu-home");
    renderHome();
  });

  document.getElementById("menu-dashboard")?.addEventListener("click", () => {
    setActiveMenu("menu-dashboard");
    renderDashboard();
  });

  document.getElementById("menu-parcelle")?.addEventListener("click", () => {
    setActiveMenu("menu-parcelle");
    renderParcelle();
  });

  document.getElementById("menu-produzione")?.addEventListener("click", () => {
    setActiveMenu("menu-produzione");
    renderProduzione();
  });

  document.getElementById("menu-contenitori")?.addEventListener("click", () => {
    setActiveMenu("menu-contenitori");
    renderContenitori();
  });

  document.getElementById("menu-clienti")?.addEventListener("click", () => {
    setActiveMenu("menu-clienti");
    renderClienti();
  });

  document.getElementById("menu-fornitori")?.addEventListener("click", () => {
    setActiveMenu("menu-fornitori");
    renderFornitori();
  });

  document.getElementById("menu-costi")?.addEventListener("click", () => {
    setActiveMenu("menu-costi");
    renderCosti();
  });

  document.getElementById("menu-magazzino")?.addEventListener("click", () => {
    setActiveMenu("menu-magazzino");
    renderMagazzino();
  });

  document.getElementById("menu-vendite")?.addEventListener("click", () => {
    setActiveMenu("menu-vendite");
    renderVendite();
  });

  document.getElementById("menu-utenti")?.addEventListener("click", () => {
    setActiveMenu("menu-utenti");
    renderUtenti();
  });

  document.getElementById("menu-logout")?.addEventListener("click", logout);
});
