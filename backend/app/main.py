"""
================================================================================
GIAMS — Green Integrated Agricultural Management System
File: main.py
Versione: 1.0.0
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
from app.routers.vendita import router as vendita_router
from app.api.v1.endpoints import users as users_router

# Database
from app.database import Base, engine


# ------------------------------------------------------------------------------
# Inizializzazione applicazione
# ------------------------------------------------------------------------------
app = FastAPI(
    title="GIAMS API",
    version="1.4.21",
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
    allow_headers=["*"],
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
app.include_router(vendita_router, prefix="/api", dependencies=_protected)


# ------------------------------------------------------------------------------
# Bootstrap Database (DEV ONLY)
# ------------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# Seed categorie costo
from app.database import SessionLocal
from app.routers.categoria_costo import seed_categorie
_db = SessionLocal()
try:
    seed_categorie(_db)
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
uploads_dir = os.path.join(os.path.dirname(__file__), "../../uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

frontend_dir = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
