import csv
import io
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import case, func, or_

from app.database import get_db
from app.models.vendita_sql import Vendita, VenditaRiga
from app.models.vendita import (
    VenditaCreate, VenditaUpdate, VenditaOut, VenditaRigaOut,
    VenditaPatchInfo, SpedisciPayload, PagaPayload,
)
from app.models.confezionamento_sql import Confezionamento
from app.models.contenitore_sql import Contenitore
from app.models.cliente_sql import Cliente
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.routers.magazzino import _calcola_giacenza, _next_codice_movimento
from app.models.pagination import paginate, paginated_response
from app.core.security import get_current_user
from app.services.audit import log_audit
from app.utils.codice import next_codice_anno
from app.utils.denominazione import cliente_denominazione as _cliente_denominazione


router = APIRouter(prefix="/vendite", tags=["vendite"])

STATI_VALIDI = {"bozza", "confermata", "spedita", "pagata"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_codice_vendita(anno: int, db: Session) -> str:
    return next_codice_anno("V", Vendita, Vendita.codice, anno, db)


def _next_numero_fattura(anno: int, db: Session) -> str:
    return next_codice_anno("FI", Vendita, Vendita.numero_fattura, anno, db)


def _next_numero_ddt(anno: int, db: Session) -> str:
    return next_codice_anno("DDT", Vendita, Vendita.numero_ddt, anno, db)


def _build_vendita_out(v, db) -> VenditaOut:
    cli = db.query(Cliente).filter(Cliente.id == v.cliente_id).first()

    righe_db = db.query(VenditaRiga).filter(VenditaRiga.vendita_id == v.id).all()
    righe_out = []
    for r in righe_db:
        conf = db.query(Confezionamento).filter(Confezionamento.id == r.confezionamento_id).first()
        cont_desc = None
        if conf and conf.contenitore_id:
            cont = db.query(Contenitore).filter(Contenitore.id == conf.contenitore_id).first()
            if cont:
                cont_desc = cont.descrizione
        righe_out.append(VenditaRigaOut(
            id=r.id,
            confezionamento_id=r.confezionamento_id,
            confezionamento_codice=conf.codice if conf else None,
            confezionamento_formato=conf.formato if conf else None,
            contenitore_descrizione=cont_desc,
            quantita=r.quantita,
            prezzo_listino=float(r.prezzo_listino) if r.prezzo_listino else None,
            sconto_percentuale=float(r.sconto_percentuale) if r.sconto_percentuale else 0,
            prezzo_unitario=float(r.prezzo_unitario),
            importo_riga=float(r.importo_riga),
        ))

    return VenditaOut(
        id=v.id,
        codice=v.codice,
        cliente_id=v.cliente_id,
        cliente_denominazione=_cliente_denominazione(cli),
        data_vendita=v.data_vendita,
        anno_campagna=v.anno_campagna,
        stato=v.stato,
        imponibile=float(v.imponibile),
        sconto_percentuale=float(v.sconto_percentuale) if v.sconto_percentuale else None,
        imponibile_scontato=float(v.imponibile_scontato),
        iva_percentuale=float(v.iva_percentuale),
        importo_iva=float(v.importo_iva),
        arrotondamento=float(v.arrotondamento) if v.arrotondamento else 0,
        importo_totale=float(v.importo_totale),
        numero_fattura=v.numero_fattura,
        data_pagamento=v.data_pagamento,
        modalita_pagamento=v.modalita_pagamento,
        riferimento_pagamento=v.riferimento_pagamento,
        data_spedizione=v.data_spedizione,
        numero_ddt=v.numero_ddt,
        note_spedizione=v.note_spedizione,
        spedizione_indirizzo=v.spedizione_indirizzo,
        spedizione_cap=v.spedizione_cap,
        spedizione_citta=v.spedizione_citta,
        spedizione_provincia=v.spedizione_provincia,
        data_conferma=v.data_conferma,
        note=v.note,
        righe=righe_out,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


# ---------------------------------------------------------------------------
# Stats & Utility
# ---------------------------------------------------------------------------

@router.get("/stats")
def vendite_stats(anno: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Vendita)
    if anno:
        q = q.filter(Vendita.anno_campagna == anno)

    totale = q.count()
    bozze = q.filter(Vendita.stato == "bozza").count()
    confermate = q.filter(Vendita.stato == "confermata").count()
    spedite = q.filter(Vendita.stato == "spedita").count()
    pagate = q.filter(Vendita.stato == "pagata").count()

    # Fatturato = importo_totale di tutte le vendite confermate+
    q_conf = db.query(Vendita).filter(Vendita.stato.in_(["confermata", "spedita", "pagata"]))
    if anno:
        q_conf = q_conf.filter(Vendita.anno_campagna == anno)
    fatturato = q_conf.with_entities(func.sum(Vendita.importo_totale)).scalar() or 0
    imponibile_totale = q_conf.with_entities(func.sum(Vendita.imponibile_scontato)).scalar() or 0
    iva_totale = q_conf.with_entities(func.sum(Vendita.importo_iva)).scalar() or 0

    # Incassato = importo_totale di vendite pagate
    q_pag = db.query(Vendita).filter(Vendita.stato == "pagata")
    if anno:
        q_pag = q_pag.filter(Vendita.anno_campagna == anno)
    incassato = q_pag.with_entities(func.sum(Vendita.importo_totale)).scalar() or 0

    da_incassare = float(fatturato) - float(incassato)

    # Litri venduti (da righe vendita confermate+)
    litri_q = (
        db.query(func.sum(VenditaRiga.quantita * Confezionamento.capacita_litri))
        .join(Vendita, VenditaRiga.vendita_id == Vendita.id)
        .join(Confezionamento, VenditaRiga.confezionamento_id == Confezionamento.id)
        .filter(Vendita.stato.in_(["confermata", "spedita", "pagata"]))
    )
    if anno:
        litri_q = litri_q.filter(Vendita.anno_campagna == anno)
    litri_venduti = litri_q.scalar() or 0

    return {
        "totale": totale,
        "bozze": bozze,
        "confermate": confermate,
        "spedite": spedite,
        "pagate": pagate,
        "imponibile_totale": float(imponibile_totale),
        "iva_totale": float(iva_totale),
        "fatturato": float(fatturato),
        "incassato": float(incassato),
        "da_incassare": round(da_incassare, 2),
        "litri_venduti": float(litri_venduti),
    }


@router.get("/anni")
def vendite_anni(db: Session = Depends(get_db)):
    anni = (
        db.query(Vendita.anno_campagna)
        .distinct()
        .order_by(Vendita.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


@router.get("/top-clienti")
def top_clienti(
    anno: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            Cliente.id,
            Cliente.codice,
            Cliente.tipo_cliente,
            Cliente.ragione_sociale,
            Cliente.nome,
            Cliente.cognome,
            func.count(Vendita.id).label("num_vendite"),
            func.sum(Vendita.importo_totale).label("fatturato"),
            func.sum(
                case(
                    (Vendita.stato == "pagata", Vendita.importo_totale),
                    else_=0,
                )
            ).label("incassato"),
        )
        .join(Vendita, Vendita.cliente_id == Cliente.id)
        .filter(Vendita.stato.in_(["confermata", "spedita", "pagata"]))
    )
    if anno:
        q = q.filter(Vendita.anno_campagna == anno)
    rows = (
        q.group_by(Cliente.id, Cliente.codice, Cliente.tipo_cliente,
                    Cliente.ragione_sociale, Cliente.nome, Cliente.cognome)
        .order_by(func.sum(Vendita.importo_totale).desc())
        .limit(limit)
        .all()
    )
    result = []
    for r in rows:
        if r.tipo_cliente == "azienda":
            denom = r.ragione_sociale or ""
        else:
            denom = " ".join(p for p in [r.nome or "", r.cognome or ""] if p)
        result.append({
            "cliente_id": r.id,
            "codice": r.codice,
            "denominazione": denom,
            "num_vendite": r.num_vendite,
            "fatturato": float(r.fatturato or 0),
            "incassato": float(r.incassato or 0),
        })
    return result


@router.get("/next-codice")
def next_codice(anno: int = Query(...), db: Session = Depends(get_db)):
    return {"codice": _next_codice_vendita(anno, db)}


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

@router.get("/export/csv")
def export_vendite_csv(
    anno: Optional[int] = Query(None),
    stato: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Vendita)
    if anno:
        query = query.filter(Vendita.anno_campagna == anno)
    if stato:
        query = query.filter(Vendita.stato == stato)
    if cliente_id:
        query = query.filter(Vendita.cliente_id == cliente_id)

    vendite = query.order_by(Vendita.data_vendita.desc()).all()

    cli_ids = list({v.cliente_id for v in vendite if v.cliente_id})
    cli_map = {}
    if cli_ids:
        for c in db.query(Cliente).filter(Cliente.id.in_(cli_ids)).all():
            cli_map[c.id] = c

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Codice", "Data Vendita", "Cliente", "Stato", "N. Fattura",
        "Imponibile", "Sconto %", "Imponibile Scontato", "IVA %",
        "Importo IVA", "Importo Totale", "Data Pagamento", "Modalita Pagamento",
        "Data Spedizione", "N. DDT", "Note",
    ])
    for v in vendite:
        cli = cli_map.get(v.cliente_id)
        writer.writerow([
            v.codice, str(v.data_vendita) if v.data_vendita else "",
            _cliente_denominazione(cli), v.stato, v.numero_fattura or "",
            f"{float(v.imponibile):.2f}", f"{float(v.sconto_percentuale):.1f}" if v.sconto_percentuale else "0",
            f"{float(v.imponibile_scontato):.2f}", f"{float(v.iva_percentuale):.0f}",
            f"{float(v.importo_iva):.2f}", f"{float(v.importo_totale):.2f}",
            str(v.data_pagamento) if v.data_pagamento else "",
            v.modalita_pagamento or "",
            str(v.data_spedizione) if v.data_spedizione else "",
            v.numero_ddt or "", v.note or "",
        ])

    filename = f"Vendite_{anno or 'tutti'}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

_VENDITE_SORT_COLS = {
    "codice": Vendita.codice,
    "data_vendita": Vendita.data_vendita,
    "stato": Vendita.stato,
    "importo_totale": Vendita.importo_totale,
    "numero_fattura": Vendita.numero_fattura,
}


@router.get("/")
def list_vendite(
    anno: Optional[int] = Query(None),
    stato: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Vendita)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Vendita.codice.ilike(term),
                Vendita.numero_fattura.ilike(term),
                Vendita.numero_ddt.ilike(term),
            )
        )
    if anno:
        query = query.filter(Vendita.anno_campagna == anno)
    if stato:
        query = query.filter(Vendita.stato == stato)
    if cliente_id:
        query = query.filter(Vendita.cliente_id == cliente_id)

    # Sorting server-side con fallback a data_vendita desc
    col = _VENDITE_SORT_COLS.get(sort_by, Vendita.data_vendita)
    query = query.order_by(col.asc() if sort_dir == "asc" else col.desc())
    vendite, total, pg, pp, pages_count = paginate(query, page, per_page)
    if not vendite:
        return paginated_response([], total, pg, pp, pages_count)

    # Pre-carica dati correlati in batch per evitare N+1
    vendita_ids = [v.id for v in vendite]
    cliente_ids = list({v.cliente_id for v in vendite if v.cliente_id})

    clienti_map = {}
    if cliente_ids:
        for c in db.query(Cliente).filter(Cliente.id.in_(cliente_ids)).all():
            clienti_map[c.id] = c

    all_righe = db.query(VenditaRiga).filter(VenditaRiga.vendita_id.in_(vendita_ids)).all()
    righe_map = {}
    conf_ids = set()
    for r in all_righe:
        righe_map.setdefault(r.vendita_id, []).append(r)
        conf_ids.add(r.confezionamento_id)

    conf_map = {}
    cont_ids = set()
    if conf_ids:
        for conf in db.query(Confezionamento).filter(Confezionamento.id.in_(conf_ids)).all():
            conf_map[conf.id] = conf
            if conf.contenitore_id:
                cont_ids.add(conf.contenitore_id)

    cont_map = {}
    if cont_ids:
        for cont in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[cont.id] = cont

    result = []
    for v in vendite:
        cli = clienti_map.get(v.cliente_id)
        righe_out = []
        for r in righe_map.get(v.id, []):
            conf = conf_map.get(r.confezionamento_id)
            cont_desc = None
            if conf and conf.contenitore_id:
                cont = cont_map.get(conf.contenitore_id)
                if cont:
                    cont_desc = cont.descrizione
            righe_out.append(VenditaRigaOut(
                id=r.id,
                confezionamento_id=r.confezionamento_id,
                confezionamento_codice=conf.codice if conf else None,
                confezionamento_formato=conf.formato if conf else None,
                contenitore_descrizione=cont_desc,
                quantita=r.quantita,
                prezzo_listino=float(r.prezzo_listino) if r.prezzo_listino else None,
                sconto_percentuale=float(r.sconto_percentuale) if r.sconto_percentuale else 0,
                prezzo_unitario=float(r.prezzo_unitario),
                importo_riga=float(r.importo_riga),
            ))
        result.append(VenditaOut(
            id=v.id, codice=v.codice, cliente_id=v.cliente_id,
            cliente_denominazione=_cliente_denominazione(cli),
            data_vendita=v.data_vendita, anno_campagna=v.anno_campagna,
            stato=v.stato, imponibile=float(v.imponibile),
            sconto_percentuale=float(v.sconto_percentuale) if v.sconto_percentuale else None,
            imponibile_scontato=float(v.imponibile_scontato),
            iva_percentuale=float(v.iva_percentuale),
            importo_iva=float(v.importo_iva),
            arrotondamento=float(v.arrotondamento) if v.arrotondamento else 0,
            importo_totale=float(v.importo_totale),
            numero_fattura=v.numero_fattura, data_pagamento=v.data_pagamento,
            modalita_pagamento=v.modalita_pagamento,
            riferimento_pagamento=v.riferimento_pagamento,
            data_spedizione=v.data_spedizione, numero_ddt=v.numero_ddt,
            note_spedizione=v.note_spedizione,
            spedizione_indirizzo=v.spedizione_indirizzo,
            spedizione_cap=v.spedizione_cap, spedizione_citta=v.spedizione_citta,
            spedizione_provincia=v.spedizione_provincia,
            data_conferma=v.data_conferma, note=v.note,
            righe=righe_out, created_at=v.created_at, updated_at=v.updated_at,
        ))
    return paginated_response(result, total, pg, pp, pages_count)


