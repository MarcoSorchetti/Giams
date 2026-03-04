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


router = APIRouter(prefix="/magazzino", tags=["magazzino"])

TIPI_VALIDI = {"carico", "scarico"}
CAUSALI_VALIDE = {"produzione", "omaggio", "pubblicita", "scarto", "vendita"}
# Causali utilizzabili manualmente (vendita riservata al modulo Vendite)
CAUSALI_MANUALI = {"produzione", "omaggio", "pubblicita", "scarto"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_codice_movimento(anno: int, db: Session) -> str:
    """Genera il prossimo codice: MV/001/2025, MV/002/2025, ..."""
    last = (
        db.query(MovimentoMagazzino)
        .filter(MovimentoMagazzino.codice.like(f"MV/%/{anno}"))
        .order_by(MovimentoMagazzino.codice.desc())
        .first()
    )
    if last:
        try:
            num = int(last.codice.split("/")[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"MV/{num:03d}/{anno}"


def _cliente_denominazione(c):
    if not c:
        return None
    if c.tipo_cliente == "azienda":
        return c.ragione_sociale or ""
    parti = [c.nome or "", c.cognome or ""]
    return " ".join(p for p in parti if p)


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
        db.flush()  # flush per generare codice sequenziale corretto
        creati += 1

    db.commit()
    return {"sincronizzati": creati, "messaggio": f"{creati} confezionamenti caricati in magazzino."}


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
def create_movimento(data: MovimentoMagCreate, db: Session = Depends(get_db)):
    # Validazioni
    if data.tipo_movimento not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail=f"Tipo movimento non valido. Usa: {', '.join(TIPI_VALIDI)}")

    if data.causale not in CAUSALI_MANUALI:
        raise HTTPException(
            status_code=400,
            detail=f"Causale non valida. Usa: {', '.join(CAUSALI_MANUALI)}. "
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
    db.commit()
    db.refresh(m)
    return _build_movimento_out(m, db)


@router.put("/{mov_id}", response_model=MovimentoMagOut)
def update_movimento(mov_id: int, data: MovimentoMagUpdate, db: Session = Depends(get_db)):
    m = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento non trovato.")

    # Non permettere modifica di movimenti di vendita (generati dal modulo Vendite)
    if m.causale == "vendita":
        raise HTTPException(status_code=400, detail="I movimenti di vendita non possono essere modificati da qui.")

    update_data = data.model_dump(exclude_unset=True)

    if "tipo_movimento" in update_data and update_data["tipo_movimento"] not in TIPI_VALIDI:
        raise HTTPException(status_code=400, detail="Tipo movimento non valido.")

    if "causale" in update_data and update_data["causale"] not in CAUSALI_MANUALI:
        raise HTTPException(status_code=400, detail="Causale non valida.")

    if "cliente_id" in update_data and update_data["cliente_id"]:
        cli = db.query(Cliente).filter(Cliente.id == update_data["cliente_id"]).first()
        if not cli:
            raise HTTPException(status_code=400, detail="Cliente non trovato.")

    for key, value in update_data.items():
        setattr(m, key, value)

    db.commit()
    db.refresh(m)
    return _build_movimento_out(m, db)


@router.delete("/{mov_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movimento(mov_id: int, db: Session = Depends(get_db)):
    m = db.query(MovimentoMagazzino).filter(MovimentoMagazzino.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento non trovato.")

    # Non permettere eliminazione di movimenti di vendita
    if m.causale == "vendita":
        raise HTTPException(status_code=400, detail="I movimenti di vendita non possono essere eliminati da qui.")

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
