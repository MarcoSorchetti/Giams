import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_

from app.database import get_db
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.models.confezionamento_sql import Confezionamento
from app.models.contenitore_sql import Contenitore
from app.models.cliente_sql import Cliente
from app.models.movimento_magazzino import (
    MovimentoMagCreate, MovimentoMagUpdate, MovimentoMagOut,
)
from app.models.pagination import paginate, paginated_response
from app.models.causale_movimento_sql import CausaleMovimento
from app.core.security import get_current_user
from app.services.audit import log_audit
from app.utils.codice import next_codice_anno
from app.utils.denominazione import cliente_denominazione as _cliente_denominazione


router = APIRouter(prefix="/magazzino", tags=["magazzino"])

TIPI_VALIDI = {"carico", "scarico"}


def _get_causali_valide(db: Session, include_vendita: bool = False):
    """Restituisce i codici causali attive dal DB. Esclude 'vendita' se non richiesto."""
    query = db.query(CausaleMovimento.codice).filter(CausaleMovimento.attivo == True)  # noqa: E712
    if not include_vendita:
        query = query.filter(CausaleMovimento.codice != "vendita")
    return {row[0] for row in query.all()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_codice_movimento(anno: int, db: Session) -> str:
    return next_codice_anno("MV", MovimentoMagazzino, MovimentoMagazzino.codice, anno, db)


def _build_movimento_out(mov, db=None, conf_map=None, cont_map=None, cli_map=None):
    """Costruisce MovimentoMagOut. Se vengono passate le mappe pre-caricate
    (conf_map, cont_map, cli_map) le usa evitando query N+1.
    Fallback a query singole se db e' fornito (per singolo record)."""
    if conf_map is not None:
        conf = conf_map.get(mov.confezionamento_id)
    elif db:
        conf = db.query(Confezionamento).filter(Confezionamento.id == mov.confezionamento_id).first()
    else:
        conf = None

    cont_desc = None
    if conf and conf.contenitore_id:
        if cont_map is not None:
            cont = cont_map.get(conf.contenitore_id)
        elif db:
            cont = db.query(Contenitore).filter(Contenitore.id == conf.contenitore_id).first()
        else:
            cont = None
        if cont:
            cont_desc = cont.descrizione

    cli = None
    if mov.cliente_id:
        if cli_map is not None:
            cli = cli_map.get(mov.cliente_id)
        elif db:
            cli = db.query(Cliente).filter(Cliente.id == mov.cliente_id).first()

    return MovimentoMagOut(
        id=mov.id,
        codice=mov.codice,
        confezionamento_id=mov.confezionamento_id,
        confezionamento_codice=conf.codice if conf else None,
        confezionamento_formato=conf.formato if conf else None,
        contenitore_descrizione=cont_desc,
        tipo_movimento=mov.tipo_movimento,
        causale=mov.causale,
        quantita=mov.quantita,
        data_movimento=mov.data_movimento,
        anno_campagna=mov.anno_campagna,
        cliente_id=mov.cliente_id,
        cliente_denominazione=_cliente_denominazione(cli),
        riferimento_documento=mov.riferimento_documento,
        note=mov.note,
        created_at=mov.created_at,
        updated_at=mov.updated_at,
    )


def _build_relation_maps(movimenti, db):
    """Carica Confezionamento, Contenitore e Cliente in batch per una lista
    di movimenti. Restituisce (conf_map, cont_map, cli_map)."""
    conf_ids = list({m.confezionamento_id for m in movimenti if m.confezionamento_id})
    conf_map = {}
    if conf_ids:
        for c in db.query(Confezionamento).filter(Confezionamento.id.in_(conf_ids)).all():
            conf_map[c.id] = c

    cont_ids = list({c.contenitore_id for c in conf_map.values() if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for c in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[c.id] = c

    cli_ids = list({m.cliente_id for m in movimenti if m.cliente_id})
    cli_map = {}
    if cli_ids:
        for c in db.query(Cliente).filter(Cliente.id.in_(cli_ids)).all():
            cli_map[c.id] = c

    return conf_map, cont_map, cli_map


# ---------------------------------------------------------------------------
# Giacenze — il cuore del magazzino
# ---------------------------------------------------------------------------

@router.get("/giacenze")
def giacenze(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Calcola la giacenza corrente per ogni confezionamento.

    giacenza = SUM(carico) - SUM(scarico) per confezionamento_id
    """
    q = db.query(
        MovimentoMagazzino.confezionamento_id,
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("totale_carichi"),
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("totale_scarichi"),
    ).group_by(MovimentoMagazzino.confezionamento_id)

    if anno:
        q = q.filter(MovimentoMagazzino.anno_campagna == anno)

    rows = q.all()

    # Batch load confezionamenti e contenitori (evita N+1)
    conf_ids = [conf_id for conf_id, _, _ in rows if conf_id]
    conf_map = {}
    if conf_ids:
        for c in db.query(Confezionamento).filter(Confezionamento.id.in_(conf_ids)).all():
            conf_map[c.id] = c

    cont_ids = list({c.contenitore_id for c in conf_map.values() if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for c in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[c.id] = c

    risultati = []
    for conf_id, carichi, scarichi in rows:
        giacenza = int(carichi) - int(scarichi)
        conf = conf_map.get(conf_id)
        if not conf:
            continue

        cont = cont_map.get(conf.contenitore_id) if conf.contenitore_id else None

        risultati.append({
            "confezionamento_id": conf_id,
            "confezionamento_codice": conf.codice,
            "formato": conf.formato,
            "capacita_litri": float(conf.capacita_litri),
            "contenitore_descrizione": cont.descrizione if cont else None,
            "totale_carichi": int(carichi),
            "totale_scarichi": int(scarichi),
            "giacenza_unita": giacenza,
            "giacenza_litri": round(giacenza * float(conf.capacita_litri), 2),
        })

    return risultati


# ---------------------------------------------------------------------------
# Giacenze raggruppate per campagna
# ---------------------------------------------------------------------------

@router.get("/giacenze-per-campagna")
def giacenze_per_campagna(db: Session = Depends(get_db)):
    """Giacenze raggruppate per anno_campagna — vista magazzino multi-campagna."""
    q = db.query(
        MovimentoMagazzino.anno_campagna,
        MovimentoMagazzino.confezionamento_id,
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("totale_carichi"),
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("totale_scarichi"),
    ).group_by(MovimentoMagazzino.anno_campagna, MovimentoMagazzino.confezionamento_id)

    rows = q.all()

    # Batch load
    conf_ids = list({r[1] for r in rows if r[1]})
    conf_map = {}
    if conf_ids:
        for c in db.query(Confezionamento).filter(Confezionamento.id.in_(conf_ids)).all():
            conf_map[c.id] = c

    cont_ids = list({c.contenitore_id for c in conf_map.values() if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for c in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[c.id] = c

    # Raggruppa per anno
    per_anno = {}
    totale_gen_unita = 0
    totale_gen_litri = 0.0

    for anno_camp, conf_id, carichi, scarichi in rows:
        giacenza = int(carichi) - int(scarichi)
        conf = conf_map.get(conf_id)
        if not conf:
            continue
        cont = cont_map.get(conf.contenitore_id) if conf.contenitore_id else None
        litri = round(giacenza * float(conf.capacita_litri), 2)

        if anno_camp not in per_anno:
            per_anno[anno_camp] = {"anno_campagna": anno_camp, "giacenze": [], "totale_unita": 0, "totale_litri": 0.0}

        per_anno[anno_camp]["giacenze"].append({
            "confezionamento_id": conf_id,
            "confezionamento_codice": conf.codice,
            "formato": conf.formato,
            "capacita_litri": float(conf.capacita_litri),
            "contenitore_descrizione": cont.descrizione if cont else None,
            "totale_carichi": int(carichi),
            "totale_scarichi": int(scarichi),
            "giacenza_unita": giacenza,
            "giacenza_litri": litri,
        })
        per_anno[anno_camp]["totale_unita"] += giacenza
        per_anno[anno_camp]["totale_litri"] = round(per_anno[anno_camp]["totale_litri"] + litri, 2)
        totale_gen_unita += giacenza
        totale_gen_litri = round(totale_gen_litri + litri, 2)

    campagne = sorted(per_anno.values(), key=lambda x: x["anno_campagna"], reverse=True)
    return {
        "campagne": campagne,
        "totale_generale_unita": totale_gen_unita,
        "totale_generale_litri": totale_gen_litri,
    }


# ---------------------------------------------------------------------------
# Confezionamenti disponibili (giacenza > 0) — per dropdown
# ---------------------------------------------------------------------------

@router.get("/confezionamenti-disponibili")
def confezionamenti_disponibili(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Restituisce solo confezionamenti con giacenza > 0, con info giacenza."""
    q = db.query(
        MovimentoMagazzino.confezionamento_id,
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("carichi"),
        func.sum(
            case(
                (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                else_=0,
            )
        ).label("scarichi"),
    ).group_by(MovimentoMagazzino.confezionamento_id)

    rows = q.all()

    # Filtra giacenza > 0
    disponibili_ids = {}
    for conf_id, carichi, scarichi in rows:
        giac = int(carichi) - int(scarichi)
        if giac > 0:
            disponibili_ids[conf_id] = giac

    if not disponibili_ids:
        return []

    # Batch load confezionamenti
    confs = db.query(Confezionamento).filter(Confezionamento.id.in_(list(disponibili_ids.keys()))).all()

    # Filtro anno se richiesto
    if anno:
        confs = [c for c in confs if c.anno_campagna == anno]

    cont_ids = list({c.contenitore_id for c in confs if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for ct in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[ct.id] = ct

    risultati = []
    for c in confs:
        giac = disponibili_ids.get(c.id, 0)
        cont = cont_map.get(c.contenitore_id) if c.contenitore_id else None
        risultati.append({
            "confezionamento_id": c.id,
            "codice": c.codice,
            "formato": c.formato,
            "anno_campagna": c.anno_campagna,
            "giacenza_unita": giac,
            "capacita_litri": float(c.capacita_litri),
            "prezzo_imponibile": float(c.prezzo_imponibile) if c.prezzo_imponibile else None,
            "contenitore_descrizione": cont.descrizione if cont else None,
        })

    risultati.sort(key=lambda x: (-x["anno_campagna"], x["codice"]))
    return risultati


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def magazzino_stats(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Statistiche aggregate del magazzino."""
    q = db.query(MovimentoMagazzino)
    if anno:
        q = q.filter(MovimentoMagazzino.anno_campagna == anno)

    totale_movimenti = q.count()

    totale_carichi = (
        q.filter(MovimentoMagazzino.tipo_movimento == "carico")
        .with_entities(func.sum(MovimentoMagazzino.quantita))
        .scalar() or 0
    )
    totale_scarichi = (
        q.filter(MovimentoMagazzino.tipo_movimento == "scarico")
        .with_entities(func.sum(MovimentoMagazzino.quantita))
        .scalar() or 0
    )

    # Scarichi per causale
    per_causale = {}
    causale_rows = (
        q.filter(MovimentoMagazzino.tipo_movimento == "scarico")
        .with_entities(
            MovimentoMagazzino.causale,
            func.sum(MovimentoMagazzino.quantita),
        )
        .group_by(MovimentoMagazzino.causale)
        .all()
    )
    for causale, tot in causale_rows:
        per_causale[causale] = int(tot)

    return {
        "totale_movimenti": totale_movimenti,
        "totale_carichi": int(totale_carichi),
        "totale_scarichi": int(totale_scarichi),
        "giacenza_totale_unita": int(totale_carichi) - int(totale_scarichi),
        "scarichi_per_causale": per_causale,
    }


@router.post("/sincronizza")
def sincronizza_da_confezionamenti(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Crea carichi automatici per tutti i confezionamenti che non hanno ancora
    un movimento di carico 'produzione' nel magazzino."""
    query = db.query(Confezionamento)
    if anno:
        query = query.filter(Confezionamento.anno_campagna == anno)

    confezionamenti = query.all()
    creati = 0
    aggiornati = 0

    for conf in confezionamenti:
        # Verifica se esiste gia' un carico produzione per questo confezionamento
        esistente = (
            db.query(MovimentoMagazzino)
            .filter(
                MovimentoMagazzino.confezionamento_id == conf.id,
                MovimentoMagazzino.tipo_movimento == "carico",
                MovimentoMagazzino.causale == "produzione",
            )
            .first()
        )
        if esistente:
            # Aggiorna quantita' se diversa dall'imbottigliamento
            if esistente.quantita != conf.num_unita:
                esistente.quantita = conf.num_unita
                esistente.anno_campagna = conf.anno_campagna
                aggiornati += 1
            continue

        mov = MovimentoMagazzino(
            codice=_next_codice_movimento(conf.anno_campagna, db),
            confezionamento_id=conf.id,
            tipo_movimento="carico",
            causale="produzione",
            quantita=conf.num_unita,
            data_movimento=conf.data_confezionamento,
            anno_campagna=conf.anno_campagna,
            note=f"Carico automatico da imbottigliamento {conf.codice}",
        )
        db.add(mov)
        db.flush()
        creati += 1

    db.commit()
    msg_parts = []
    if creati:
        msg_parts.append(f"{creati} nuovi carichi creati")
    if aggiornati:
        msg_parts.append(f"{aggiornati} carichi aggiornati")
    if not msg_parts:
        msg_parts.append("Magazzino gia' allineato")
    return {"sincronizzati": creati + aggiornati, "messaggio": ". ".join(msg_parts) + "."}


@router.get("/next-codice")
def next_codice(anno: int = Query(...), db: Session = Depends(get_db)):
    return {"codice": _next_codice_movimento(anno, db)}


@router.get("/anni")
def magazzino_anni(db: Session = Depends(get_db)):
    anni = (
        db.query(MovimentoMagazzino.anno_campagna)
        .distinct()
        .order_by(MovimentoMagazzino.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

@router.get("/export/csv")
def export_movimenti_csv(
    anno: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    causale: Optional[str] = Query(None),
    confezionamento_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(MovimentoMagazzino)
    if anno:
        query = query.filter(MovimentoMagazzino.anno_campagna == anno)
    if tipo:
        query = query.filter(MovimentoMagazzino.tipo_movimento == tipo)
    if causale:
        query = query.filter(MovimentoMagazzino.causale == causale)
    if confezionamento_id:
        query = query.filter(MovimentoMagazzino.confezionamento_id == confezionamento_id)

    movimenti = query.order_by(MovimentoMagazzino.data_movimento.desc()).all()

    conf_ids = list({m.confezionamento_id for m in movimenti if m.confezionamento_id})
    conf_map = {}
    if conf_ids:
        for c in db.query(Confezionamento).filter(Confezionamento.id.in_(conf_ids)).all():
            conf_map[c.id] = c
    cli_ids = list({m.cliente_id for m in movimenti if m.cliente_id})
    cli_map = {}
    if cli_ids:
        for c in db.query(Cliente).filter(Cliente.id.in_(cli_ids)).all():
            cli_map[c.id] = c

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Codice", "Data", "Tipo", "Causale", "Confezionamento", "Formato",
        "Quantita", "Cliente", "Riferimento", "Note",
    ])
    for m in movimenti:
        conf = conf_map.get(m.confezionamento_id)
        cli = cli_map.get(m.cliente_id) if m.cliente_id else None
        writer.writerow([
            m.codice, str(m.data_movimento) if m.data_movimento else "",
            m.tipo_movimento, m.causale,
            conf.codice if conf else "", conf.formato if conf else "",
            m.quantita, _cliente_denominazione(cli) or "",
            m.riferimento_documento or "", m.note or "",
        ])

    filename = f"Movimenti_{anno or 'tutti'}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/")
def list_movimenti(
    anno: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    causale: Optional[str] = Query(None),
    confezionamento_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(MovimentoMagazzino)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                MovimentoMagazzino.codice.ilike(term),
                MovimentoMagazzino.causale.ilike(term),
                MovimentoMagazzino.note.ilike(term),
            )
        )
    if anno:
        query = query.filter(MovimentoMagazzino.anno_campagna == anno)
    if tipo:
        query = query.filter(MovimentoMagazzino.tipo_movimento == tipo)
    if causale:
        query = query.filter(MovimentoMagazzino.causale == causale)
    if confezionamento_id:
        query = query.filter(MovimentoMagazzino.confezionamento_id == confezionamento_id)

    query = query.order_by(MovimentoMagazzino.data_movimento.desc())
    movimenti, total, pg, pp, pages_count = paginate(query, page, per_page)

    # Batch load relazioni (evita N+1 query)
    conf_map, cont_map, cli_map = _build_relation_maps(movimenti, db)
    items = [_build_movimento_out(m, conf_map=conf_map, cont_map=cont_map, cli_map=cli_map) for m in movimenti]
    return paginated_response(items, total, pg, pp, pages_count)


@router.get("/{mov_id}", response_model=MovimentoMagOut)
def get_movimento(mov_id: int, db: Session = Depends(get_db)):
    m = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento non trovato.")
    return _build_movimento_out(m, db)


@router.post("/", response_model=MovimentoMagOut, status_code=status.HTTP_201_CREATED)
def create_movimento(data: MovimentoMagCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Validazioni
    if data.tipo_movimento not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail=f"Tipo movimento non valido. Usa: {', '.join(TIPI_VALIDI)}")

    causali_manuali = _get_causali_valide(db, include_vendita=False)
    if data.causale not in causali_manuali:
        raise HTTPException(
            status_code=400,
            detail=f"Causale non valida. Usa: {', '.join(sorted(causali_manuali))}. "
                   "La causale 'vendita' e' riservata al modulo Vendite."
        )

    # Verifica confezionamento
    conf = db.query(Confezionamento).filter(Confezionamento.id == data.confezionamento_id).first()
    if not conf:
        raise HTTPException(status_code=400, detail="Confezionamento non trovato.")

    # Per scarichi: verifica disponibilita
    if data.tipo_movimento == "scarico":
        giacenza = _calcola_giacenza(data.confezionamento_id, db)
        if data.quantita > giacenza:
            raise HTTPException(
                status_code=400,
                detail=f"Quantita' insufficiente. Giacenza attuale: {giacenza} unita'."
            )

    # Verifica cliente se specificato
    if data.cliente_id:
        cli = db.query(Cliente).filter(Cliente.id == data.cliente_id).first()
        if not cli:
            raise HTTPException(status_code=400, detail="Cliente non trovato.")

    # Auto-genera codice
    mov_data = data.model_dump()
    if not mov_data.get("codice") or mov_data["codice"].strip() == "":
        mov_data["codice"] = _next_codice_movimento(data.anno_campagna, db)

    if db.query(MovimentoMagazzino).filter(MovimentoMagazzino.codice == mov_data["codice"]).first():
        raise HTTPException(status_code=400, detail="Codice movimento gia' esistente.")

    m = MovimentoMagazzino(**mov_data)
    db.add(m)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="movimento", entita_id=m.id, codice_entita=m.codice,
              dettagli=f"{m.tipo_movimento} {m.causale}")
    db.commit()
    db.refresh(m)
    return _build_movimento_out(m, db)


@router.put("/{mov_id}", response_model=MovimentoMagOut)
def update_movimento(mov_id: int, data: MovimentoMagUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    m = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento non trovato.")

    # Non permettere modifica di movimenti di vendita (generati dal modulo Vendite)
    if m.causale in ("vendita", "annullo_vendita"):
        raise HTTPException(status_code=400, detail="I movimenti di vendita non possono essere modificati da qui.")

    update_data = data.model_dump(exclude_unset=True)

    if "tipo_movimento" in update_data and update_data["tipo_movimento"] not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail="Tipo movimento non valido.")

    if "causale" in update_data:
        causali_manuali = _get_causali_valide(db, include_vendita=False)
        if update_data["causale"] not in causali_manuali:
            raise HTTPException(status_code=400, detail="Causale non valida.")

    if "cliente_id" in update_data and update_data["cliente_id"]:
        cli = db.query(Cliente).filter(Cliente.id == update_data["cliente_id"]).first()
        if not cli:
            raise HTTPException(status_code=400, detail="Cliente non trovato.")

    for key, value in update_data.items():
        setattr(m, key, value)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="movimento", entita_id=m.id, codice_entita=m.codice)
    db.commit()
    db.refresh(m)
    return _build_movimento_out(m, db)


@router.delete("/{mov_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movimento(mov_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    m = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento non trovato.")

    # Non permettere eliminazione di movimenti di vendita
    if m.causale in ("vendita", "annullo_vendita"):
        raise HTTPException(status_code=400, detail="I movimenti di vendita non possono essere eliminati da qui.")

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="movimento", entita_id=mov_id, codice_entita=m.codice)
    db.delete(m)
    db.commit()


# ---------------------------------------------------------------------------
# Utility interna
# ---------------------------------------------------------------------------

def _calcola_giacenza(confezionamento_id: int, db: Session) -> int:
    """Calcola la giacenza per un confezionamento specifico."""
    carichi = (
        db.query(func.sum(MovimentoMagazzino.quantita))
        .filter(
            MovimentoMagazzino.confezionamento_id == confezionamento_id,
            MovimentoMagazzino.tipo_movimento == "carico",
        )
        .scalar() or 0
    )
    scarichi = (
        db.query(func.sum(MovimentoMagazzino.quantita))
        .filter(
            MovimentoMagazzino.confezionamento_id == confezionamento_id,
            MovimentoMagazzino.tipo_movimento == "scarico",
        )
        .scalar() or 0
    )
    return int(carichi) - int(scarichi)
