from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tipo_documento_sql import TipoDocumento
from app.models.tipo_documento import TipoDocumentoCreate, TipoDocumentoUpdate, TipoDocumentoOut
from app.models.costo_sql import Costo
from app.core.security import get_current_user
from app.services.audit import log_audit

router = APIRouter(prefix="/tipi-documento", tags=["tipi-documento"])


@router.get("/")
def list_tipi_documento(
    tutti: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    """Lista tipi documento, di default solo attivi."""
    query = db.query(TipoDocumento)
    if not tutti:
        query = query.filter(TipoDocumento.attivo == True)  # noqa: E712
    items = query.order_by(TipoDocumento.ordine, TipoDocumento.etichetta).all()
    return [TipoDocumentoOut.model_validate(t) for t in items]


@router.post("/", response_model=TipoDocumentoOut, status_code=status.HTTP_201_CREATED)
def create_tipo_documento(
    data: TipoDocumentoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crea un nuovo tipo documento."""
    valore = data.valore.strip().lower().replace(" ", "_")
    if db.query(TipoDocumento).filter(TipoDocumento.valore == valore).first():
        raise HTTPException(status_code=400, detail="Tipo documento con questo valore gia' esistente.")

    t = TipoDocumento(**data.model_dump())
    t.valore = valore
    db.add(t)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="tipo_documento", entita_id=t.id, codice_entita=t.valore)
    db.commit()
    db.refresh(t)
    return TipoDocumentoOut.model_validate(t)


@router.put("/{tipo_id}", response_model=TipoDocumentoOut)
def update_tipo_documento(
    tipo_id: int,
    data: TipoDocumentoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Modifica un tipo documento."""
    t = db.query(TipoDocumento).filter(TipoDocumento.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo documento non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if t.sistema:
        # Tipi di sistema: si puo' solo modificare etichetta, attivo e ordine
        allowed = {"etichetta", "attivo", "ordine"}
        forbidden = set(update_data.keys()) - allowed
        if forbidden:
            raise HTTPException(
                status_code=400,
                detail="Tipo di sistema: puoi modificare solo etichetta, attivo e ordine.",
            )

    if "valore" in update_data:
        new_valore = update_data["valore"].strip().lower().replace(" ", "_")
        if new_valore != t.valore:
            if db.query(TipoDocumento).filter(
                TipoDocumento.valore == new_valore, TipoDocumento.id != tipo_id
            ).first():
                raise HTTPException(status_code=400, detail="Valore gia' esistente.")
            update_data["valore"] = new_valore

    for key, value in update_data.items():
        setattr(t, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="tipo_documento", entita_id=t.id, codice_entita=t.valore)
    db.commit()
    db.refresh(t)
    return TipoDocumentoOut.model_validate(t)


@router.delete("/{tipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tipo_documento(
    tipo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Elimina un tipo documento (solo se non di sistema e non in uso)."""
    t = db.query(TipoDocumento).filter(TipoDocumento.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo documento non trovato.")

    if t.sistema:
        raise HTTPException(status_code=400, detail="Impossibile eliminare un tipo di sistema.")

    # Verifica uso nei costi
    in_uso = db.query(Costo).filter(Costo.tipo_documento == t.valore).first()
    if in_uso:
        return JSONResponse(status_code=409, content={
            "detail": f"Tipo '{t.etichetta}' utilizzato in costi esistenti. Puoi solo disattivarlo.",
            "conflict_type": "tipo_in_uso",
        })

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="tipo_documento", entita_id=tipo_id, codice_entita=t.valore)
    db.delete(t)
    db.commit()
