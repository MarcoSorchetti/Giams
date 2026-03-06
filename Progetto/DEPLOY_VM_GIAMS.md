# GIAMS — Documento di Deploy su Macchina Virtuale
# Specifica Tecnica per Sistemisti

**Progetto:** GIAMS — Green Integrated Agricultural Management System
**Versione:** 2.10.0
**Data:** 06/03/2026
**Destinatari:** Team Sistemisti — preparazione VM per ambiente di produzione


---

## 0. DEPLOY RAPIDO (TUTTO AUTOMATICO)

Se la VM ha Ubuntu Server 22.04/24.04 LTS gia' installato con accesso SSH:

### Passo 1 — I sistemisti preparano la VM

Serve solo Ubuntu Server con SSH. Nient'altro. Lo script fa tutto il resto.

### Passo 2 — Clonare il repository e lanciare lo script

```bash
# Sulla VM, come root o con sudo:
git clone https://github.com/MarcoSorchetti/Giams.git /opt/giams
cd /opt/giams/Progetto
sudo bash setup_vm.sh giams.VOSTRODOMINIO.it PASSWORD_DATABASE_SICURA
```

Lo script `setup_vm.sh` installa e configura **tutto automaticamente**:
- PostgreSQL 15 + creazione database e utente
- Python 3.12 + virtualenv + dipendenze
- Importazione database completo (dump incluso nel repo: `Progetto/giams_db.dump`)
- Avvio applicazione come servizio systemd (auto-restart)
- Nginx reverse proxy
- Firewall UFW
- Backup automatico giornaliero (cron)

### Passo 3 — SSL e DNS

```bash
# 1. Configurare il record DNS A: giams.VOSTRODOMINIO.it -> IP della VM
# 2. Una volta propagato il DNS, installare il certificato SSL:
sudo certbot --nginx -d giams.VOSTRODOMINIO.it
```

### Cosa c'e' nel repository GitHub

| Elemento                    | Descrizione                              |
|-----------------------------|------------------------------------------|
| `backend/`                  | Codice server Python (FastAPI)           |
| `frontend/`                 | Interfaccia web (HTML/JS/CSS)            |
| `requirements.txt`          | Dipendenze Python                        |
| `Progetto/giams_db.dump`    | **Dump completo del database** (87 KB)   |
| `Progetto/setup_vm.sh`      | **Script di setup automatico**           |
| `Progetto/DEPLOY_VM_GIAMS.md` | Questo documento                      |
| `uploads/`                  | Cartella documenti allegati              |

> **Il database e' incluso nel repository come file dump PostgreSQL.**
> Lo script lo importa automaticamente. Non serve ricreare nulla a mano.

---

Di seguito il dettaglio completo per chi vuole capire cosa fa lo script o procedere manualmente.

---

## 1. SPECIFICHE MACCHINA VIRTUALE

### 1.1 Requisiti Minimi

| Risorsa         | Minimo          | Consigliato      | Note                                    |
|-----------------|-----------------|------------------|-----------------------------------------|
| **vCPU**        | 2 core          | 4 core           | Il backend e' single-thread, PostgreSQL beneficia di core aggiuntivi |
| **RAM**         | 2 GB            | 4 GB             | PostgreSQL usa ~256 MB, Python ~200 MB  |
| **Disco**       | 20 GB SSD       | 40 GB SSD        | DB attuale ~10 MB, crescita stimata 1-2 GB/anno con upload documenti |
| **Rete**        | 100 Mbps        | 1 Gbps           | Traffico leggero (5-10 utenti concorrenti) |
| **IP Pubblico**  | Si (1 IPv4)     | Si (IPv4 + IPv6) | Necessario per accesso da internet      |

### 1.2 Sistema Operativo

| Parametro       | Valore                                |
|-----------------|---------------------------------------|
| **OS**          | Ubuntu Server 22.04 LTS (o 24.04 LTS) |
| **Architettura**| x86_64 (amd64)                        |
| **Interfaccia** | Solo CLI (no desktop environment)     |
| **Accesso**     | SSH (porta 22) con chiave pubblica    |

> Alternativa accettabile: Debian 12, Rocky Linux 9, AlmaLinux 9


---

## 2. SOFTWARE E SERVIZI DA INSTALLARE

### 2.1 Riepilogo Servizi

| Servizio         | Versione  | Porta | Descrizione                          |
|------------------|-----------|-------|--------------------------------------|
| **PostgreSQL**   | 15 o 16  | 5432  | Database relazionale (solo localhost) |
| **Python**       | 3.12.x   | —     | Runtime applicazione backend         |
| **Uvicorn**      | 0.38+    | 8003  | ASGI server (gestito da systemd)     |
| **Nginx**        | latest    | 80/443| Reverse proxy + SSL termination      |
| **Certbot**      | latest    | —     | Certificati SSL Let's Encrypt        |
| **UFW**          | preinstallato | — | Firewall                             |

