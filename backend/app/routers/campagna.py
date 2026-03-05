from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campagna_sql import Campagna
from app.models.campagna import CampagnaCreate, CampagnaUpdate, CampagnaOut
from app.core.security import get_current_user
from app.services.audit import log_audit

router = APIRouter(prefix="/campagne", tags=["campagne"])

STATI_VALIDI = {"aperta", "chiusa"}


@router.get("/")
def list_campagne(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Campagna).order_by(Campagna.anno.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [CampagnaOut.model_validate(c) for c in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/attive")
def list_campagne_attive(db: Session = Depends(get_db)):
    items = (
        db.query(Campagna)
        .filter(Campagna.stato == "aperta")
        .order_by(Campagna.anno.desc())
        .all()
    )
    return [CampagnaOut.model_validate(c) for c in items]


@router.get("/anni")
def list_anni(db: Session = Depends(get_db)):
    """Lista anni da campagne registrate (retrocompatibilita')."""
    rows = db.query(Campagna.anno).order_by(Campagna.anno.desc()).all()
    return [r[0] for r in rows]


@router.get("/{campagna_id}", response_model=CampagnaOut)
def get_campagna(campagna_id: int, db: Session = Depends(get_db)):
    c = db.query(Campagna).filter(Campagna.id == campagna_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagna non trovata.")
    return CampagnaOut.model_validate(c)


@router.post("/", response_model=CampagnaOut, status_code=status.HTTP_201_CREATED)
def create_campagna(
    data: CampagnaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if db.query(Campagna).filter(Campagna.anno == data.anno).first():
        raise HTTPException(status_code=400, detail=f"Campagna {data.anno} gia' esistente.")

    c = Campagna(**data.model_dump())
    db.add(c)
    db.flush()
    log_audit(
        db, user_id=current_user.id, username=current_user.username,
        azione="creato", entita="campagna", entita_id=c.id,
        codice_entita=str(c.anno),
    )
    db.commit()
    db.refresh(c)
    return CampagnaOut.model_validate(c)


@router.put("/{campagna_id}", response_model=CampagnaOut)
def update_campagna(
    campagna_id: int,
    data: CampagnaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(Campagna).filter(Campagna.id == campagna_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagna non trovata.")

    update_data = data.model_dump(exclude_unset=True)

    if "anno" in update_data and update_data["anno"] != c.anno:
        if db.query(Campagna).filter(
            Campagna.anno == update_data["anno"], Campagna.id != campagna_id
        ).first():
            raise HTTPException(status_code=400, detail="Anno campagna gia' esistente.")

    for key, value in update_data.items():
        setattr(c, key, value)

    log_audit(
        db, user_id=current_user.id, username=current_user.username,
        azione="modificato", entita="campagna", entita_id=c.id,
        codice_entita=str(c.anno),
    )
    db.commit()
    db.refresh(c)
    return CampagnaOut.model_validate(c)


@router.delete("/{campagna_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campagna(
    campagna_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.confezionamento_sql import Confezionamento

    c = db.query(Campagna).filter(Campagna.id == campagna_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagna non trovata.")

    # Non eliminare se ci sono confezionamenti collegati
    in_uso = db.query(Confezionamento).filter(Confezionamento.anno_campagna == c.anno).first()
    if in_uso:
        raise HTTPException(
            status_code=409,
            detail=f"Campagna {c.anno} ha confezionamenti associati. Non eliminabile.",
        )

    log_audit(
        db, user_id=current_user.id, username=current_user.username,
        azione="eliminato", entita="campagna", entita_id=campagna_id,
        codice_entita=str(c.anno),
    )
    db.delete(c)
    db.commit()


@router.post("/{campagna_id}/chiudi", response_model=CampagnaOut)
def chiudi_campagna(
    campagna_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(Campagna).filter(Campagna.id == campagna_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagna non trovata.")
    if c.stato == "chiusa":
        raise HTTPException(status_code=400, detail="Campagna gia' chiusa.")

    c.stato = "chiusa"
    log_audit(
        db, user_id=current_user.id, username=current_user.username,
        azione="chiuso", entita="campagna", entita_id=c.id,
        codice_entita=str(c.anno),
    )
    db.commit()
    db.refresh(c)
    return CampagnaOut.model_validate(c)


@router.post("/{campagna_id}/riapri", response_model=CampagnaOut)
def riapri_campagna(
    campagna_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(Campagna).filter(Campagna.id == campagna_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagna non trovata.")
    if c.stato == "aperta":
        raise HTTPException(status_code=400, detail="Campagna gia' aperta.")

    c.stato = "aperta"
    log_audit(
        db, user_id=current_user.id, username=current_user.username,
        azione="riaperto", entita="campagna", entita_id=c.id,
        codice_entita=str(c.anno),
    )
    db.commit()
    db.refresh(c)
    return CampagnaOut.model_validate(c)
