from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.parcella_sql import Parcella
from app.models.parcella import ParcellaCreate, ParcellaUpdate, ParcellaOut
from app.models.pagination import paginate, paginated_response


router = APIRouter(prefix="/parcelle", tags=["parcelle"])


@router.get("/stats")
def parcelle_stats(db: Session = Depends(get_db)):
    totale = db.query(func.count(Parcella.id)).scalar() or 0
    ettari = db.query(func.sum(Parcella.superficie_ettari)).scalar() or 0
    piante = db.query(func.sum(Parcella.num_piante)).scalar() or 0

    # Conta per varieta' principale
    varieta_rows = (
        db.query(Parcella.varieta_principale, func.count(Parcella.id))
        .group_by(Parcella.varieta_principale)
        .all()
    )
    per_varieta = {row[0]: row[1] for row in varieta_rows}

    # Conta per stato
    stato_rows = (
        db.query(Parcella.stato, func.count(Parcella.id))
        .group_by(Parcella.stato)
        .all()
    )
    per_stato = {row[0]: row[1] for row in stato_rows}

    return {
        "totale_parcelle": totale,
        "totale_ettari": float(ettari),
        "totale_piante": int(piante),
        "per_varieta": per_varieta,
        "per_stato": per_stato,
    }


@router.get("/")
def list_parcelle(
    search: Optional[str] = Query(None, alias="q"),
    varieta: Optional[str] = Query(None),
    stato: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Parcella)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Parcella.codice.ilike(term),
                Parcella.nome.ilike(term),
                Parcella.varieta_principale.ilike(term),
            )
        )
    if varieta:
        query = query.filter(Parcella.varieta_principale == varieta)
    if stato:
        query = query.filter(Parcella.stato == stato)

    query = query.order_by(Parcella.codice)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response(items, total, pg, pp, pages)


@router.get("/{parcella_id}", response_model=ParcellaOut)
def get_parcella(parcella_id: int, db: Session = Depends(get_db)):
    p = db.query(Parcella).filter(Parcella.id == parcella_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcella non trovata.")
    return p


@router.post("/", response_model=ParcellaOut, status_code=status.HTTP_201_CREATED)
def create_parcella(data: ParcellaCreate, db: Session = Depends(get_db)):
    if db.query(Parcella).filter(Parcella.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice parcella gia' esistente.")
    p = Parcella(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{parcella_id}", response_model=ParcellaOut)
def update_parcella(parcella_id: int, data: ParcellaUpdate, db: Session = Depends(get_db)):
    p = db.query(Parcella).filter(Parcella.id == parcella_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcella non trovata.")

    update_data = data.model_dump(exclude_unset=True)
    if "codice" in update_data and update_data["codice"] != p.codice:
        if db.query(Parcella).filter(Parcella.codice == update_data["codice"], Parcella.id != parcella_id).first():
            raise HTTPException(status_code=400, detail="Codice parcella gia' esistente.")

    for key, value in update_data.items():
        setattr(p, key, value)

    db.commit()
    db.refresh(p)
    return p


@router.delete("/{parcella_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parcella(parcella_id: int, db: Session = Depends(get_db)):
    p = db.query(Parcella).filter(Parcella.id == parcella_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcella non trovata.")
    db.delete(p)
    db.commit()
