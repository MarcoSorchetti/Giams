import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_sql import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
)
from app.services.audit import log_audit


router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Rate limiting in-memory per login
# ---------------------------------------------------------------------------
_MAX_ATTEMPTS = 5          # tentativi massimi per IP
_WINDOW_SECONDS = 300      # finestra di 5 minuti
_BLOCK_SECONDS = 900       # blocco per 15 minuti dopo troppi tentativi

_login_attempts: dict[str, list[float]] = defaultdict(list)
_blocked_until: dict[str, float] = {}


def _check_rate_limit(ip: str):
    now = time.time()

    # Se l'IP e' bloccato, verifica se il blocco e' scaduto
    if ip in _blocked_until:
        if now < _blocked_until[ip]:
            remaining = int(_blocked_until[ip] - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Troppi tentativi. Riprova tra {remaining} secondi.",
            )
        del _blocked_until[ip]
        _login_attempts[ip].clear()

    # Pulisci tentativi vecchi (fuori dalla finestra)
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECONDS]

    if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
        _blocked_until[ip] = now + _BLOCK_SECONDS
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Troppi tentativi. Riprova tra {_BLOCK_SECONDS // 60} minuti.",
        )


def _record_failed_attempt(ip: str):
    _login_attempts[ip].append(time.time())


def _clear_attempts(ip: str):
    _login_attempts.pop(ip, None)
    _blocked_until.pop(ip, None)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"

    _check_rate_limit(client_ip)

    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not user.is_active:
        _record_failed_attempt(client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    if not verify_password(payload.password, user.password_hash):
        _record_failed_attempt(client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    # Login riuscito: resetta contatore
    _clear_attempts(client_ip)

    log_audit(db, user_id=user.id, username=user.username,
              azione="login", entita="sessione", dettagli=f"IP: {client_ip}")
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
        is_admin=user.is_admin,
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="logout", entita="sessione", dettagli=f"IP: {client_ip}")
    db.commit()
    return {"detail": "Logout registrato"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
    }
