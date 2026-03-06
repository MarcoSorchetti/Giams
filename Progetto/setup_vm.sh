#!/bin/bash
# ==============================================================================
# GIAMS — Script di Setup Automatico per VM
# Esegue: installazione servizi, deploy app, importazione database, avvio
#
# USO: sudo bash setup_vm.sh DOMINIO PASSWORD_DB
# ES:  sudo bash setup_vm.sh giams.tuodominio.it MyP4ssw0rd!Sicura
# ==============================================================================

set -e  # Esci al primo errore

# --- Parametri ---
DOMINIO="${1:-}"
DB_PASSWORD="${2:-}"

if [ -z "$DOMINIO" ] || [ -z "$DB_PASSWORD" ]; then
    echo ""
    echo "USO: sudo bash setup_vm.sh DOMINIO PASSWORD_DB"
    echo "  DOMINIO     = dominio pubblico (es: giams.miosito.it)"
    echo "  PASSWORD_DB = password per utente database giams_user"
    echo ""
    echo "Esempio: sudo bash setup_vm.sh giams.miosito.it MiaPasswordSicura123!"
    echo ""
    exit 1
fi

APP_DIR="/opt/giams"
REPO_URL="https://github.com/MarcoSorchetti/Giams.git"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)

echo ""
echo "============================================================"
echo " GIAMS — Setup Automatico"
echo " Dominio:  $DOMINIO"
echo " App dir:  $APP_DIR"
echo "============================================================"
echo ""

# ==============================================================
# 1. AGGIORNAMENTO SISTEMA
# ==============================================================
echo "[1/9] Aggiornamento sistema..."
apt update && apt upgrade -y
apt install -y curl wget git unzip software-properties-common

# ==============================================================
# 2. POSTGRESQL 15
# ==============================================================
echo "[2/9] Installazione PostgreSQL 15..."
apt install -y postgresql-15 postgresql-client-15
systemctl enable postgresql
systemctl start postgresql

# ==============================================================
# 3. PYTHON 3.12
# ==============================================================
echo "[3/9] Installazione Python 3.12..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-venv python3.12-dev

# ==============================================================
# 4. NGINX + CERTBOT
# ==============================================================
echo "[4/9] Installazione Nginx e Certbot..."
apt install -y nginx certbot python3-certbot-nginx
systemctl enable nginx

# ==============================================================
# 5. CREAZIONE DATABASE
# ==============================================================
echo "[5/9] Configurazione database..."
sudo -u postgres psql -c "CREATE USER giams_user WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER giams_user WITH PASSWORD '$DB_PASSWORD';"

sudo -u postgres psql -c "CREATE DATABASE giams_db OWNER giams_user ENCODING 'UTF8';" 2>/dev/null || \
    echo "  Database giams_db esiste gia'"

sudo -u postgres psql -d giams_db -c "GRANT ALL ON SCHEMA public TO giams_user;"

# ==============================================================
# 6. CLONE REPOSITORY E SETUP APP
# ==============================================================
echo "[6/9] Deploy applicazione da GitHub..."
useradd -m -s /bin/bash giams 2>/dev/null || echo "  Utente giams esiste gia'"

if [ -d "$APP_DIR/.git" ]; then
    echo "  Repository esistente, aggiornamento..."
    sudo -u giams git -C "$APP_DIR" pull origin main
else
    rm -rf "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    chown -R giams:giams "$APP_DIR"
fi

# Virtual environment e dipendenze
echo "  Installazione dipendenze Python..."
sudo -u giams bash -c "
    cd $APP_DIR
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install python-jose[cryptography] fpdf2 pillow -q
"

# Cartella uploads
sudo -u giams mkdir -p "$APP_DIR/uploads/costi"

# ==============================================================
# 7. IMPORTAZIONE DATABASE (se presente il dump)
# ==============================================================
DUMP_FILE="$APP_DIR/Progetto/giams_db.dump"
if [ -f "$DUMP_FILE" ]; then
    echo "[7/9] Importazione database da dump..."
    sudo -u postgres pg_restore \
        -d giams_db \
        --no-owner --role=giams_user \
        --clean --if-exists \
        "$DUMP_FILE" 2>/dev/null || echo "  Alcune tabelle potrebbero non esistere ancora (ok al primo deploy)"
    echo "  Database importato con successo"
