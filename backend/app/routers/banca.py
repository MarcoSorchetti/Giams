from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models.banca_sql import Banca
from app.models.banca import BancaCreate, BancaUpdate, BancaOut
from app.models.pagination import paginate, paginated_response
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/banche", tags=["banche"])


def _next_codice_banca(db: Session) -> str:
    """Genera il prossimo codice banca sequenziale: BK001, BK002, ..."""
    last = (
        db.query(func.max(Banca.codice))
        .filter(Banca.codice.like("BK%"))
        .scalar()
    )
    if last:
        try:
            num = int(last[2:]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"BK{num:03d}"


def _to_out(b: Banca) -> BancaOut:
    return BancaOut(
        id=b.id, codice=b.codice, denominazione=b.denominazione,
        iban=b.iban, bic_swift=b.bic_swift, abi=b.abi, cab=b.cab,
        numero_conto=b.numero_conto, filiale=b.filiale,
        intestatario=b.intestatario, tipo_conto=b.tipo_conto,
        note=b.note, attivo=b.attivo,
        created_at=b.created_at, updated_at=b.updated_at,
    )


@router.get("/next-codice")
def next_codice_banca(db: Session = Depends(get_db)):
    """Restituisce il prossimo codice banca sequenziale."""
    return {"codice": _next_codice_banca(db)}


@router.get("/")
def list_banche(
    search: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Banca)
    if not tutti:
        query = query.filter(Banca.attivo == True)  # noqa: E712
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Banca.codice.ilike(like), Banca.denominazione.ilike(like), Banca.iban.ilike(like))
        )
    query = query.order_by(Banca.denominazione)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response([_to_out(b) for b in items], total, pg, pp, pages)


@router.get("/{banca_id}", response_model=BancaOut)
def get_banca(banca_id: int, db: Session = Depends(get_db)):
    b = db.query(Banca).filter(Banca.id == banca_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Banca non trovata.")
    return _to_out(b)


@router.post("/", response_model=BancaOut, status_code=status.HTTP_201_CREATED)
def create_banca(data: BancaCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_banca(db)
    if db.query(Banca).filter(Banca.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice banca gia' esistente.")
    b = Banca(**data.model_dump())
    db.add(b)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="banca", entita_id=b.id, codice_entita=b.codice)
    db.commit()
    db.refresh(b)
    return _to_out(b)


@router.put("/{banca_id}", response_model=BancaOut)
def update_banca(banca_id: int, data: BancaUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    b = db.query(Banca).filter(Banca.id == banca_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Banca non trovata.")
    update_data = data.model_dump(exclude_unset=True)
    if "codice" in update_data and update_data["codice"] != b.codice:
        if db.query(Banca).filter(Banca.codice == update_data["codice"], Banca.id != banca_id).first():
            raise HTTPException(status_code=400, detail="Codice banca gia' esistente.")
    for key, value in update_data.items():
        setattr(b, key, value)
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="banca", entita_id=b.id, codice_entita=b.codice)
    db.commit()
    db.refresh(b)
    return _to_out(b)


@router.delete("/{banca_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_banca(banca_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    b = db.query(Banca).filter(Banca.id == banca_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Banca non trovata.")
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="banca", entita_id=banca_id, codice_entita=b.codice)
    db.delete(b)
    db.commit()
