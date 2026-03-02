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
let contenitoriLista = [];
let contenitoreInModifica = null;
let clientiLista = [];
let clienteInModifica = null;

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
  window.location.href = "login.html";
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
  document.getElementById("quick-utenti")?.addEventListener("click", () => {
    setActiveMenu("menu-utenti");
    renderUtenti();
  });
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

  // Enter per filtrare
  document.getElementById("filtro-q")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") caricaParcelle();
  });
}

async function caricaParcelleStats() {
  try {
    const res = await fetch(`${API_URL}/parcelle/stats`);
    const stats = await res.json();
    document.getElementById("stat-parcelle").textContent = stats.totale_parcelle;
    document.getElementById("stat-ettari").textContent = parseFloat(stats.totale_ettari).toFixed(1);
    document.getElementById("stat-piante").textContent = stats.totale_piante.toLocaleString("it-IT");
    document.getElementById("stat-produttive").textContent = stats.per_stato?.produttivo || 0;
  } catch (err) {
    console.error("Errore caricamento stats:", err);
  }
}

async function caricaParcelle() {
  const q = document.getElementById("filtro-q")?.value || "";
  const varieta = document.getElementById("filtro-varieta")?.value || "";
  const stato = document.getElementById("filtro-stato")?.value || "";

  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (varieta) params.append("varieta", varieta);
  if (stato) params.append("stato", stato);

  try {
    const res = await fetch(`${API_URL}/parcelle/?${params}`);
    parcelleLista = await res.json();
    renderTabellaParcelle();
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
        <button class="btn-action btn-action-delete" onclick="eliminaParcella(${p.id}, '${p.nome}')" title="Elimina">
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
    const res = await fetch(`${API_URL}/parcelle/${id}`);
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/parcelle/${id}`, { method: "DELETE" });
      caricaParcelleStats();
      caricaParcelle();
    } catch (err) {
      console.error("Errore eliminazione:", err);
    }
  });
}

function mostraConferma(messaggio, onConfirm) {
  const overlay = document.createElement("div");
  overlay.className = "modal-confirm-overlay";
  overlay.innerHTML = `
    <div class="modal-confirm-box">
      <h5>${messaggio}</h5>
      <div class="d-flex gap-2 justify-content-center mt-3">
        <button class="btn btn-outline-secondary" id="modal-annulla">Annulla</button>
        <button class="btn btn-danger" id="modal-conferma">Elimina</button>
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
    const res = await fetch(`${API_URL}/users/`);
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
        <span class="badge-stato-${u.is_active ? 'produttivo' : 'dismesso'}">
          ${u.is_active ? "Attivo" : "Disattivato"}
        </span>
      </td>
      <td>
        <button class="btn-action btn-action-edit me-1" onclick="modificaUtente(${u.id}, '${u.username}', ${u.is_active})" title="Modifica">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="btn-action btn-action-delete" onclick="eliminaUtente(${u.id}, '${u.username}')" title="Elimina">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

function modificaUtente(id, username, isActive) {
  utenteInModifica = id;
  document.getElementById("form-utente-titolo").textContent = "Modifica Utente";
  document.getElementById("u-username").value = username;
  document.getElementById("u-password").value = "";
  document.getElementById("u-password").required = false;
  document.getElementById("u-attivo").checked = isActive;
}

function resetFormUtente() {
  utenteInModifica = null;
  document.getElementById("form-utente-titolo").textContent = "Nuovo Utente";
  document.getElementById("u-username").value = "";
  document.getElementById("u-password").value = "";
  document.getElementById("u-password").required = true;
  document.getElementById("u-attivo").checked = true;
}

async function salvaUtente() {
  const data = {
    username: document.getElementById("u-username").value.trim(),
    is_active: document.getElementById("u-attivo").checked,
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/users/${id}`, { method: "DELETE" });
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
    aggiornaTabProduzione();
    renderRaccolteLista();
  });
  document.getElementById("tab-lotti")?.addEventListener("click", () => {
    produzioneTabAttiva = "lotti";
    aggiornaTabProduzione();
    renderLottiLista();
  });
  document.getElementById("tab-confezionamento")?.addEventListener("click", () => {
    produzioneTabAttiva = "confezionamento";
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
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-raccolte-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await popolaFiltroAnniRaccolte();
  await popolaFiltroParcelle();
  initRaccolteListUI();
  await caricaRaccolteStats();
  await caricaRaccolte();
}

async function popolaFiltroAnniRaccolte() {
  try {
    const res = await fetch(`${API_URL}/raccolte/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-raccolte-anno");
    if (sel) {
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
}

async function popolaFiltroParcelle() {
  try {
    const res = await fetch(`${API_URL}/parcelle/`);
    const parcelle = await res.json();
    const sel = document.getElementById("filtro-raccolte-parcella");
    if (sel) {
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
    const res = await fetch(`${API_URL}/raccolte/stats?${params}`);
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

async function caricaRaccolte() {
  const anno = document.getElementById("filtro-raccolte-anno")?.value || "";
  const parcella = document.getElementById("filtro-raccolte-parcella")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (parcella) params.append("parcella_id", parcella);

  try {
    const res = await fetch(`${API_URL}/raccolte/?${params}`);
    raccolteLista = await res.json();
    renderTabellaRaccolte();
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
          <button class="btn-action btn-action-delete" onclick="eliminaRaccolta(${r.id}, '${r.codice}')" title="Elimina">
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
    const res = await fetch(`${API_URL}/raccolte/next-codice?anno=${anno}`);
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
    const res = await fetch(`${API_URL}/parcelle/`);
    const parcelle = await res.json();

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
    const res = await fetch(`${API_URL}/raccolte/${id}`);
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/raccolte/${id}`, { method: "DELETE" });
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
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-lotti-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await popolaFiltroAnniLotti();
  initLottiListUI();
  await caricaLottiStats();
  await caricaLotti();
}

async function popolaFiltroAnniLotti() {
  try {
    const res = await fetch(`${API_URL}/lotti/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-lotti-anno");
    if (sel) {
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
}

async function caricaLottiStats() {
  const anno = document.getElementById("filtro-lotti-anno")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);

  try {
    const res = await fetch(`${API_URL}/lotti/stats?${params}`);
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

async function caricaLotti() {
  const anno = document.getElementById("filtro-lotti-anno")?.value || "";
  const tipo = document.getElementById("filtro-lotti-tipo")?.value || "";
  const stato = document.getElementById("filtro-lotti-stato")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (tipo) params.append("tipo_olio", tipo);
  if (stato) params.append("stato", stato);

  try {
    const res = await fetch(`${API_URL}/lotti/?${params}`);
    lottiLista = await res.json();
    renderTabellaLotti();
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
        <button class="btn-action btn-action-delete" onclick="eliminaLotto(${l.id}, '${l.codice_lotto}')" title="Elimina">
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
    const res = await fetch(`${API_URL}/raccolte/${raccoltaId}`);
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
    const res = await fetch(`${API_URL}/lotti/next-codice?anno=${anno}`);
    const data = await res.json();
    document.getElementById("l-codice").value = data.codice;
  } catch (err) {
    console.error("Errore generazione codice lotto:", err);
  }
}

async function popolaSelectRaccolte() {
  try {
    const res = await fetch(`${API_URL}/raccolte/`);
    const raccolte = await res.json();
    const sel = document.getElementById("l-raccolta");
    if (sel) {
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
    const res = await fetch(`${API_URL}/lotti/${id}`);
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/lotti/${id}`, { method: "DELETE" });
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
    const res = await fetch(`${API_URL}/contenitori/`);
    contenitoriCache = await res.json();
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
  const container = document.getElementById("produzione-content");
  const tpl = document.getElementById("template-confezionamenti-lista");
  container.innerHTML = "";
  container.appendChild(tpl.content.cloneNode(true));

  await caricaContenitoriCache();
  await popolaFiltroAnniConf();
  popolaFiltroContenitori();
  initConfListUI();
  await caricaConfStats();
  await caricaConfezionamenti();
}

function popolaFiltroContenitori() {
  const sel = document.getElementById("filtro-conf-formato");
  if (!sel) return;
  contenitoriCache.forEach(ct => {
    const opt = document.createElement("option");
    opt.value = ct.codice;
    opt.textContent = ct.descrizione;
    sel.appendChild(opt);
  });
}

async function popolaFiltroAnniConf() {
  try {
    const res = await fetch(`${API_URL}/confezionamenti/anni`);
    const anni = await res.json();
    const sel = document.getElementById("filtro-conf-anno");
    if (sel) {
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
}

async function caricaConfStats() {
  const anno = document.getElementById("filtro-conf-anno")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);

  try {
    const res = await fetch(`${API_URL}/confezionamenti/stats?${params}`);
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

async function caricaConfezionamenti() {
  const anno = document.getElementById("filtro-conf-anno")?.value || "";
  const formato = document.getElementById("filtro-conf-formato")?.value || "";
  const params = new URLSearchParams();
  if (anno) params.append("anno", anno);
  if (formato) params.append("formato", formato);

  try {
    const res = await fetch(`${API_URL}/confezionamenti/?${params}`);
    confezionamentiLista = await res.json();
    renderTabellaConf();
  } catch (err) {
    console.error("Errore caricamento confezionamenti:", err);
  }
}

function renderTabellaConf() {
  const tbody = document.getElementById("conf-tbody");
  if (!tbody) return;

  if (confezionamentiLista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-secondary py-4">Nessun confezionamento trovato</td></tr>`;
    return;
  }

  tbody.innerHTML = confezionamentiLista.map(c => {
    const lottiNomi = c.lotti.map(l => `${l.lotto_codice} (${l.litri_utilizzati}L)`).join(", ") || "—";
    const costo = c.costo_totale ? `€ ${parseFloat(c.costo_totale).toFixed(0)}` : "—";
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
        <td>
          <button class="btn-action btn-action-edit me-1" onclick="renderConfezionamentoForm(${c.id})" title="Modifica">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn-action btn-action-delete" onclick="eliminaConfezionamento(${c.id}, '${c.codice}')" title="Elimina">
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
    const res = await fetch(`${API_URL}/lotti/`);
    const lotti = await res.json();

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
    const res = await fetch(`${API_URL}/confezionamenti/${id}`);
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
    note: document.getElementById("cf-note").value || null,
    lotti,
  };

  const method = confezionamentoInModifica ? "PUT" : "POST";
  const url = confezionamentoInModifica
    ? `${API_URL}/confezionamenti/${confezionamentoInModifica}`
    : `${API_URL}/confezionamenti/`;

  try {
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/confezionamenti/${id}`, { method: "DELETE" });
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

async function renderContenitori() {
  const main = document.getElementById("main-content");
  const tpl = document.getElementById("template-contenitori");
  main.innerHTML = "";
  main.appendChild(tpl.content.cloneNode(true));

  document.getElementById("btn-nuovo-contenitore")?.addEventListener("click", () => renderContenitoreForm());

  await caricaContenitori();
}

async function caricaContenitori() {
  try {
    const res = await fetch(`${API_URL}/contenitori/?tutti=true`);
    contenitoriLista = await res.json();
    renderContenitoriGrid();
  } catch (err) {
    console.error("Errore caricamento contenitori:", err);
  }
}

function renderContenitoriGrid() {
  const grid = document.getElementById("contenitori-grid");
  if (!grid) return;

  if (contenitoriLista.length === 0) {
    grid.innerHTML = `<div class="col-12 text-center text-secondary py-5">Nessun contenitore configurato</div>`;
    return;
  }

  grid.innerHTML = contenitoriLista.map(ct => {
    const fotoHtml = ct.foto
      ? `<img src="/uploads/${ct.foto}" alt="${ct.descrizione}" class="ct-card-img" />`
      : `<div class="ct-card-placeholder"><i class="fa-solid fa-bottle-water fa-2x"></i></div>`;
    const badgeAttivo = ct.attivo
      ? `<span class="badge bg-success">Attivo</span>`
      : `<span class="badge bg-secondary">Inattivo</span>`;

    return `
      <div class="col-md-4 col-lg-3">
        <div class="card ct-card ${!ct.attivo ? 'ct-card-inattivo' : ''}">
          <div class="ct-card-img-wrap">${fotoHtml}</div>
          <div class="ct-card-body">
            <div class="ct-card-title">${ct.descrizione}</div>
            <div class="ct-card-info">
              <span class="ct-card-cap">${ct.capacita_litri}L</span>
              ${badgeAttivo}
            </div>
            <div class="ct-card-code small text-secondary">${ct.codice}</div>
            <div class="ct-card-actions mt-2">
              <button class="btn-action btn-action-edit me-1" onclick="renderContenitoreForm(${ct.id})" title="Modifica">
                <i class="fa-solid fa-pen-to-square"></i>
              </button>
              <button class="btn-action btn-action-delete" onclick="eliminaContenitore(${ct.id}, '${ct.descrizione}')" title="Elimina">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
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
    const res = await fetch(`${API_URL}/contenitori/${id}`);
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/contenitori/${saved.id}/foto`, {
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

function eliminaContenitore(id, descrizione) {
  mostraConferma(`Eliminare il contenitore "${descrizione}"?`, async () => {
    try {
      const res = await fetch(`${API_URL}/contenitori/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore durante l'eliminazione.");
        return;
      }
      caricaContenitori();
    } catch (err) {
      console.error("Errore eliminazione contenitore:", err);
    }
  });
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
}

async function caricaClientiStats() {
  try {
    const res = await fetch(`${API_URL}/clienti/stats`);
    const s = await res.json();
    document.getElementById("stat-clienti-totale").textContent = s.totale;
    document.getElementById("stat-clienti-attivi").textContent = s.attivi;
    document.getElementById("stat-clienti-privati").textContent = s.privati;
    document.getElementById("stat-clienti-aziende").textContent = s.aziende;
  } catch (err) {
    console.error("Errore stats clienti:", err);
  }
}

async function caricaClienti() {
  const q = document.getElementById("filtro-clienti-q")?.value || "";
  const tipo = document.getElementById("filtro-clienti-tipo")?.value || "";
  const tutti = document.getElementById("filtro-clienti-tutti")?.checked || false;
  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (tipo) params.append("tipo", tipo);
  if (tutti) params.append("tutti", "true");

  try {
    const res = await fetch(`${API_URL}/clienti/?${params}`);
    clientiLista = await res.json();
    renderTabellaClienti();
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
          <button class="btn-action btn-action-delete" onclick="eliminaCliente(${c.id}, '${(c.denominazione || c.codice).replace(/'/g, "\\'")}')" title="Elimina">
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
    const res = await fetch(`${API_URL}/clienti/${id}`);
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

async function salvaCliente() {
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
  const url = clienteInModifica
    ? `${API_URL}/clienti/${clienteInModifica}`
    : `${API_URL}/clienti/`;

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

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
      await fetch(`${API_URL}/clienti/${id}`, { method: "DELETE" });
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

  document.getElementById("btn-filtra-fornitori").addEventListener("click", caricaFornitori);

  document.getElementById("filtro-fornitori-q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); caricaFornitori(); }
  });
}

async function caricaFornitoriStats() {
  try {
    const res = await fetch(`${API_URL}/fornitori/stats`);
    const data = await res.json();
    document.getElementById("stat-fornitori-totale").textContent = data.totale;
    document.getElementById("stat-fornitori-attivi").textContent = data.attivi;
    document.getElementById("stat-fornitori-privati").textContent = data.privati;
    document.getElementById("stat-fornitori-aziende").textContent = data.aziende;
  } catch (err) {
    console.error("Errore caricamento stats fornitori:", err);
  }
}

async function caricaFornitori() {
  const q = document.getElementById("filtro-fornitori-q")?.value || "";
  const tipo = document.getElementById("filtro-fornitori-tipo")?.value || "";
  const categoria = document.getElementById("filtro-fornitori-categoria")?.value || "";
  const tutti = document.getElementById("filtro-fornitori-tutti")?.checked || false;

  let url = `${API_URL}/fornitori/?tutti=${tutti}`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (tipo) url += `&tipo=${tipo}`;
  if (categoria) url += `&categoria=${categoria}`;

  try {
    const res = await fetch(url);
    fornitoriLista = await res.json();
    renderTabellaFornitori();
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
        <button class="btn btn-sm btn-outline-danger" onclick="eliminaFornitore(${f.id}, '${(f.denominazione || f.codice).replace(/'/g, "\\'")}')"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>`;
  }).join("");
}

async function editFornitore(id) {
  try {
    const res = await fetch(`${API_URL}/fornitori/${id}`);
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
    fetch(`${API_URL}/fornitori/next-codice`)
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

async function salvaFornitore(e) {
  e.preventDefault();

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
  const url = isEdit ? `${API_URL}/fornitori/${fornitoreInModifica.id}` : `${API_URL}/fornitori/`;
  const method = isEdit ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

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
      await fetch(`${API_URL}/fornitori/${id}`, { method: "DELETE" });
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

  // Filtri
  document.getElementById("filtro-costi-anno")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-tipo")?.addEventListener("change", () => {
    aggiornaFiltroCategorie();
    caricaCosti();
  });
  document.getElementById("filtro-costi-categoria")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-stato")?.addEventListener("change", () => caricaCosti());
  document.getElementById("filtro-costi-fornitore")?.addEventListener("change", () => caricaCosti());

  await caricaCategorieCosto();
  await popolaFiltroCosti();
  await caricaCostiStats();
  await caricaCosti();
}

async function caricaCategorieCosto() {
  try {
    const res = await fetch(`${API_URL}/categorie-costo/`);
    categorieCostoLista = await res.json();
  } catch (err) {
    console.error("Errore caricamento categorie:", err);
  }
}

async function popolaFiltroCosti() {
  // Anni
  try {
    const res = await fetch(`${API_URL}/costi/anni`);
    const anni = await res.json();
    const selAnno = document.getElementById("filtro-costi-anno");
    if (selAnno) {
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
    const res = await fetch(`${API_URL}/fornitori/?tutti=false`);
    const fornitori = await res.json();
    const selForn = document.getElementById("filtro-costi-fornitore");
    if (selForn) {
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
    const res = await fetch(url);
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

async function caricaCosti() {
  try {
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

    const res = await fetch(`${API_URL}/costi/?${params.toString()}`);
    costiLista = await res.json();
    renderTabellaCosti();
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
    const res = await fetch(`${API_URL}/costi/${id}`);
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
      const res = await fetch(`${API_URL}/costi/${costoId}/documento`, { method: "DELETE" });
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
    const res = await fetch(`${API_URL}/fornitori/?tutti=false`);
    const fornitori = await res.json();
    const sel = document.getElementById("costo-fornitore");
    if (!sel) return;
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
    const res = await fetch(`${API_URL}/costi/next-codice?anno=${anno}`);
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
    const res = await fetch(url, {
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
      await fetch(`${API_URL}/costi/${saved.id}/documento`, {
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
      await fetch(`${API_URL}/costi/${id}`, { method: "DELETE" });
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
  document.getElementById("btn-nuova-categoria")?.addEventListener("click", () => mostraFormCategoria());
  document.getElementById("btn-annulla-cat")?.addEventListener("click", () => nascondiFormCategoria());
  document.getElementById("form-categoria")?.addEventListener("submit", salvaCategoria);

  await caricaCategorieCosto();
  renderTabellaCategorie();
}

function mostraFormCategoria(cat) {
  const wrapper = document.getElementById("cat-form-wrapper");
  wrapper.style.display = "block";
  if (cat) {
    document.getElementById("cat-id").value = cat.id;
    document.getElementById("cat-codice").value = cat.codice;
    document.getElementById("cat-nome").value = cat.nome;
    document.getElementById("cat-tipo").value = cat.tipo_costo;
  } else {
    document.getElementById("cat-id").value = "";
    document.getElementById("cat-codice").value = "";
    document.getElementById("cat-nome").value = "";
    document.getElementById("cat-tipo").value = "campagna";
  }
}

function nascondiFormCategoria() {
  document.getElementById("cat-form-wrapper").style.display = "none";
}

function renderTabellaCategorie() {
  const tbody = document.getElementById("categorie-tbody");
  if (!tbody) return;

  tbody.innerHTML = categorieCostoLista.map(c => `
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

function editCategoriaCosto(id) {
  const cat = categorieCostoLista.find(c => c.id === id);
  if (cat) mostraFormCategoria(cat);
}

async function toggleCategoriaCosto(id, nuovoStato) {
  try {
    await fetch(`${API_URL}/categorie-costo/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attiva: nuovoStato }),
    });
    await caricaCategorieCosto();
    renderTabellaCategorie();
  } catch (err) {
    console.error("Errore toggle categoria:", err);
  }
}

async function eliminaCategoriaCosto(id) {
  mostraConferma("Eliminare questa categoria?", async () => {
    try {
      const res = await fetch(`${API_URL}/categorie-costo/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Errore eliminazione.");
        return;
      }
      await caricaCategorieCosto();
      renderTabellaCategorie();
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
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Errore salvataggio.");
      return;
    }

    nascondiFormCategoria();
    await caricaCategorieCosto();
    renderTabellaCategorie();
  } catch (err) {
    console.error("Errore salvataggio categoria:", err);
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

  document.getElementById("menu-utenti")?.addEventListener("click", () => {
    setActiveMenu("menu-utenti");
    renderUtenti();
  });

  document.getElementById("menu-logout")?.addEventListener("click", logout);
});
