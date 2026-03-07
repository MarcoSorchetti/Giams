from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models.frantoio_sql import Frantoio
from app.models.frantoio import FrantoioCreate, FrantoioUpdate, FrantoioOut
from app.models.pagination import paginate, paginated_response
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/frantoi", tags=["frantoi"])


def _next_codice_frantoio(db: Session) -> str:
    """Genera il prossimo codice frantoio sequenziale: FR001, FR002, ..."""
    last = (
        db.query(func.max(Frantoio.codice))
        .filter(Frantoio.codice.like("FR%"))
        .scalar()
    )
    if last:
        try:
            num = int(last[2:]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"FR{num:03d}"


def _to_out(f: Frantoio) -> FrantoioOut:
    return FrantoioOut(
        id=f.id, codice=f.codice, denominazione=f.denominazione,
        partita_iva=f.partita_iva, indirizzo=f.indirizzo, cap=f.cap,
        citta=f.citta, provincia=f.provincia, telefono=f.telefono,
        email=f.email, referente=f.referente, servizi=f.servizi,
        note=f.note, attivo=f.attivo,
        created_at=f.created_at, updated_at=f.updated_at,
    )


@router.get("/next-codice")
def next_codice_frantoio(db: Session = Depends(get_db)):
    """Restituisce il prossimo codice frantoio sequenziale."""
    return {"codice": _next_codice_frantoio(db)}


@router.get("/")
def list_frantoi(
    search: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Frantoio)
    if not tutti:
        query = query.filter(Frantoio.attivo == True)  # noqa: E712
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Frantoio.codice.ilike(like), Frantoio.denominazione.ilike(like))
        )
    query = query.order_by(Frantoio.denominazione)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response([_to_out(f) for f in items], total, pg, pp, pages)


@router.get("/{frantoio_id}", response_model=FrantoioOut)
def get_frantoio(frantoio_id: int, db: Session = Depends(get_db)):
    f = db.query(Frantoio).filter(Frantoio.id == frantoio_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Frantoio non trovato.")
    return _to_out(f)


@router.post("/", response_model=FrantoioOut, status_code=status.HTTP_201_CREATED)
def create_frantoio(data: FrantoioCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_frantoio(db)
    if db.query(Frantoio).filter(Frantoio.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice frantoio gia' esistente.")
    f = Frantoio(**data.model_dump())
    db.add(f)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="frantoio", entita_id=f.id, codice_entita=f.codice)
    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.put("/{frantoio_id}", response_model=FrantoioOut)
def update_frantoio(frantoio_id: int, data: FrantoioUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    f = db.query(Frantoio).filter(Frantoio.id == frantoio_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Frantoio non trovato.")
    update_data = data.model_dump(exclude_unset=True)
    if "codice" in update_data and update_data["codice"] != f.codice:
        if db.query(Frantoio).filter(Frantoio.codice == update_data["codice"], Frantoio.id != frantoio_id).first():
            raise HTTPException(status_code=400, detail="Codice frantoio gia' esistente.")
    for key, value in update_data.items():
        setattr(f, key, value)
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="frantoio", entita_id=f.id, codice_entita=f.codice)
    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.delete("/{frantoio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_frantoio(frantoio_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    f = db.query(Frantoio).filter(Frantoio.id == frantoio_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Frantoio non trovato.")
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="frantoio", entita_id=frantoio_id, codice_entita=f.codice)
    db.delete(f)
    db.commit()