@router.get("/{vendita_id}", response_model=VenditaOut)
def get_vendita(vendita_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")
    return _build_vendita_out(v, db)


@router.post("/", response_model=VenditaOut, status_code=status.HTTP_201_CREATED)
def create_vendita(data: VenditaCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Verifica cliente
    cli = db.query(Cliente).filter(Cliente.id == data.cliente_id).first()
    if not cli:
        raise HTTPException(status_code=400, detail="Cliente non trovato.")

    # Auto-genera codice dopo aver determinato anno_campagna
    codice = data.codice.strip() if data.codice else ""

    if db.query(Vendita).filter(Vendita.codice == codice).first():
        raise HTTPException(status_code=400, detail="Codice vendita gia' esistente.")

    # Verifica confezionamenti esistenti
    for riga in data.righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == riga.confezionamento_id).first()
        if not conf:
            raise HTTPException(status_code=400, detail=f"Confezionamento {riga.confezionamento_id} non trovato.")

    vendita_dict = data.model_dump(exclude={"righe"})
    # anno_campagna viene dal frontend (anno commerciale); default anno corrente
    if not vendita_dict.get("anno_campagna"):
        from datetime import date as _date
        vendita_dict["anno_campagna"] = _date.today().year
    # Auto-genera codice con anno campagna corretto
    if not codice:
        codice = _next_codice_vendita(vendita_dict["anno_campagna"], db)
    vendita_dict["codice"] = codice
    vendita_dict["stato"] = "bozza"

    # Ricalcolo importi server-side dalle righe (sconto per riga)
    iva_pct = float(vendita_dict.get("iva_percentuale", 4))
    imponibile_totale = 0.0

    v = Vendita(**vendita_dict)
    db.add(v)
    db.flush()

    for riga in data.righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == riga.confezionamento_id).first()
        prezzo_listino = float(riga.prezzo_listino) if riga.prezzo_listino else (float(conf.prezzo_imponibile) if conf and conf.prezzo_imponibile else 0)
        sconto_pct = float(riga.sconto_percentuale or 0)
        prezzo_unitario = round(prezzo_listino * (1 - sconto_pct / 100), 2)
        importo_riga = round(riga.quantita * prezzo_unitario, 2)
        imponibile_totale += importo_riga

        r = VenditaRiga(
            vendita_id=v.id,
            confezionamento_id=riga.confezionamento_id,
            quantita=riga.quantita,
            prezzo_listino=prezzo_listino,
            sconto_percentuale=sconto_pct,
            prezzo_unitario=prezzo_unitario,
            importo_riga=importo_riga,
        )
        db.add(r)

    # Totali header: sconto header = 0, imponibile = somma righe
    v.imponibile = round(imponibile_totale, 2)
    v.sconto_percentuale = 0
    v.imponibile_scontato = round(imponibile_totale, 2)
    v.importo_iva = round(imponibile_totale * iva_pct / 100, 2)
    arrotondamento = float(vendita_dict.get("arrotondamento", 0) or 0)
    v.arrotondamento = round(arrotondamento, 2)
    v.importo_totale = round(v.imponibile_scontato + v.importo_iva + v.arrotondamento, 2)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="vendita", entita_id=v.id, codice_entita=v.codice)
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


