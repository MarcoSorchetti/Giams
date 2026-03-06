"""
================================================================================
GIAMS — Green Integrated Agricultural Management System
File: main.py
Versione: 2.5.0
Autore: Team Gia.Mar Srl
Responsabile Progetto: Marco Sorchetti
================================================================================
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.security import get_current_user, get_current_admin

# Routers
from app.routers.auth import router as auth_router
from app.routers.parcella import router as parcella_router
from app.routers.raccolta import router as raccolta_router
from app.routers.lotto import router as lotto_router
from app.routers.confezionamento import router as confezionamento_router
from app.routers.contenitore import router as contenitore_router
from app.routers.cliente import router as cliente_router
from app.routers.fornitore import router as fornitore_router
from app.routers.categoria_costo import router as categoria_costo_router
from app.routers.costo import router as costo_router
from app.routers.magazzino import router as magazzino_router
from app.routers.causale_movimento import router as causale_movimento_router
from app.routers.vendita import router as vendita_router
from app.routers.campagna import router as campagna_router
from app.routers.audit import router as audit_router
from app.routers.tipo_documento import router as tipo_documento_router
from app.api.v1.endpoints import users as users_router

# Database
from app.database import Base, engine


# ------------------------------------------------------------------------------
# Inizializzazione applicazione
# ------------------------------------------------------------------------------
app = FastAPI(
    title="GIAMS API",
    version="2.11.1",
    description="Green Integrated Agricultural Management System — Gia.Mar Green Farm"
)


# ------------------------------------------------------------------------------
# Configurazione CORS
# ------------------------------------------------------------------------------
allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8003,http://127.0.0.1:8003").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ------------------------------------------------------------------------------
# Registrazione Routers
# ------------------------------------------------------------------------------
_protected = [Depends(get_current_user)]

# Auth — login NON protetto, /me protetto internamente
app.include_router(auth_router, prefix="/api")

# Tutti gli altri router richiedono JWT valido
app.include_router(users_router.router, prefix="/api", dependencies=[Depends(get_current_admin)])
app.include_router(parcella_router, prefix="/api", dependencies=_protected)
app.include_router(raccolta_router, prefix="/api", dependencies=_protected)
app.include_router(lotto_router, prefix="/api", dependencies=_protected)
app.include_router(confezionamento_router, prefix="/api", dependencies=_protected)
app.include_router(contenitore_router, prefix="/api", dependencies=_protected)
app.include_router(cliente_router, prefix="/api", dependencies=_protected)
app.include_router(fornitore_router, prefix="/api", dependencies=_protected)
app.include_router(categoria_costo_router, prefix="/api", dependencies=_protected)
app.include_router(costo_router, prefix="/api", dependencies=_protected)
app.include_router(magazzino_router, prefix="/api", dependencies=_protected)
app.include_router(causale_movimento_router, prefix="/api", dependencies=_protected)
app.include_router(vendita_router, prefix="/api", dependencies=_protected)
app.include_router(campagna_router, prefix="/api", dependencies=_protected)
app.include_router(audit_router, prefix="/api", dependencies=_protected)
app.include_router(tipo_documento_router, prefix="/api", dependencies=_protected)


# ------------------------------------------------------------------------------
# Bootstrap Database (DEV ONLY)
# ------------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# Seed categorie costo + causali movimento
from app.database import SessionLocal
from app.routers.categoria_costo import seed_categorie
from app.models.causale_movimento_sql import CausaleMovimento
from app.models.campagna_sql import Campagna
from app.models.tipo_documento_sql import TipoDocumento

def _seed_causali(db):
    """Popola le causali di default se la tabella e' vuota."""
    if db.query(CausaleMovimento).first():
        return
    defaults = [
        ("produzione", "Produzione", "carico", True),
        ("omaggio", "Omaggio / Degustazione", "scarico", False),
        ("pubblicita", "Pubblicita'", "scarico", False),
        ("scarto", "Scarto / Rottura", "scarico", False),
        ("vendita", "Vendita", "scarico", True),
    ]
    for codice, label, tipo, sistema in defaults:
        db.add(CausaleMovimento(codice=codice, label=label, tipo_movimento=tipo, sistema=sistema))
    db.commit()

def _seed_campagne(db):
    """Crea campagna 2025 se la tabella e' vuota."""
    if db.query(Campagna).first():
        return
    from datetime import date
    db.add(Campagna(anno=2025, stato="aperta", data_inizio=date(2025, 10, 1)))
    db.commit()

def _seed_tipi_documento(db):
    """Popola i tipi documento di default se la tabella e' vuota."""
    if db.query(TipoDocumento).first():
        return
    defaults = [
        ("fattura", "Fattura", True, 1),
        ("ricevuta", "Ricevuta", True, 2),
        ("nota_credito", "Nota di credito", True, 3),
        ("scontrino", "Scontrino", True, 4),
    ]
    for valore, etichetta, sistema, ordine in defaults:
        db.add(TipoDocumento(valore=valore, etichetta=etichetta, sistema=sistema, ordine=ordine))
    db.commit()

_db = SessionLocal()
try:
    seed_categorie(_db)
    _seed_causali(_db)
    _seed_campagne(_db)
    _seed_tipi_documento(_db)
finally:
    _db.close()


# ------------------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# Servire Frontend come file statici
# ------------------------------------------------------------------------------
# Upload directory (creata ma NON servita come static — accesso via endpoint protetti)
uploads_dir = os.path.join(os.path.dirname(__file__), "../../uploads")
os.makedirs(uploads_dir, exist_ok=True)

frontend_dir = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
