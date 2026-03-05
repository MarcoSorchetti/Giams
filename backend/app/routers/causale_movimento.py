from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.causale_movimento_sql import CausaleMovimento
from app.models.causale_movimento import CausaleMovCreate, CausaleMovUpdate, CausaleMovOut
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.core.security import get_current_user
from app.services.audit import log_audit

router = APIRouter(prefix="/causali-movimento", tags=["causali-movimento"])

TIPI_VALIDI = {"carico", "scarico"}


@router.get("/")
def list_causali(
    tipo: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(CausaleMovimento)
    if not tutti:
        query = query.filter(CausaleMovimento.attivo == True)  # noqa: E712
    if tipo and tipo in TIPI_VALIDI:
        query = query.filter(CausaleMovimento.tipo_movimento == tipo)
    items = query.order_by(CausaleMovimento.label).all()
    return [CausaleMovOut.model_validate(c) for c in items]


@router.post("/", response_model=CausaleMovOut, status_code=status.HTTP_201_CREATED)
def create_causale(
    data: CausaleMovCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.tipo_movimento not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail="tipo_movimento deve essere 'carico' o 'scarico'.")

    codice = data.codice.strip().lower()
    if db.query(CausaleMovimento).filter(CausaleMovimento.codice == codice).first():
        raise HTTPException(status_code=400, detail="Codice causale gia' esistente.")

    c = CausaleMovimento(**data.model_dump())
    c.codice = codice
    db.add(c)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="causale_movimento", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)
    return CausaleMovOut.model_validate(c)


@router.put("/{causale_id}", response_model=CausaleMovOut)
def update_causale(
    causale_id: int,
    data: CausaleMovUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(CausaleMovimento).filter(CausaleMovimento.id == causale_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Causale non trovata.")

    update_data = data.model_dump(exclude_unset=True)

    if c.sistema:
        # Causali di sistema: si puo' solo modificare label e attivo
        allowed = {"label", "attivo"}
        forbidden = set(update_data.keys()) - allowed
        if forbidden:
            raise HTTPException(
                status_code=400,
                detail=f"Causale di sistema: puoi modificare solo label e attivo.",
            )

    if "tipo_movimento" in update_data and update_data["tipo_movimento"] not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail="tipo_movimento deve essere 'carico' o 'scarico'.")

    if "codice" in update_data:
        new_codice = update_data["codice"].strip().lower()
        if new_codice != c.codice:
            if db.query(CausaleMovimento).filter(
                CausaleMovimento.codice == new_codice, CausaleMovimento.id != causale_id
            ).first():
                raise HTTPException(status_code=400, detail="Codice causale gia' esistente.")
            update_data["codice"] = new_codice

    for key, value in update_data.items():
        setattr(c, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="causale_movimento", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)
    return CausaleMovOut.model_validate(c)


@router.delete("/{causale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_causale(
    causale_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(CausaleMovimento).filter(CausaleMovimento.id == causale_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Causale non trovata.")

    if c.sistema:
        raise HTTPException(status_code=400, detail="Impossibile eliminare una causale di sistema.")

    # Verifica uso in movimenti esistenti
    in_uso = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.causale == c.codice).first()
    if in_uso:
        return JSONResponse(status_code=409, content={
            "detail": f"Causale '{c.label}' utilizzata in movimenti esistenti. Puoi solo disattivarla.",
            "conflict_type": "causale_in_uso",
        })

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="causale_movimento", entita_id=causale_id, codice_entita=c.codice)
    db.delete(c)
    db.commit()