@router.put("/{vendita_id}", response_model=VenditaOut)
def update_vendita(vendita_id: int, data: VenditaUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato != "bozza":
        raise HTTPException(status_code=400, detail="Solo le vendite in bozza possono essere modificate.")

    update_data = data.model_dump(exclude_unset=True)
    righe_data = update_data.pop("righe", None)

    if "codice" in update_data and update_data["codice"] != v.codice:
        if db.query(Vendita).filter(Vendita.codice == update_data["codice"], Vendita.id != vendita_id).first():
            raise HTTPException(status_code=400, detail="Codice vendita gia' esistente.")

    if "cliente_id" in update_data:
        cli = db.query(Cliente).filter(Cliente.id == update_data["cliente_id"]).first()
        if not cli:
            raise HTTPException(status_code=400, detail="Cliente non trovato.")

    for key, value in update_data.items():
        setattr(v, key, value)

    iva_pct = float(v.iva_percentuale or 4)

    if righe_data is not None:
        # Cancella righe esistenti e ricrea con ricalcolo sconto per riga
        db.query(VenditaRiga).filter(VenditaRiga.vendita_id == vendita_id).delete()
        imponibile_totale = 0.0
        for riga in righe_data:
            conf = db.query(Confezionamento).filter(Confezionamento.id == riga["confezionamento_id"]).first()
            if not conf:
                raise HTTPException(status_code=400, detail=f"Confezionamento {riga['confezionamento_id']} non trovato.")
            prezzo_listino = float(riga.get("prezzo_listino") or 0) or (float(conf.prezzo_imponibile) if conf and conf.prezzo_imponibile else 0)
            sconto_pct = float(riga.get("sconto_percentuale", 0) or 0)
            prezzo_unitario = round(prezzo_listino * (1 - sconto_pct / 100), 2)
            importo_riga = round(riga["quantita"] * prezzo_unitario, 2)
            imponibile_totale += importo_riga

            r = VenditaRiga(
                vendita_id=vendita_id,
                confezionamento_id=riga["confezionamento_id"],
                quantita=riga["quantita"],
                prezzo_listino=prezzo_listino,
                sconto_percentuale=sconto_pct,
                prezzo_unitario=prezzo_unitario,
                importo_riga=importo_riga,
            )
            db.add(r)

        # Ricalcolo totali header dalle righe
        v.imponibile = round(imponibile_totale, 2)
        v.sconto_percentuale = 0
        v.imponibile_scontato = round(imponibile_totale, 2)
        v.importo_iva = round(imponibile_totale * iva_pct / 100, 2)
        arrotondamento = float(v.arrotondamento or 0)
        v.importo_totale = round(v.imponibile_scontato + v.importo_iva + arrotondamento, 2)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="vendita", entita_id=v.id, codice_entita=v.codice)
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