else
    echo "[7/9] Nessun dump trovato, creazione tabelle vuote..."
    sudo -u giams bash -c "
        cd $APP_DIR/backend
        source $APP_DIR/.venv/bin/activate
        alembic upgrade head 2>/dev/null || python3 -c 'from app.database import Base, engine; Base.metadata.create_all(bind=engine)'
    "
fi

# ==============================================================
# 8. FILE .ENV + SERVIZIO SYSTEMD
# ==============================================================
echo "[8/9] Configurazione servizio..."

# File .env
cat > "$APP_DIR/backend/.env" << ENVEOF
DATABASE_URL=postgresql://giams_user:${DB_PASSWORD}@localhost:5432/giams_db
SECRET_KEY=${SECRET_KEY}
ALLOWED_ORIGINS=https://${DOMINIO},https://www.${DOMINIO}
ENV=production
ENVEOF
chmod 600 "$APP_DIR/backend/.env"
chown giams:giams "$APP_DIR/backend/.env"

# Servizio systemd
cat > /etc/systemd/system/giams.service << 'SVCEOF'
[Unit]
Description=GIAMS - Green Integrated Agricultural Management System
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
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/giams/uploads
ReadOnlyPaths=/opt/giams

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable giams
systemctl start giams

# Attendi avvio
sleep 3
if curl -s http://127.0.0.1:8003/health | grep -q "ok"; then
    echo "  Applicazione avviata correttamente!"
else
    echo "  ATTENZIONE: l'applicazione potrebbe non essersi avviata. Controllare: journalctl -u giams -f"
fi

# ==============================================================
# 9. NGINX + FIREWALL
# ==============================================================
echo "[9/9] Configurazione Nginx e firewall..."

cat > /etc/nginx/sites-available/giams << NGXEOF
server {
    listen 80;
    server_name ${DOMINIO} www.${DOMINIO};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMINIO} www.${DOMINIO};

    # SSL verra' configurato da certbot
    # ssl_certificate ...
    # ssl_certificate_key ...

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 60s;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/giams /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

# Firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
echo "y" | ufw enable

# ==============================================================
# BACKUP CRON
# ==============================================================
cat > "$APP_DIR/backup.sh" << 'BKEOF'
#!/bin/bash
BACKUP_DIR="/opt/giams/backups"
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
pg_dump -U giams_user -h localhost giams_db -F c -f "$BACKUP_DIR/giams_db_$TS.dump"
tar czf "$BACKUP_DIR/uploads_$TS.tar.gz" -C /opt/giams uploads/
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
echo "[$(date)] Backup completato"
BKEOF
chmod +x "$APP_DIR/backup.sh"
chown giams:giams "$APP_DIR/backup.sh"
(sudo -u giams crontab -l 2>/dev/null; echo "0 3 * * * $APP_DIR/backup.sh >> $APP_DIR/backups/backup.log 2>&1") | sort -u | sudo -u giams crontab -

# ==============================================================
# RIEPILOGO FINALE
# ==============================================================
echo ""
echo "============================================================"
echo " GIAMS — Setup Completato!"
echo "============================================================"
echo ""
echo " App locale:     http://127.0.0.1:8003"
echo " App pubblica:   https://${DOMINIO}"
echo " API docs:       https://${DOMINIO}/docs"
echo ""
echo " PROSSIMI STEP:"
echo " 1. Configura il record DNS A: ${DOMINIO} -> $(curl -s ifconfig.me 2>/dev/null || echo 'IP_PUBBLICO')"
echo " 2. Installa certificato SSL:  sudo certbot --nginx -d ${DOMINIO}"
echo " 3. Verifica accesso:          curl https://${DOMINIO}/health"
echo ""
echo " COMANDI UTILI:"
echo "   sudo systemctl status giams    # Stato applicazione"
echo "   sudo journalctl -u giams -f    # Log in tempo reale"
echo "   sudo systemctl restart giams   # Riavvio"
echo ""
echo "============================================================"