### 2.2 Installazione Step-by-Step

```bash
# ============================================================
# STEP 1: Aggiornamento sistema
# ============================================================
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip software-properties-common

# ============================================================
# STEP 2: PostgreSQL 15
# ============================================================
sudo apt install -y postgresql-15 postgresql-client-15

# Verifica
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "SELECT version();"

# ============================================================
# STEP 3: Python 3.12
# ============================================================
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Verifica
python3.12 --version

# ============================================================
# STEP 4: Nginx
# ============================================================
sudo apt install -y nginx

sudo systemctl enable nginx
sudo systemctl start nginx

# ============================================================
# STEP 5: Certbot (SSL Let's Encrypt)
# ============================================================
sudo apt install -y certbot python3-certbot-nginx

# ============================================================
# STEP 6: Firewall
# ============================================================
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```


---

## 3. CONFIGURAZIONE DATABASE

### 3.1 Creazione Database e Utente

```bash
sudo -u postgres psql << 'SQL'
-- Crea utente applicativo
CREATE USER giams_user WITH PASSWORD 'CAMBIARE_CON_PASSWORD_SICURA';

-- Crea database
CREATE DATABASE giams_db OWNER giams_user ENCODING 'UTF8' LC_COLLATE 'it_IT.UTF-8' LC_CTYPE 'it_IT.UTF-8' TEMPLATE template0;

-- Permessi
GRANT ALL PRIVILEGES ON DATABASE giams_db TO giams_user;
\c giams_db
GRANT ALL ON SCHEMA public TO giams_user;
SQL
```

> **IMPORTANTE:** Sostituire `CAMBIARE_CON_PASSWORD_SICURA` con una password robusta (almeno 16 caratteri, lettere, numeri, simboli).

### 3.2 Configurazione PostgreSQL per Sicurezza

Modificare `/etc/postgresql/15/main/pg_hba.conf`:
```
# Solo connessioni locali per giams_user
local   giams_db    giams_user                          md5
host    giams_db    giams_user    127.0.0.1/32          md5
```

Modificare `/etc/postgresql/15/main/postgresql.conf`:
```
listen_addresses = 'localhost'    # NON esporre su rete
max_connections = 50
shared_buffers = 256MB
work_mem = 4MB
```

```bash
sudo systemctl restart postgresql
```


---

## 4. DEPLOY APPLICAZIONE

### 4.1 Utente di Sistema Dedicato

```bash
# Crea utente applicativo (senza login interattivo)
sudo useradd -m -s /bin/bash giams
sudo mkdir -p /opt/giams
sudo chown giams:giams /opt/giams
```

### 4.2 Trasferimento Codice

**Dal computer di sviluppo**, eseguire:

```bash
# Opzione A: Da Git (consigliato)
sudo -u giams git clone https://github.com/MarcoSorchetti/Giams.git /opt/giams

# Opzione B: Copia manuale via SCP
scp -r ./giams/* utente@IP_SERVER:/opt/giams/
sudo chown -R giams:giams /opt/giams
```

### 4.3 Setup Ambiente Python

```bash
sudo -u giams bash << 'EOF'
cd /opt/giams

# Crea virtual environment
python3.12 -m venv .venv

# Attiva e installa dipendenze
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Dipendenze aggiuntive per produzione
pip install python-jose[cryptography] fpdf2 pillow gunicorn
EOF
```

### 4.4 File di Configurazione Ambiente

Creare il file `/opt/giams/backend/.env`:

```bash
sudo -u giams cat > /opt/giams/backend/.env << 'EOF'
# Database
DATABASE_URL=postgresql://giams_user:CAMBIARE_CON_PASSWORD_SICURA@localhost:5432/giams_db

# JWT Secret (generare con: python3 -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=GENERARE_UNA_CHIAVE_SEGRETA_LUNGA_QUI

# Origini consentite (inserire il dominio reale)
ALLOWED_ORIGINS=https://giams.tuodominio.it,https://www.giams.tuodominio.it

# Ambiente
ENV=production
EOF

# Proteggere il file
sudo chmod 600 /opt/giams/backend/.env
sudo chown giams:giams /opt/giams/backend/.env
```

### 4.5 Cartella Upload

```bash
sudo -u giams mkdir -p /opt/giams/uploads/costi
sudo chmod 750 /opt/giams/uploads
```

### 4.6 Migrazioni Database

```bash
sudo -u giams bash << 'EOF'
cd /opt/giams/backend
source /opt/giams/.venv/bin/activate
alembic upgrade head
EOF
```

