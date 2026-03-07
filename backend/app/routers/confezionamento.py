from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import case, func, or_

from app.database import get_db
from app.models.confezionamento_sql import Confezionamento, ConfezionamentoLotto
from app.models.contenitore_sql import Contenitore
from app.models.frantoio_sql import Frantoio
from app.models.lotto_sql import LottoOlio
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.models.vendita_sql import VenditaRiga
from app.models.confezionamento import (
    ConfezionamentoCreate, ConfezionamentoUpdate, ConfezionamentoOut,
    ConfezionamentoLottoOut,
)
from app.routers.magazzino import _next_codice_movimento
from app.models.pagination import paginate, paginated_response
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/confezionamenti", tags=["confezionamenti"])


def _build_conf_out(conf, db):
    """Costruisce ConfezionamentoOut con dettagli lotti e contenitore."""
    dettagli = (
        db.query(ConfezionamentoLotto, LottoOlio.codice_lotto)
        .join(LottoOlio, ConfezionamentoLotto.lotto_id == LottoOlio.id)
        .filter(ConfezionamentoLotto.confezionamento_id == conf.id)
        .all()
    )
    lotti_out = [
        ConfezionamentoLottoOut(
            id=cl.id,
            lotto_id=cl.lotto_id,
            litri_utilizzati=float(cl.litri_utilizzati),
            lotto_codice=codice,
        )
        for cl, codice in dettagli
    ]

    contenitore_desc = None
    contenitore_foto = None
    if conf.contenitore_id:
        cont = db.query(Contenitore).filter(Contenitore.id == conf.contenitore_id).first()
        if cont:
            contenitore_desc = cont.descrizione
            contenitore_foto = cont.foto

    frantoio_den = None
    if conf.frantoio_id:
        fr = db.query(Frantoio).filter(Frantoio.id == conf.frantoio_id).first()
        if fr:
            frantoio_den = fr.denominazione

    return ConfezionamentoOut(
        id=conf.id,
        codice=conf.codice,
        data_confezionamento=conf.data_confezionamento,
        anno_campagna=conf.anno_campagna,
        contenitore_id=conf.contenitore_id or 0,
        frantoio_id=conf.frantoio_id,
        contenitore_descrizione=contenitore_desc,
        contenitore_foto=contenitore_foto,
        frantoio_denominazione=frantoio_den,
        formato=conf.formato,
        capacita_litri=float(conf.capacita_litri),
        num_unita=conf.num_unita,
        litri_totali=float(conf.litri_totali),
        prezzo_imponibile=float(conf.prezzo_imponibile) if conf.prezzo_imponibile else None,
        iva_percentuale=float(conf.iva_percentuale) if conf.iva_percentuale is not None else 4,
        importo_iva=float(conf.importo_iva) if conf.importo_iva else None,
        prezzo_listino=float(conf.prezzo_listino) if conf.prezzo_listino else None,
        note=conf.note,
        lotti=lotti_out,
        created_at=conf.created_at,
        updated_at=conf.updated_at,
    )


