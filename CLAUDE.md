# GIAMS — Gia.Mar Green Farm Management System

## 🏢 Descrizione del Progetto
Piattaforma di gestione aziendale completa per **Gia.Mar Green Farm**, azienda agricola 
specializzata nella **produzione di olio d'oliva**. Il sistema digitalizza l'intera 
operatività aziendale: produzione, costi, fatturazione e gestione generale.

## 🌿 Dominio di Business
- **Core business**: Produzione e vendita olio d'oliva
- **Settore**: Agricoltura / Agroalimentare
- **Tipo**: Gestione aziendale integrata (ERP agricolo)
- **Moduli principali**:
  - Gestione produzione (raccolta olive, spremitura, imbottigliamento)
  - Gestione costi (spese operative, macchinari, manodopera)
  - Fatturazione (clienti, fornitori, DDT)
  - Gestione magazzino (scorte olio, bottiglie, materiali)
  - Reportistica aziendale
  - Mappa aziendale interattiva (parcelle, infrastrutture, strade)

## 🛠 Stack Tecnologico
- **Frontend**: HTML5 + CSS3 + JavaScript Vanilla + Bootstrap 5 (dark theme)
  - `index.html` → dashboard principale (SPA)
  - `login.html` → autenticazione
  - `app.js` → logica applicativa principale (~7200 righe)
  - `styles.css` → stile globale (variabili CSS, tema scuro verde)
  - Servito come file statici da FastAPI (non ha un server separato)
  - **Leaflet.js** v1.9.4 (via CDN unpkg) per mappa interattiva aziendale
- **Backend**: FastAPI + SQLAlchemy + Alembic (Python 3.12)
  - Auth: JWT (python-jose) con `apiFetch()` lato frontend
  - PDF: fpdf2 (Helvetica, no Unicode — evitare em-dash e caratteri speciali)
  - Porta: **8003**
- **Database**: PostgreSQL 15 (Homebrew) — LOCALE
  - DB: `giams_db` | User: `giams_user` | Password: `password_sicura`
  - Connection string default in `backend/app/database.py`
- **Ambiente**: Sviluppo locale (NO Render, NO cloud per ora)
  - Virtualenv: `.venv/` (Python 3.12 via Homebrew)
  - Il frontend e' servito da FastAPI come StaticFiles sulla stessa porta 8003
- **Cartella upload**: `uploads/` per documenti e allegati
- **Documentazione progetto**: `Progetto/`

## 📁 Struttura del Progetto
```
GIAMS/
├── .claude/          # Configurazione Claude Code
├── backend/          # Server Python, API, logica business
├── frontend/         # Interfaccia utente
│   ├── assets/       # Immagini, icone, font
│   ├── app.js        # Logica JS principale
│   ├── index.html    # Dashboard
│   ├── login.html    # Login
│   └── styles.css    # Stili globali
├── Progetto/         # Documentazione e specifiche
├── uploads/          # File caricati dagli utenti
├── render.yaml       # Configurazione deploy Render
└── requirements.txt  # Dipendenze Python
```

## 💻 Convenzioni di Codice

### JavaScript (Frontend)
- Usa **JavaScript Vanilla** — niente framework esterni salvo diversa indicazione
- Preferisci `async/await` a `.then()`
- Variabili e funzioni in **camelCase** (`calcolaCosteOlio`, `getProduzioneAnnuale`)
- Costanti in **UPPER_SNAKE_CASE** (`MAX_CAPACITA_SERBATOIO`)
- Commenti sempre in **italiano**
- Ogni funzione deve avere un commento descrittivo sopra

### Python (Backend)
- Segui **PEP 8**
- Nomi funzioni e variabili in **snake_case** (`calcola_costo_produzione`)
- Classi in **PascalCase** (`GestioneMagazzino`)
- Docstring su ogni funzione
- Commenti in **italiano**

### HTML/CSS
- Classi CSS in **kebab-case** (`btn-salva-fattura`, `card-produzione`)
- ID in **camelCase** (`formNuovaFattura`)
- Usa variabili CSS per colori e spaziature

