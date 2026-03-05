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

## 🛠 Stack Tecnologico
- **Frontend**: HTML5 + CSS3 + JavaScript Vanilla
  - `index.html` → dashboard principale
  - `login.html` → autenticazione
  - `app.js` → logica applicativa principale
  - `styles.css` → stile globale
- **Backend**: Python
- **Deploy**: Render (`render.yaml`)
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

## 🔧 Comandi Utili
```bash
# Avviare il backend Python
cd backend && python app.py

# Installare dipendenze
pip install -r requirements.txt

# Deploy su Render
git push origin main   # il deploy è automatico via render.yaml
```

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