> Se le migrazioni Alembic non sono aggiornate, l'applicazione creera' le tabelle automaticamente al primo avvio (`Base.metadata.create_all`).


---

## 5. MIGRAZIONE DATABASE ATTUALE

Per trasferire il database dal computer di sviluppo alla VM:

### 5.1 Export dal Computer di Sviluppo (Mac)

```bash
# Sul Mac di sviluppo
pg_dump -U giams_user -h localhost -d giams_db \
    --no-owner --no-privileges \
    -F c -f /tmp/giams_db_backup.dump

# Dimensione attuale: ~10 MB
```

### 5.2 Trasferimento alla VM

```bash
# Dal Mac
scp /tmp/giams_db_backup.dump utente@IP_SERVER:/tmp/
```

### 5.3 Import sulla VM

```bash
# Sulla VM
sudo -u postgres pg_restore \
    -d giams_db \
    --no-owner --role=giams_user \
    --clean --if-exists \
    /tmp/giams_db_backup.dump

# Verifica
sudo -u postgres psql -d giams_db -c "\dt"
sudo -u postgres psql -d giams_db -c "SELECT count(*) FROM users;"

# Pulizia
rm /tmp/giams_db_backup.dump
```


---

## 6. SERVIZIO SYSTEMD (AVVIO AUTOMATICO)

### 6.1 Creare il Service

```bash
sudo cat > /etc/systemd/system/giams.service << 'EOF'
[Unit]
Description=GIAMS — Green Integrated Agricultural Management System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=giams
Group=giams
WorkingDirectory=/opt/giams/backend
Environment=PATH=/opt/giams/.venv/bin:/usr/bin
EnvironmentFile=/opt/giams/backend/.env
ExecStart=/opt/giams/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8003 \
    --workers 2 \
    --log-level warning
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Sicurezza
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/giams/uploads
ReadOnlyPaths=/opt/giams

[Install]
WantedBy=multi-user.target
EOF
```

### 6.2 Abilitare e Avviare

```bash
sudo systemctl daemon-reload
sudo systemctl enable giams
sudo systemctl start giams

# Verifica
sudo systemctl status giams
curl -s http://127.0.0.1:8003/health
# Deve rispondere: {"status":"ok"}
```

### 6.3 Comandi Utili

```bash
sudo systemctl start giams      # Avvia
sudo systemctl stop giams       # Ferma
sudo systemctl restart giams    # Riavvia
sudo journalctl -u giams -f     # Log in tempo reale
sudo journalctl -u giams --since "1 hour ago"  # Log ultima ora
```


---

## 7. CONFIGURAZIONE NGINX (REVERSE PROXY + SSL)

### 7.1 Virtual Host

```bash
sudo cat > /etc/nginx/sites-available/giams << 'NGINX'
server {
    listen 80;
    server_name giams.tuodominio.it;

    # Redirect HTTP -> HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name giams.tuodominio.it;

    # SSL (gestito da Certbot, vedi step successivo)
    # ssl_certificate ...
    # ssl_certificate_key ...

    # Sicurezza headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;

    # Limiti upload (per file Excel e documenti allegati)
    client_max_body_size 20M;

    # Proxy verso Uvicorn
    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (per eventuali sviluppi futuri)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 60s;
    }
}
NGINX

# Attiva il sito
sudo ln -s /etc/nginx/sites-available/giams /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test e ricarica
sudo nginx -t
sudo systemctl reload nginx
```

### 7.2 Certificato SSL con Let's Encrypt

```bash
# Prerequisito: il dominio deve puntare all'IP della VM (record DNS A)
sudo certbot --nginx -d giams.tuodominio.it

# Rinnovo automatico (gia' configurato da certbot, verificare)
sudo certbot renew --dry-run
```

> **PRIMA di eseguire certbot:** il record DNS `A` per `giams.tuodominio.it` deve puntare all'IP pubblico della VM.


---

## 8. SCHEMA DI RETE

```
Internet
   |
   | (HTTPS :443)
   v
[Firewall UFW]  ---- Porte aperte: 22 (SSH), 80 (redirect), 443 (HTTPS)
   |
   v
[Nginx :80/:443]  ---- Reverse proxy + SSL termination
   |
   | (HTTP :8003, solo localhost)
   v
[Uvicorn/FastAPI]  ---- Applicazione GIAMS (2 workers)
   |
   | (TCP :5432, solo localhost)
   v
[PostgreSQL]  ---- Database giams_db
```

**Porte esposte su internet:** Solo 22 (SSH), 80 (redirect a HTTPS), 443 (HTTPS)
**Porte interne (localhost only):** 8003 (app), 5432 (database)


---

## 9. TABELLE DATABASE (20 tabelle)

