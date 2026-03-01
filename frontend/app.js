/**
 * GIAMS — Green Integrated Agricultural Management System
 * app.js — Logica frontend SPA
 */

const API_URL = "/api";

// ---- Stato globale ----
let parcelleLista = [];
let parcellaInModifica = null;
let utenteInModifica = null;

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
      <h1 class="home-greeting mb-2">GIAMS</h1>
      <p class="home-subtitle mb-2">Gia.Mar Green Farm — Gestione Agricola</p>
      <div class="home-logo-icon mb-3">🌿</div>
      <p class="home-greeting-user mb-4">Benvenuto, <span>${userName}</span> &middot; Ver. ${version}</p>

      <div class="row g-3 w-100" style="max-width:500px;">
        <div class="col-6">
          <div class="quick-card" id="quick-parcelle">
            <div class="quick-card-icon"><i class="fa-solid fa-seedling"></i></div>
            <div class="quick-card-title">Gestione Parcelle</div>
            <div class="quick-card-desc">Terreni e oliveti</div>
          </div>
        </div>
        <div class="col-6">
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

  document.getElementById("menu-utenti")?.addEventListener("click", () => {
    setActiveMenu("menu-utenti");
    renderUtenti();
  });

  document.getElementById("menu-logout")?.addEventListener("click", logout);
});