@router.get("/stats")
def confezionamenti_stats(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Confezionamento)
    if anno:
        query = query.filter(Confezionamento.anno_campagna == anno)

    totale = query.count()
    unita = query.with_entities(func.sum(Confezionamento.num_unita)).scalar() or 0
    litri = query.with_entities(func.sum(Confezionamento.litri_totali)).scalar() or 0

    # Valore produzione totale (num_unita * prezzo_listino)
    valore_produzione = (
        query.with_entities(
            func.sum(Confezionamento.num_unita * Confezionamento.prezzo_listino)
        ).scalar() or 0
    )

    # Per-formato: unita + valore produzione
    formato_rows = (
        query.with_entities(
            Confezionamento.contenitore_id,
            Confezionamento.formato,
            func.sum(Confezionamento.num_unita),
            func.sum(Confezionamento.num_unita * Confezionamento.prezzo_listino),
        )
        .group_by(Confezionamento.contenitore_id, Confezionamento.formato)
        .all()
    )

    # Giacenza per confezionamento (carico - scarico)
    mov_q = db.query(
        MovimentoMagazzino.confezionamento_id,
        func.sum(case(
            (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
            else_=0,
        )).label("carichi"),
        func.sum(case(
            (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
            else_=0,
        )).label("scarichi"),
    ).group_by(MovimentoMagazzino.confezionamento_id)

    if anno:
        mov_q = mov_q.filter(MovimentoMagazzino.anno_campagna == anno)

    # Mappa confezionamento_id -> giacenza unita
    giacenza_per_conf = {}
    for conf_id, carichi, scarichi in mov_q.all():
        giacenza_per_conf[conf_id] = int(carichi) - int(scarichi)

    # Mappa confezionamento_id -> (contenitore_id, prezzo_listino)
    conf_list = query.all()
    conf_info = {c.id: c for c in conf_list}

    # Aggrega giacenza e valore per contenitore_id
    giacenza_per_formato = {}  # contenitore_id -> {unita, valore}
    for conf_id, giac_unita in giacenza_per_conf.items():
        c = conf_info.get(conf_id)
        if not c or giac_unita <= 0:
            continue
        key = c.contenitore_id or 0
        if key not in giacenza_per_formato:
            giacenza_per_formato[key] = {"unita": 0, "valore": 0}
        giacenza_per_formato[key]["unita"] += giac_unita
        prezzo = float(c.prezzo_listino) if c.prezzo_listino else 0
        giacenza_per_formato[key]["valore"] += round(giac_unita * prezzo, 2)

    # Contenitore descrizioni
    cont_ids = list({c.contenitore_id for c in conf_list if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for ct in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[ct.id] = ct.descrizione

    valore_giacenza = sum(g["valore"] for g in giacenza_per_formato.values())
    giacenza_unita = sum(g["unita"] for g in giacenza_per_formato.values())

    per_formato = []
    for cont_id, formato, prod_unita, prod_valore in formato_rows:
        giac = giacenza_per_formato.get(cont_id or 0, {"unita": 0, "valore": 0})
        per_formato.append({
            "contenitore_id": cont_id,
            "formato": formato,
            "descrizione": cont_map.get(cont_id, formato),
            "produzione_unita": int(prod_unita or 0),
            "produzione_valore": round(float(prod_valore or 0), 2),
            "giacenza_unita": giac["unita"],
            "giacenza_valore": round(giac["valore"], 2),
        })

    return {
        "totale_confezionamenti": totale,
        "totale_unita": int(unita),
        "totale_litri": float(litri),
        "valore_produzione": round(float(valore_produzione), 2),
        "giacenza_unita": giacenza_unita,
        "valore_giacenza": round(valore_giacenza, 2),
        "per_formato": per_formato,
    }


@router.get("/anni")
def confezionamenti_anni(db: Session = Depends(get_db)):
    anni = (
        db.query(Confezionamento.anno_campagna)
        .distinct()
        .order_by(Confezionamento.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


# ---------------------------------------------------------------------------
# Listino Prezzi
# ---------------------------------------------------------------------------

@router.get("/listino")
def get_listino(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Restituisce il listino prezzi per una campagna (tutti i confezionamenti con prezzo)."""
    query = db.query(Confezionamento).filter(Confezionamento.prezzo_listino.isnot(None))
    if anno:
        query = query.filter(Confezionamento.anno_campagna == anno)
    query = query.order_by(Confezionamento.formato, Confezionamento.capacita_litri)

    confs = query.all()

    # Contenitori
    cont_ids = list({c.contenitore_id for c in confs if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for ct in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[ct.id] = ct.descrizione

    # Giacenza per confezionamento
    conf_ids = [c.id for c in confs]
    giacenza_map = {}
    if conf_ids:
        mov_rows = (
            db.query(
                MovimentoMagazzino.confezionamento_id,
                func.sum(case(
                    (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                    else_=0,
                )),
                func.sum(case(
                    (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                    else_=0,
                )),
            )
            .filter(MovimentoMagazzino.confezionamento_id.in_(conf_ids))
            .group_by(MovimentoMagazzino.confezionamento_id)
            .all()
        )
        for cid, carichi, scarichi in mov_rows:
            giacenza_map[cid] = int(carichi) - int(scarichi)

    result = []
    for c in confs:
        result.append({
            "id": c.id,
            "codice": c.codice,
            "formato": c.formato,
            "contenitore": cont_map.get(c.contenitore_id, c.formato),
            "contenitore_id": c.contenitore_id,
            "capacita_litri": float(c.capacita_litri),
            "prezzo_listino": float(c.prezzo_listino) if c.prezzo_listino else None,
            "prezzo_imponibile": float(c.prezzo_imponibile) if c.prezzo_imponibile else None,
            "iva_percentuale": float(c.iva_percentuale) if c.iva_percentuale is not None else 4,
            "importo_iva": float(c.importo_iva) if c.importo_iva else None,
            "anno_campagna": c.anno_campagna,
            "giacenza_unita": giacenza_map.get(c.id, 0),
        })
    return result


@router.get("/listino/pdf")
def download_listino_pdf(
    anno: int = Query(..., description="Anno campagna"),
    db: Session = Depends(get_db),
):
    """Genera e scarica il PDF del listino prezzi per la campagna indicata."""
    from app.services.pdf_listino import genera_listino_pdf
    from app.models.campagna_sql import Campagna

    query = (
        db.query(Confezionamento)
        .filter(Confezionamento.anno_campagna == anno)
        .filter(Confezionamento.prezzo_listino.isnot(None))
        .order_by(Confezionamento.formato, Confezionamento.capacita_litri)
    )
    confs = query.all()

    cont_ids = list({c.contenitore_id for c in confs if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for ct in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[ct.id] = ct.descrizione

    prodotti = []
    for c in confs:
        prodotti.append({
            "codice": c.codice,
            "formato": c.formato,
            "contenitore": cont_map.get(c.contenitore_id, c.formato),
            "capacita_litri": float(c.capacita_litri),
            "prezzo_listino": float(c.prezzo_listino) if c.prezzo_listino else None,
            "prezzo_imponibile": float(c.prezzo_imponibile) if c.prezzo_imponibile else None,
            "iva_percentuale": float(c.iva_percentuale) if c.iva_percentuale is not None else 4,
            "importo_iva": float(c.importo_iva) if c.importo_iva else None,
        })

    # Recupera info campagna per l'intestazione PDF
    campagna_info = {}
    camp = db.query(Campagna).filter(Campagna.anno == anno).first()
    if camp:
        campagna_info = {
            "stato": camp.stato,
            "data_inizio": camp.data_inizio.strftime("%d/%m/%Y") if camp.data_inizio else None,
            "data_fine": camp.data_fine.strftime("%d/%m/%Y") if camp.data_fine else None,
        }

    pdf_bytes = genera_listino_pdf(anno, prodotti, campagna_info=campagna_info)
    filename = f"Listino_Prezzi_{anno}_{anno + 1}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/")
def list_confezionamenti(
    anno: Optional[int] = Query(None),
    formato: Optional[str] = Query(None),
    contenitore_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Confezionamento)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Confezionamento.codice.ilike(term),
                Confezionamento.formato.ilike(term),
            )
        )
    if anno:
        query = query.filter(Confezionamento.anno_campagna == anno)
    if formato:
        query = query.filter(Confezionamento.formato == formato)
    if contenitore_id:
        query = query.filter(Confezionamento.contenitore_id == contenitore_id)

    query = query.order_by(Confezionamento.data_confezionamento.desc())
    confs, total, pg, pp, pages_count = paginate(query, page, per_page)
    if not confs:
        return paginated_response([], total, pg, pp, pages_count)

    conf_ids = [c.id for c in confs]

    # Pre-carica lotti per tutti i confezionamenti
    all_cl = (
        db.query(ConfezionamentoLotto, LottoOlio.codice_lotto)
        .join(LottoOlio, ConfezionamentoLotto.lotto_id == LottoOlio.id)
        .filter(ConfezionamentoLotto.confezionamento_id.in_(conf_ids))
        .all()
    )
    lotti_map = {}
    for cl, codice in all_cl:
        lotti_map.setdefault(cl.confezionamento_id, []).append(
            ConfezionamentoLottoOut(
                id=cl.id, lotto_id=cl.lotto_id,
                litri_utilizzati=float(cl.litri_utilizzati),
                lotto_codice=codice,
            )
        )

    # Pre-carica contenitori
    cont_ids = list({c.contenitore_id for c in confs if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for cont in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[cont.id] = cont

    # Pre-carica frantoi
    frantoio_ids = list({c.frantoio_id for c in confs if c.frantoio_id})
    frantoi_map = {}
    if frantoio_ids:
        for fr in db.query(Frantoio).filter(Frantoio.id.in_(frantoio_ids)).all():
            frantoi_map[fr.id] = fr.denominazione

    # Giacenza per confezionamento (carico - scarico)
    giacenza_map = {}
    if conf_ids:
        mov_rows = (
            db.query(
                MovimentoMagazzino.confezionamento_id,
                func.sum(case(
                    (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                    else_=0,
                )),
                func.sum(case(
                    (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                    else_=0,
                )),
            )
            .filter(MovimentoMagazzino.confezionamento_id.in_(conf_ids))
            .group_by(MovimentoMagazzino.confezionamento_id)
            .all()
        )
        for cid, carichi, scarichi in mov_rows:
            giacenza_map[cid] = int(carichi) - int(scarichi)

    result = []
    for conf in confs:
        cont = cont_map.get(conf.contenitore_id) if conf.contenitore_id else None
        result.append(ConfezionamentoOut(
            id=conf.id, codice=conf.codice,
            data_confezionamento=conf.data_confezionamento,
            anno_campagna=conf.anno_campagna,
            contenitore_id=conf.contenitore_id or 0,
            frantoio_id=conf.frantoio_id,
            contenitore_descrizione=cont.descrizione if cont else None,
            contenitore_foto=cont.foto if cont else None,
            frantoio_denominazione=frantoi_map.get(conf.frantoio_id) if conf.frantoio_id else None,
            formato=conf.formato,
            capacita_litri=float(conf.capacita_litri),
            num_unita=conf.num_unita,
            litri_totali=float(conf.litri_totali),
            prezzo_imponibile=float(conf.prezzo_imponibile) if conf.prezzo_imponibile else None,
            iva_percentuale=float(conf.iva_percentuale) if conf.iva_percentuale is not None else 4,
            importo_iva=float(conf.importo_iva) if conf.importo_iva else None,
            prezzo_listino=float(conf.prezzo_listino) if conf.prezzo_listino else None,
            giacenza_unita=giacenza_map.get(conf.id),
            note=conf.note, lotti=lotti_map.get(conf.id, []),
            created_at=conf.created_at, updated_at=conf.updated_at,
        ))
    return paginated_response(result, total, pg, pp, pages_count)


@router.get("/{conf_id}", response_model=ConfezionamentoOut)
def get_confezionamento(conf_id: int, db: Session = Depends(get_db)):
    c = db.query(Confezionamento).filter(Confezionamento.id == conf_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confezionamento non trovato.")
    return _build_conf_out(c, db)


@router.post("/", response_model=ConfezionamentoOut, status_code=status.HTTP_201_CREATED)
def create_confezionamento(data: ConfezionamentoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Confezionamento).filter(Confezionamento.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice confezionamento gia' esistente.")

    cont = db.query(Contenitore).filter(Contenitore.id == data.contenitore_id).first()
    if not cont:
        raise HTTPException(status_code=400, detail="Contenitore non trovato.")

    lotti_data = data.lotti
    conf_dict = data.model_dump(exclude={"lotti"})
    # Ricalcola imponibile e IVA dal prezzo listino ivato
    if conf_dict.get("prezzo_listino") is not None:
        listino = conf_dict["prezzo_listino"]
        iva_pct = conf_dict.get("iva_percentuale") or 4
        conf_dict["prezzo_imponibile"] = round(listino / (1 + iva_pct / 100), 2)
        conf_dict["importo_iva"] = round(listino - conf_dict["prezzo_imponibile"], 2)
    c = Confezionamento(**conf_dict)
    db.add(c)
    db.flush()

    for ld in lotti_data:
        lotto = db.query(LottoOlio).filter(LottoOlio.id == ld.lotto_id).first()
        if not lotto:
            raise HTTPException(status_code=400, detail=f"Lotto {ld.lotto_id} non trovato.")
        cl = ConfezionamentoLotto(
            confezionamento_id=c.id,
            lotto_id=ld.lotto_id,
            litri_utilizzati=ld.litri_utilizzati,
        )
        db.add(cl)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="confezionamento", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)

    # --- Carico automatico in magazzino ---
    mov = MovimentoMagazzino(
        codice=_next_codice_movimento(c.anno_campagna, db),
        confezionamento_id=c.id,
        tipo_movimento="carico",
        causale="produzione",
        quantita=c.num_unita,
        data_movimento=c.data_confezionamento,
        anno_campagna=c.anno_campagna,
        note=f"Carico automatico da imbottigliamento {c.codice}",
    )
    db.add(mov)
    db.commit()

    return _build_conf_out(c, db)


@router.put("/{conf_id}", response_model=ConfezionamentoOut)
def update_confezionamento(conf_id: int, data: ConfezionamentoUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(Confezionamento).filter(Confezionamento.id == conf_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confezionamento non trovato.")

    update_data = data.model_dump(exclude_unset=True)
    lotti_data = update_data.pop("lotti", None)

    if "codice" in update_data and update_data["codice"] != c.codice:
        if db.query(Confezionamento).filter(Confezionamento.codice == update_data["codice"], Confezionamento.id != conf_id).first():
            raise HTTPException(status_code=400, detail="Codice confezionamento gia' esistente.")

    if "contenitore_id" in update_data:
        cont = db.query(Contenitore).filter(Contenitore.id == update_data["contenitore_id"]).first()
        if not cont:
            raise HTTPException(status_code=400, detail="Contenitore non trovato.")

    for key, value in update_data.items():
        setattr(c, key, value)

    # Ricalcola imponibile e IVA dal prezzo listino ivato
    if c.prezzo_listino is not None:
        listino = float(c.prezzo_listino)
        iva_pct = float(c.iva_percentuale) if c.iva_percentuale is not None else 4
        c.prezzo_imponibile = round(listino / (1 + iva_pct / 100), 2)
        c.importo_iva = round(listino - float(c.prezzo_imponibile), 2)

    if lotti_data is not None:
        # Verifica che tutti i lotti esistano
        if lotti_data:
            lotto_ids = [ld["lotto_id"] for ld in lotti_data]
            existing = {row[0] for row in db.query(LottoOlio.id).filter(LottoOlio.id.in_(lotto_ids)).all()}
            missing = set(lotto_ids) - existing
            if missing:
                raise HTTPException(status_code=400, detail=f"Lotti non trovati: {missing}")

        db.query(ConfezionamentoLotto).filter(ConfezionamentoLotto.confezionamento_id == conf_id).delete()
        for ld in lotti_data:
            cl = ConfezionamentoLotto(
                confezionamento_id=conf_id,
                lotto_id=ld["lotto_id"],
                litri_utilizzati=ld["litri_utilizzati"],
            )
            db.add(cl)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="confezionamento", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)
    return _build_conf_out(c, db)


@router.delete("/{conf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_confezionamento(conf_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(Confezionamento).filter(Confezionamento.id == conf_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confezionamento non trovato.")

    # Verifica dipendenze
    if db.query(VenditaRiga).filter(VenditaRiga.confezionamento_id == conf_id).first():
        raise HTTPException(status_code=400, detail="Impossibile eliminare: il confezionamento ha righe vendita associate.")
    if db.query(MovimentoMagazzino).filter(MovimentoMagazzino.confezionamento_id == conf_id).first():
        raise HTTPException(status_code=400, detail="Impossibile eliminare: il confezionamento ha movimenti magazzino associati.")

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="confezionamento", entita_id=conf_id, codice_entita=c.codice)
    db.query(ConfezionamentoLotto).filter(ConfezionamentoLotto.confezionamento_id == conf_id).delete()
    db.delete(c)
    db.commit()
