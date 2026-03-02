from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.fornitore_sql import Fornitore
from app.models.fornitore import FornitoreCreate, FornitoreUpdate, FornitoreOut


router = APIRouter(prefix="/fornitori", tags=["fornitori"])


def _next_codice_fornitore(db: Session) -> str:
    """Genera il prossimo codice fornitore: 0001, 0002, ..."""
    last = (
        db.query(Fornitore)
        .order_by(Fornitore.codice.desc())
        .first()
    )
    if last and last.codice:
        try:
            num = int(last.codice) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"{num:04d}"


def _to_out(f: Fornitore) -> FornitoreOut:
    if f.tipo_fornitore == "azienda":
        denominazione = f.ragione_sociale or ""
    else:
        parti = [f.nome or "", f.cognome or ""]
        denominazione = " ".join(p for p in parti if p)

    return FornitoreOut(
        id=f.id,
        codice=f.codice,
        tipo_fornitore=f.tipo_fornitore,
        nome=f.nome,
        cognome=f.cognome,
        codice_fiscale=f.codice_fiscale,
        ragione_sociale=f.ragione_sociale,
        partita_iva=f.partita_iva,
        codice_sdi=f.codice_sdi,
        pec=f.pec,
        referente_nome=f.referente_nome,
        referente_telefono=f.referente_telefono,
        indirizzo=f.indirizzo,
        cap=f.cap,
        citta=f.citta,
        provincia=f.provincia,
        email=f.email,
        telefono=f.telefono,
        iban=f.iban,
        banca=f.banca,
        categoria_merceologica=f.categoria_merceologica,
        condizioni_pagamento=f.condizioni_pagamento,
        attivo=f.attivo,
        note=f.note,
        denominazione=denominazione,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


@router.get("/next-codice")
def next_codice_fornitore(db: Session = Depends(get_db)):
    return {"codice": _next_codice_fornitore(db)}


@router.get("/stats")
def fornitori_stats(db: Session = Depends(get_db)):
    totale = db.query(Fornitore).count()
    attivi = db.query(Fornitore).filter(Fornitore.attivo == True).count()  # noqa: E712
    privati = db.query(Fornitore).filter(Fornitore.tipo_fornitore == "privato").count()
    aziende = db.query(Fornitore).filter(Fornitore.tipo_fornitore == "azienda").count()

    return {
        "totale": totale,
        "attivi": attivi,
        "privati": privati,
        "aziende": aziende,
    }


@router.get("/", response_model=List[FornitoreOut])
def list_fornitori(
    tipo: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(Fornitore)

    if not tutti:
        query = query.filter(Fornitore.attivo == True)  # noqa: E712

    if tipo:
        query = query.filter(Fornitore.tipo_fornitore == tipo)

    if categoria:
        query = query.filter(Fornitore.categoria_merceologica == categoria)

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Fornitore.codice.ilike(search),
                Fornitore.nome.ilike(search),
                Fornitore.cognome.ilike(search),
                Fornitore.ragione_sociale.ilike(search),
                Fornitore.email.ilike(search),
                Fornitore.citta.ilike(search),
            )
        )

    fornitori = query.order_by(Fornitore.codice).all()
    return [_to_out(f) for f in fornitori]


@router.get("/{fornitore_id}", response_model=FornitoreOut)
def get_fornitore(fornitore_id: int, db: Session = Depends(get_db)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")
    return _to_out(f)


@router.post("/", response_model=FornitoreOut, status_code=status.HTTP_201_CREATED)
def create_fornitore(data: FornitoreCreate, db: Session = Depends(get_db)):
    # Auto-genera codice
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_fornitore(db)

    if db.query(Fornitore).filter(Fornitore.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice fornitore gia' esistente.")

    if data.tipo_fornitore not in ("privato", "azienda"):
        raise HTTPException(status_code=400, detail="tipo_fornitore deve essere 'privato' o 'azienda'.")

    f = Fornitore(**data.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.put("/{fornitore_id}", response_model=FornitoreOut)
def update_fornitore(fornitore_id: int, data: FornitoreUpdate, db: Session = Depends(get_db)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice" in update_data and update_data["codice"] != f.codice:
        if db.query(Fornitore).filter(Fornitore.codice == update_data["codice"], Fornitore.id != fornitore_id).first():
            raise HTTPException(status_code=400, detail="Codice fornitore gia' esistente.")

    for key, value in update_data.items():
        setattr(f, key, value)

    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.delete("/{fornitore_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fornitore(fornitore_id: int, db: Session = Depends(get_db)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")
    db.delete(f)
    db.commit()
