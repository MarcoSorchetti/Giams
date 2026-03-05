import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.fornitore_sql import Fornitore
from app.models.fornitore import FornitoreCreate, FornitoreUpdate, FornitoreOut
from app.models.pagination import paginate, paginated_response
from app.models.costo_sql import Costo
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/fornitori", tags=["fornitori"])


def _check_duplicato_fornitore(db: Session, tipo_fornitore: str, partita_iva: str = None,
                                codice_fiscale: str = None, exclude_id: int = None):
    """Controlla duplicato P.IVA (azienda) o CF (privato). Ritorna dict conflict o None."""
    if tipo_fornitore == "azienda" and partita_iva:
        q = db.query(Fornitore).filter(Fornitore.partita_iva == partita_iva)
        if exclude_id:
            q = q.filter(Fornitore.id != exclude_id)
        dup = q.first()
        if dup:
            denom = dup.ragione_sociale or "" if dup.tipo_fornitore == "azienda" else " ".join(
                p for p in [dup.nome or "", dup.cognome or ""] if p)
            return {"detail": f"Partita IVA {partita_iva} gia' utilizzata da: {dup.codice} — {denom}",
                    "conflict_type": "partita_iva", "existing_codice": dup.codice,
                    "existing_denominazione": denom}
    elif tipo_fornitore == "privato" and codice_fiscale:
        q = db.query(Fornitore).filter(Fornitore.codice_fiscale == codice_fiscale)
        if exclude_id:
            q = q.filter(Fornitore.id != exclude_id)
        dup = q.first()
        if dup:
            denom = dup.ragione_sociale or "" if dup.tipo_fornitore == "azienda" else " ".join(
                p for p in [dup.nome or "", dup.cognome or ""] if p)
            return {"detail": f"Codice Fiscale {codice_fiscale} gia' utilizzato da: {dup.codice} — {denom}",
                    "conflict_type": "codice_fiscale", "existing_codice": dup.codice,
                    "existing_denominazione": denom}
    return None


def _next_codice_fornitore(db: Session) -> str:
    """Genera il prossimo codice fornitore: 0001, 0002, ..."""
    last = (
        db.query(Fornitore)
        .order_by(Fornitore.codice.desc())
        .with_for_update()
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


@router.get("/export/csv")
def export_fornitori_csv(
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
        query = query.filter(or_(
            Fornitore.codice.ilike(search), Fornitore.nome.ilike(search),
            Fornitore.cognome.ilike(search), Fornitore.ragione_sociale.ilike(search),
        ))

    fornitori = query.order_by(Fornitore.codice).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Codice", "Tipo", "Denominazione", "P.IVA", "Codice Fiscale",
        "Indirizzo", "CAP", "Citta", "Provincia", "Telefono", "Email",
        "IBAN", "Banca", "Categoria", "Cond. Pagamento", "Attivo", "Note",
    ])
    for f in fornitori:
        out = _to_out(f)
        writer.writerow([
            f.codice, f.tipo_fornitore, out.denominazione,
            f.partita_iva or "", f.codice_fiscale or "",
            f.indirizzo or "", f.cap or "", f.citta or "", f.provincia or "",
            f.telefono or "", f.email or "",
            f.iban or "", f.banca or "",
            f.categoria_merceologica or "", f.condizioni_pagamento or "",
            "Si" if f.attivo else "No", f.note or "",
        ])

    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Fornitori.csv"'},
    )


@router.get("/")
def list_fornitori(
    tipo: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    search: Optional[str] = Query(None, alias="q"),
    tutti: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Fornitore)

    if not tutti:
        query = query.filter(Fornitore.attivo == True)  # noqa: E712

    if tipo:
        query = query.filter(Fornitore.tipo_fornitore == tipo)

    if categoria:
        query = query.filter(Fornitore.categoria_merceologica == categoria)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Fornitore.codice.ilike(like),
                Fornitore.nome.ilike(like),
                Fornitore.cognome.ilike(like),
                Fornitore.ragione_sociale.ilike(like),
                Fornitore.email.ilike(like),
                Fornitore.citta.ilike(like),
                Fornitore.telefono.ilike(like),
            )
        )

    query = query.order_by(Fornitore.codice)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response([_to_out(f) for f in items], total, pg, pp, pages)


@router.get("/{fornitore_id}", response_model=FornitoreOut)
def get_fornitore(fornitore_id: int, db: Session = Depends(get_db)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")
    return _to_out(f)


@router.post("/", response_model=FornitoreOut, status_code=status.HTTP_201_CREATED)
def create_fornitore(data: FornitoreCreate, force: bool = Query(False), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Auto-genera codice
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_fornitore(db)

    if db.query(Fornitore).filter(Fornitore.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice fornitore gia' esistente.")

    if data.tipo_fornitore not in ("privato", "azienda"):
        raise HTTPException(status_code=400, detail="tipo_fornitore deve essere 'privato' o 'azienda'.")

    if not force:
        conflict = _check_duplicato_fornitore(db, data.tipo_fornitore, data.partita_iva, data.codice_fiscale)
        if conflict:
            return JSONResponse(status_code=409, content=conflict)

    f = Fornitore(**data.model_dump())
    db.add(f)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="fornitore", entita_id=f.id, codice_entita=f.codice)
    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.put("/{fornitore_id}", response_model=FornitoreOut)
def update_fornitore(fornitore_id: int, data: FornitoreUpdate, force: bool = Query(False), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice" in update_data and update_data["codice"] != f.codice:
        if db.query(Fornitore).filter(Fornitore.codice == update_data["codice"], Fornitore.id != fornitore_id).first():
            raise HTTPException(status_code=400, detail="Codice fornitore gia' esistente.")

    if not force:
        tipo = update_data.get("tipo_fornitore", f.tipo_fornitore)
        piva = update_data.get("partita_iva", f.partita_iva)
        cf = update_data.get("codice_fiscale", f.codice_fiscale)
        conflict = _check_duplicato_fornitore(db, tipo, piva, cf, exclude_id=fornitore_id)
        if conflict:
            return JSONResponse(status_code=409, content=conflict)

    for key, value in update_data.items():
        setattr(f, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="fornitore", entita_id=f.id, codice_entita=f.codice)
    db.commit()
    db.refresh(f)
    return _to_out(f)


@router.delete("/{fornitore_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fornitore(fornitore_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    f = db.query(Fornitore).filter(Fornitore.id == fornitore_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornitore non trovato.")

    # Verifica dipendenze
    if db.query(Costo).filter(Costo.fornitore_id == fornitore_id).first():
        raise HTTPException(status_code=400, detail="Impossibile eliminare: il fornitore ha costi associati.")

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="fornitore", entita_id=fornitore_id, codice_entita=f.codice)
    db.delete(f)
    db.commit()