## 🌱 Terminologia del Dominio
Usa sempre questa terminologia nei nomi di variabili, funzioni e commenti:
- `olive` → materia prima
- `spremitura` / `frangitura` → processo di produzione
- `olio` → prodotto finito
- `lotto` → batch di produzione
- `resa` → percentuale olio ottenuto dalle olive (es. 18%)
- `DOP` / `IGP` → certificazioni qualità
- `DDT` → documento di trasporto
- `campagna` → stagione produttiva annuale (es. "campagna 2024/2025")
- `frantoio` → impianto di lavorazione
- `cultivar` → varietà di olivo (es. Leccino, Frantoio, Moraiolo)

## 🔧 Ambiente Locale — Avvio Completo

### Prerequisiti
- **PostgreSQL 15** (Homebrew): `brew services start postgresql@15`
- **Python 3.12** (Homebrew): `/opt/homebrew/bin/python3.12`
- **Virtualenv**: `.venv/` nella root del progetto

### 1. Avviare PostgreSQL (se non attivo)
```bash
brew services start postgresql@15
# Verifica: pg_isready  →  deve rispondere "accepting connections"
```

### 2. Attivare il virtualenv e avviare il backend
```bash
source /Users/marcos.orchetti/giams/.venv/bin/activate
cd /Users/marcos.orchetti/giams/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 3. Aprire l'applicazione
- **Frontend + Backend**: http://localhost:8003
- **API docs (Swagger)**: http://localhost:8003/docs

### Installare/aggiornare dipendenze
```bash
source /Users/marcos.orchetti/giams/.venv/bin/activate
pip install -r /Users/marcos.orchetti/giams/requirements.txt
```

### Comandi utili
```bash
# Stato PostgreSQL
brew services list | grep postgres

# Verificare che il server sia attivo
curl -s http://localhost:8003/health

# Migrazioni Alembic
cd backend && alembic upgrade head

# Push su GitHub
git push origin main
```

## 🗺 Mappa Aziendale (Leaflet.js)
- **Libreria**: Leaflet.js v1.9.4 caricato via CDN (unpkg) in `index.html`
- **Tile layers**: Esri satellite (default) + OpenStreetMap (toggle)
- **Dati poligoni**: definiti staticamente in `app.js` nell'array `MAPPA_ZONE`
  - Coordinate estratte da file KML (Google Earth) e convertite in formato `[lat, lng]`
  - 11 zone totali: 6 oliveti (P001-P006), 3 edifici, 2 strade
- **Layer groups**: Oliveti, Infrastrutture, Strade — toggle indipendente
- **Integrazione DB**: le parcelle (P001-P006) sono nella tabella `parcelle`, la mappa carica i dati via API `/api/parcelle/` per le stat cards
- **Stili dark theme**: popup, tooltip, zoom controls e attribution stilizzati in `styles.css`
- **Funzione principale**: `renderMappa()` in `app.js`
- **Colori zone**: definiti in `MAPPA_COLORI` (verde oliveti, grigio edifici, marrone strade)

## ⚠️ Regole Importanti
- **VERSIONING OBBLIGATORIO**: Dopo OGNI modifica al codice, aggiornare SEMPRE la versione in TUTTI e 3 i file:
  1. `frontend/version.json` → `"version": "X.Y.Z"`
  2. `frontend/index.html` → sidebar `<div class="app-version">vX.Y.Z</div>`
  3. `backend/app/main.py` → `version="X.Y.Z"`
  Questo e' l'ULTIMO step di ogni task. Non dimenticarlo MAI.
- **Paginazione**: sempre 10 righe per pagina (`per_page=10`) sia backend che frontend.
- **Non toccare mai** `render.yaml` senza conferma esplicita
- I file in `uploads/` possono contenere dati sensibili aziendali — gestire con cura
- La fatturazione deve rispettare le normative fiscali italiane (IVA, fattura elettronica)
- Per calcoli di produzione, la **resa** è sempre espressa in percentuale sul peso olive
- I prezzi sono sempre in **Euro (€)**, con 2 decimali
- Le date seguono il formato **italiano**: GG/MM/AAAA

## 🎯 Priorità di Sviluppo
Quando suggerisci soluzioni, considera in quest'ordine:
1. **Semplicità** — meno codice, più manutenibile
2. **Affidabilità** — i dati aziendali non devono mai andare persi
3. **Usabilità** — l'utente finale non è un tecnico informatico
4. **Performance** — ottimizza solo se necessario
