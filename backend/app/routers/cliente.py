import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.cliente_sql import Cliente
from app.models.cliente import ClienteCreate, ClienteUpdate, ClienteOut
from app.models.pagination import paginate, paginated_response


router = APIRouter(prefix="/clienti", tags=["clienti"])


def _to_out(c: Cliente) -> ClienteOut:
    if c.tipo_cliente == "azienda":
        denominazione = c.ragione_sociale or ""
    else:
        parti = [c.nome or "", c.cognome or ""]
        denominazione = " ".join(p for p in parti if p)

    return ClienteOut(
        id=c.id,
        codice=c.codice,
        tipo_cliente=c.tipo_cliente,
        nome=c.nome,
        cognome=c.cognome,
        codice_fiscale=c.codice_fiscale,
        ragione_sociale=c.ragione_sociale,
        partita_iva=c.partita_iva,
        codice_sdi=c.codice_sdi,
        pec=c.pec,
        referente_nome=c.referente_nome,
        referente_telefono=c.referente_telefono,
        indirizzo=c.indirizzo,
        cap=c.cap,
        citta=c.citta,
        provincia=c.provincia,
        consegna_indirizzo=c.consegna_indirizzo,
        consegna_cap=c.consegna_cap,
        consegna_citta=c.consegna_citta,
        consegna_provincia=c.consegna_provincia,
        email=c.email,
        telefono=c.telefono,
        sconto_default=float(c.sconto_default) if c.sconto_default else None,
        attivo=c.attivo,
        note=c.note,
        denominazione=denominazione,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("/stats")
def clienti_stats(db: Session = Depends(get_db)):
    totale = db.query(Cliente).count()
    attivi = db.query(Cliente).filter(Cliente.attivo == True).count()  # noqa: E712
    privati = db.query(Cliente).filter(Cliente.tipo_cliente == "privato").count()
    aziende = db.query(Cliente).filter(Cliente.tipo_cliente == "azienda").count()

    return {
        "totale": totale,
        "attivi": attivi,
        "privati": privati,
        "aziende": aziende,
    }


@router.get("/export/csv")
def export_clienti_csv(
    tipo: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(Cliente)
    if not tutti:
        query = query.filter(Cliente.attivo == True)  # noqa: E712
    if tipo:
        query = query.filter(Cliente.tipo_cliente == tipo)
    if q:
        search = f"%{q}%"
        query = query.filter(or_(
            Cliente.codice.ilike(search), Cliente.nome.ilike(search),
            Cliente.cognome.ilike(search), Cliente.ragione_sociale.ilike(search),
        ))

    clienti = query.order_by(Cliente.codice).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Codice", "Tipo", "Denominazione", "P.IVA", "Codice Fiscale",
        "Indirizzo", "CAP", "Citta", "Provincia", "Telefono", "Email",
        "Sconto Default %", "Attivo", "Note",
    ])
    for c in clienti:
        out = _to_out(c)
        writer.writerow([
            c.codice, c.tipo_cliente, out.denominazione,
            c.partita_iva or "", c.codice_fiscale or "",
            c.indirizzo or "", c.cap or "", c.citta or "", c.provincia or "",
            c.telefono or "", c.email or "",
            f"{float(c.sconto_default):.1f}" if c.sconto_default else "0",
            "Si" if c.attivo else "No", c.note or "",
        ])

    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Clienti.csv"'},
    )


@router.get("/")
def list_clienti(
    tipo: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tutti: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Cliente)

    if not tutti:
        query = query.filter(Cliente.attivo == True)  # noqa: E712

    if tipo:
        query = query.filter(Cliente.tipo_cliente == tipo)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Cliente.codice.ilike(like),
                Cliente.nome.ilike(like),
                Cliente.cognome.ilike(like),
                Cliente.ragione_sociale.ilike(like),
                Cliente.email.ilike(like),
                Cliente.citta.ilike(like),
            )
        )
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Cliente.codice.ilike(term),
                Cliente.ragione_sociale.ilike(term),
                Cliente.nome.ilike(term),
                Cliente.cognome.ilike(term),
                Cliente.email.ilike(term),
                Cliente.telefono.ilike(term),
            )
        )

    query = query.order_by(Cliente.codice)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response([_to_out(c) for c in items], total, pg, pp, pages)


@router.get("/{cliente_id}", response_model=ClienteOut)
def get_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    return _to_out(c)


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    if db.query(Cliente).filter(Cliente.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice cliente gia' esistente.")

    if data.tipo_cliente not in ("privato", "azienda"):
        raise HTTPException(status_code=400, detail="tipo_cliente deve essere 'privato' o 'azienda'.")

    c = Cliente(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.put("/{cliente_id}", response_model=ClienteOut)
def update_cliente(cliente_id: int, data: ClienteUpdate, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice" in update_data and update_data["codice"] != c.codice:
        if db.query(Cliente).filter(Cliente.codice == update_data["codice"], Cliente.id != cliente_id).first():
            raise HTTPException(status_code=400, detail="Codice cliente gia' esistente.")

    for key, value in update_data.items():
        setattr(c, key, value)

    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    db.delete(c)
    db.commit()
