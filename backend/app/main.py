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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Routers
from app.routers.auth import router as auth_router
from app.routers.parcella import router as parcella_router
from app.api.v1.endpoints import users as users_router

# Database
from app.database import Base, engine


# ------------------------------------------------------------------------------
# Inizializzazione applicazione
# ------------------------------------------------------------------------------
app = FastAPI(
    title="GIAMS API",
    version="1.0.0",
    description="Green Integrated Agricultural Management System — Gia.Mar Green Farm"
)


# ------------------------------------------------------------------------------
# Configurazione CORS
# ------------------------------------------------------------------------------
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8003,http://127.0.0.1:8003").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Registrazione Routers
# ------------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api")
app.include_router(users_router.router, prefix="/api")
app.include_router(parcella_router, prefix="/api")


# ------------------------------------------------------------------------------
# Bootstrap Database (DEV ONLY)
# ------------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)


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
