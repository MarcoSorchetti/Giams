from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.azienda_sql import Azienda
from app.models.azienda import AziendaUpdate, AziendaOut
from app.models.banca_sql import Banca
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/azienda", tags=["azienda"])


def _to_out(a: Azienda, db: Session) -> AziendaOut:
    banca_denom = None
    if a.banca_id:
        banca = db.query(Banca).filter(Banca.id == a.banca_id).first()
        if banca:
            banca_denom = banca.denominazione
    return AziendaOut(
        id=a.id, ragione_sociale=a.ragione_sociale,
        forma_giuridica=a.forma_giuridica, partita_iva=a.partita_iva,
        codice_fiscale=a.codice_fiscale, rea=a.rea,
        codice_ateco=a.codice_ateco, pec=a.pec, codice_sdi=a.codice_sdi,
        sede_legale_indirizzo=a.sede_legale_indirizzo,
        sede_legale_cap=a.sede_legale_cap,
        sede_legale_citta=a.sede_legale_citta,
        sede_legale_provincia=a.sede_legale_provincia,
        sede_operativa_indirizzo=a.sede_operativa_indirizzo,
        sede_operativa_cap=a.sede_operativa_cap,
        sede_operativa_citta=a.sede_operativa_citta,
        sede_operativa_provincia=a.sede_operativa_provincia,
        telefono=a.telefono, cellulare=a.cellulare,
        email=a.email, sito_web=a.sito_web,
        banca_id=a.banca_id, banca_denominazione=banca_denom,
        logo_path=a.logo_path, rappresentante_legale=a.rappresentante_legale,
        capitale_sociale=float(a.capitale_sociale) if a.capitale_sociale else None,
        note=a.note, updated_at=a.updated_at,
    )


@router.get("/", response_model=AziendaOut)
def get_azienda(db: Session = Depends(get_db)):
    """Restituisce i dati aziendali (singolo record)."""
    a = db.query(Azienda).first()
    if not a:
        # Crea record vuoto se non esiste
        a = Azienda(ragione_sociale="Gia.Mar Green Farm S.r.l.")
        db.add(a)
        db.commit()
        db.refresh(a)
    return _to_out(a, db)


@router.put("/", response_model=AziendaOut)
def update_azienda(data: AziendaUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Aggiorna i dati aziendali."""
    a = db.query(Azienda).first()
    if not a:
        a = Azienda(ragione_sociale="Gia.Mar Green Farm S.r.l.")
        db.add(a)
        db.flush()

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(a, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="azienda", entita_id=a.id,
              dettagli=f"Campi aggiornati: {', '.join(update_data.keys())}")
    db.commit()
    db.refresh(a)
    return _to_out(a, db)