| # | Tabella                | Descrizione                              |
|---|------------------------|------------------------------------------|
| 1 | users                  | Utenti della piattaforma (admin, operatori) |
| 2 | audit_log              | Log operazioni utente                    |
| 3 | parcelle               | Terreni e oliveti                        |
| 4 | raccolte               | Sessioni di raccolta olive               |
| 5 | raccolta_parcelle      | Associazione raccolta-parcella           |
| 6 | lotti_olio             | Lotti di produzione olio                 |
| 7 | confezionamenti        | Formati di confezionamento (bottiglie)   |
| 8 | confezionamento_lotti  | Associazione confezionamento-lotto       |
| 9 | contenitori            | Tipologie di contenitore                 |
| 10| clienti                | Anagrafica clienti                       |
| 11| fornitori              | Anagrafica fornitori                     |
| 12| vendite                | Fatture e DDT                            |
| 13| vendita_righe          | Righe dettaglio vendita                  |
| 14| categorie_costo        | Categorie spese (campagna/strutturale)   |
| 15| costi                  | Fatture passive e spese                  |
| 16| tipi_documento         | Lookup tipi documento (fattura, ricevuta)|
| 17| causali_movimento      | Causali movimenti magazzino              |
| 18| movimenti_magazzino    | Carichi e scarichi magazzino             |
| 19| campagne               | Stagioni produttive                      |
| 20| alembic_version        | Versione migrazioni DB                   |


---

## 10. CHECKLIST POST-INSTALLAZIONE

Prima di rendere il sistema accessibile:

- [ ] VM avviata e accessibile via SSH
- [ ] PostgreSQL attivo e database `giams_db` creato
- [ ] Utente `giams_user` con password sicura
- [ ] Database migrato (dump importato o tabelle create)
- [ ] Python 3.12 installato con virtualenv
- [ ] Dipendenze Python installate (`pip install -r requirements.txt`)
- [ ] File `.env` creato con password DB e SECRET_KEY
- [ ] Servizio `giams.service` attivo (`systemctl status giams`)
- [ ] `curl http://127.0.0.1:8003/health` risponde `{"status":"ok"}`
- [ ] Nginx configurato come reverse proxy
- [ ] DNS: record A puntato all'IP della VM
- [ ] Certificato SSL installato (certbot)
- [ ] `https://giams.tuodominio.it` risponde correttamente
- [ ] Login con utente admin funzionante
- [ ] Firewall UFW attivo (solo porte 22, 80, 443)
- [ ] Backup automatico database configurato (vedi sezione 11)


---

## 11. BACKUP AUTOMATICO (CONSIGLIATO)

### 11.1 Script di Backup

```bash
sudo cat > /opt/giams/backup.sh << 'SCRIPT'
#!/bin/bash
# Backup database GIAMS
BACKUP_DIR="/opt/giams/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

pg_dump -U giams_user -h localhost giams_db \
    -F c -f "$BACKUP_DIR/giams_db_$TIMESTAMP.dump"

# Backup cartella uploads
tar czf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" -C /opt/giams uploads/

# Mantieni solo ultimi 30 giorni
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] Backup completato: giams_db_$TIMESTAMP.dump"
SCRIPT

sudo chmod +x /opt/giams/backup.sh
sudo chown giams:giams /opt/giams/backup.sh
```

### 11.2 Cron Job (backup giornaliero ore 3:00)

```bash
sudo -u giams crontab -e
# Aggiungere:
0 3 * * * /opt/giams/backup.sh >> /opt/giams/backups/backup.log 2>&1
```


---

## 12. AGGIORNAMENTO APPLICAZIONE

Procedura per aggiornare GIAMS a una nuova versione:

```bash
# 1. Backup prima dell'aggiornamento
sudo -u giams /opt/giams/backup.sh

# 2. Aggiorna il codice
cd /opt/giams
sudo -u giams git pull origin main

# 3. Aggiorna dipendenze
sudo -u giams bash -c "source .venv/bin/activate && pip install -r requirements.txt"

# 4. Esegui migrazioni DB (se presenti)
sudo -u giams bash -c "cd backend && source /opt/giams/.venv/bin/activate && alembic upgrade head"

# 5. Riavvia il servizio
sudo systemctl restart giams

# 6. Verifica
curl -s http://127.0.0.1:8003/health
sudo systemctl status giams
```


---

## 13. CONTATTI E RIFERIMENTI

| Ruolo                  | Contatto               |
|------------------------|------------------------|
| Responsabile Progetto  | Marco Sorchetti        |
| Repository GitHub      | github.com/MarcoSorchetti/Giams |
| Documentazione API     | https://giams.tuodominio.it/docs |

---

*Documento generato automaticamente da GIAMS v2.10.0*