@router.delete("/{vendita_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendita(vendita_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato != "bozza":
        raise HTTPException(status_code=400, detail="Solo le vendite in bozza possono essere eliminate.")

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="vendita", entita_id=vendita_id, codice_entita=v.codice)
    db.query(VenditaRiga).filter(VenditaRiga.vendita_id == vendita_id).delete()
    db.delete(v)
    db.commit()


# ---------------------------------------------------------------------------
# Modifica dati non-critici (data, note) — disponibile su qualsiasi stato
# ---------------------------------------------------------------------------

@router.patch("/{vendita_id}", response_model=VenditaOut)
def patch_vendita_info(vendita_id: int, data: VenditaPatchInfo, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare.")

    for key, value in update_data.items():
        setattr(v, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato_info", entita="vendita", entita_id=v.id, codice_entita=v.codice,
              dettagli=f"Campi aggiornati: {', '.join(update_data.keys())}")
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


# ---------------------------------------------------------------------------
# Transizioni di stato
# ---------------------------------------------------------------------------

@router.post("/{vendita_id}/riporta-bozza", response_model=VenditaOut)
def riporta_bozza(vendita_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Riporta una vendita confermata, spedita o pagata in bozza, ricaricando il magazzino."""
    v = db.query(Vendita).filter(Vendita.id == vendita_id).with_for_update().first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato not in ("confermata", "spedita", "pagata"):
        raise HTTPException(status_code=400, detail="Solo le vendite confermate, spedite o pagate possono essere riportate in bozza.")

    righe = db.query(VenditaRiga).filter(VenditaRiga.vendita_id == vendita_id).all()

    # 1. Ricarica magazzino: crea movimenti di carico per annullare gli scarichi
    for riga in righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == riga.confezionamento_id).first()
        anno_conf = conf.anno_campagna if conf else v.anno_campagna
        mov = MovimentoMagazzino(
            codice=_next_codice_movimento(anno_conf, db),
            confezionamento_id=riga.confezionamento_id,
            tipo_movimento="carico",
            causale="annullo_vendita",
            quantita=riga.quantita,
            data_movimento=date.today(),
            anno_campagna=anno_conf,
            cliente_id=v.cliente_id,
            riferimento_documento=v.codice,
            note=f"Ricarico annullo vendita {v.codice} — {conf.codice if conf else ''}",
        )
        db.add(mov)
        db.flush()

    # 2. Salva dati precedenti nei campi "memoria" (prev_*)
    # I dati DDT e pagamento restano sui campi originali come memoria
    # Li azzeriamo solo: numero_fattura, data_conferma, stato

    # 3. Libera numero fattura e riporta in bozza
    numero_fattura_annullata = v.numero_fattura
    v.numero_fattura = None
    v.data_conferma = None
    v.stato = "bozza"

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="riportato_in_bozza", entita="vendita", entita_id=v.id, codice_entita=v.codice,
              dettagli=f"Fattura annullata: {numero_fattura_annullata or '—'}, magazzino ricaricato")
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


@router.post("/{vendita_id}/conferma", response_model=VenditaOut)
def conferma_vendita(vendita_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).with_for_update().first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato != "bozza":
        raise HTTPException(status_code=400, detail="Solo le vendite in bozza possono essere confermate.")

    righe = db.query(VenditaRiga).filter(VenditaRiga.vendita_id == vendita_id).all()
    if not righe:
        raise HTTPException(status_code=400, detail="La vendita non ha righe prodotto.")

    # 1. Verifica giacenza per ogni riga
    for riga in righe:
        giacenza = _calcola_giacenza(riga.confezionamento_id, db)
        if riga.quantita > giacenza:
            conf = db.query(Confezionamento).filter(Confezionamento.id == riga.confezionamento_id).first()
            codice_conf = conf.codice if conf else str(riga.confezionamento_id)
            raise HTTPException(
                status_code=400,
                detail=f"Giacenza insufficiente per {codice_conf}: richieste {riga.quantita} unita', disponibili {giacenza}."
            )

    # 2. Crea scarichi magazzino per ogni riga (anno_campagna dal confezionamento)
    for riga in righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == riga.confezionamento_id).first()
        anno_conf = conf.anno_campagna if conf else v.anno_campagna
        mov = MovimentoMagazzino(
            codice=_next_codice_movimento(anno_conf, db),
            confezionamento_id=riga.confezionamento_id,
            tipo_movimento="scarico",
            causale="vendita",
            quantita=riga.quantita,
            data_movimento=v.data_vendita or date.today(),
            anno_campagna=anno_conf,
            cliente_id=v.cliente_id,
            riferimento_documento=v.codice,
            note=f"Scarico vendita {v.codice} — {conf.codice if conf else ''}",
        )
        db.add(mov)
        db.flush()

    # 3. Genera numero fattura
    v.numero_fattura = _next_numero_fattura(v.anno_campagna, db)

    # 4. Snapshot indirizzo spedizione da cliente se non compilato
    if not v.spedizione_indirizzo:
        cli = db.query(Cliente).filter(Cliente.id == v.cliente_id).first()
        if cli:
            v.spedizione_indirizzo = cli.consegna_indirizzo or cli.indirizzo
            v.spedizione_cap = cli.consegna_cap or cli.cap
            v.spedizione_citta = cli.consegna_citta or cli.citta
            v.spedizione_provincia = cli.consegna_provincia or cli.provincia

    # 5. Aggiorna stato
    v.stato = "confermata"
    v.data_conferma = v.data_vendita or date.today()

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="confermato", entita="vendita", entita_id=v.id, codice_entita=v.codice,
              dettagli=f"Fattura {v.numero_fattura}")
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


@router.post("/{vendita_id}/spedisci", response_model=VenditaOut)
def spedisci_vendita(vendita_id: int, payload: SpedisciPayload, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).with_for_update().first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato != "confermata":
        raise HTTPException(status_code=400, detail="Solo le vendite confermate possono essere spedite.")

    v.stato = "spedita"
    v.data_spedizione = payload.data_spedizione
    if payload.numero_ddt:
        v.numero_ddt = payload.numero_ddt
    else:
        v.numero_ddt = _next_numero_ddt(v.anno_campagna, db)
    if payload.note_spedizione:
        v.note_spedizione = payload.note_spedizione
    if payload.spedizione_indirizzo:
        v.spedizione_indirizzo = payload.spedizione_indirizzo
        v.spedizione_cap = payload.spedizione_cap
        v.spedizione_citta = payload.spedizione_citta
        v.spedizione_provincia = payload.spedizione_provincia

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="spedito", entita="vendita", entita_id=v.id, codice_entita=v.codice,
              dettagli=f"DDT {v.numero_ddt}")
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


@router.post("/{vendita_id}/paga", response_model=VenditaOut)
def paga_vendita(vendita_id: int, payload: PagaPayload, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).with_for_update().first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")

    if v.stato not in ("confermata", "spedita"):
        raise HTTPException(status_code=400, detail="Solo le vendite confermate o spedite possono essere pagate.")

    v.stato = "pagata"
    v.data_pagamento = payload.data_pagamento
    v.modalita_pagamento = payload.modalita_pagamento
    v.riferimento_pagamento = payload.riferimento_pagamento

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="pagato", entita="vendita", entita_id=v.id, codice_entita=v.codice,
              dettagli=f"{payload.modalita_pagamento or ''}")
    db.commit()
    db.refresh(v)
    return _build_vendita_out(v, db)


# ---------------------------------------------------------------------------
# PDF — Fattura interna e DDT
# ---------------------------------------------------------------------------

@router.get("/{vendita_id}/fattura/pdf")
def download_fattura_pdf(vendita_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")
    if v.stato == "bozza":
        raise HTTPException(status_code=400, detail="La fattura e' disponibile solo per vendite confermate.")

    from app.services.pdf_vendita import genera_fattura_pdf

    cli = db.query(Cliente).filter(Cliente.id == v.cliente_id).first()
    righe = db.query(VenditaRiga).filter(VenditaRiga.vendita_id == v.id).all()

    # Arricchisci righe con dati confezionamento
    righe_info = []
    for r in righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == r.confezionamento_id).first()
        cont_desc = None
        if conf and conf.contenitore_id:
            cont = db.query(Contenitore).filter(Contenitore.id == conf.contenitore_id).first()
            if cont:
                cont_desc = cont.descrizione
        righe_info.append({
            "confezionamento_codice": conf.codice if conf else "",
            "confezionamento_formato": conf.formato if conf else "",
            "contenitore_descrizione": cont_desc or "",
            "quantita": r.quantita,
            "prezzo_listino": float(r.prezzo_listino) if r.prezzo_listino else None,
            "sconto_percentuale": float(r.sconto_percentuale) if r.sconto_percentuale else 0,
            "prezzo_unitario": float(r.prezzo_unitario),
            "importo_riga": float(r.importo_riga),
        })

    pdf_bytes = genera_fattura_pdf(v, cli, righe_info, db=db)
    filename = f"Fattura_{v.numero_fattura or v.codice}.pdf".replace("/", "-")

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{vendita_id}/ddt/pdf")
def download_ddt_pdf(vendita_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendita non trovata.")
    if v.stato == "bozza":
        raise HTTPException(status_code=400, detail="Il DDT e' disponibile solo per vendite confermate.")

    from app.services.pdf_vendita import genera_ddt_pdf

    cli = db.query(Cliente).filter(Cliente.id == v.cliente_id).first()
    righe = db.query(VenditaRiga).filter(VenditaRiga.vendita_id == v.id).all()

    righe_info = []
    for r in righe:
        conf = db.query(Confezionamento).filter(Confezionamento.id == r.confezionamento_id).first()
        cont_desc = None
        if conf and conf.contenitore_id:
            cont = db.query(Contenitore).filter(Contenitore.id == conf.contenitore_id).first()
            if cont:
                cont_desc = cont.descrizione
        righe_info.append({
            "confezionamento_codice": conf.codice if conf else "",
            "confezionamento_formato": conf.formato if conf else "",
            "contenitore_descrizione": cont_desc or "",
            "quantita": r.quantita,
        })

    pdf_bytes = genera_ddt_pdf(v, cli, righe_info, db=db)
    filename = f"DDT_{v.numero_ddt or v.codice}.pdf".replace("/", "-")

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
