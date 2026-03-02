from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.confezionamento_sql import Confezionamento, ConfezionamentoLotto
from app.models.contenitore_sql import Contenitore
from app.models.lotto_sql import LottoOlio
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.models.confezionamento import (
    ConfezionamentoCreate, ConfezionamentoUpdate, ConfezionamentoOut,
    ConfezionamentoLottoOut,
)
from app.routers.magazzino import _next_codice_movimento


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

    return ConfezionamentoOut(
        id=conf.id,
        codice=conf.codice,
        data_confezionamento=conf.data_confezionamento,
        anno_campagna=conf.anno_campagna,
        contenitore_id=conf.contenitore_id or 0,
        contenitore_descrizione=contenitore_desc,
        contenitore_foto=contenitore_foto,
        formato=conf.formato,
        capacita_litri=float(conf.capacita_litri),
        num_unita=conf.num_unita,
        litri_totali=float(conf.litri_totali),
        costo_totale=float(conf.costo_totale) if conf.costo_totale else None,
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
    costo = query.with_entities(func.sum(Confezionamento.costo_totale)).scalar() or 0

    per_formato = {}
    formato_rows = (
        query.with_entities(
            Confezionamento.formato,
            func.sum(Confezionamento.num_unita),
        )
        .group_by(Confezionamento.formato)
        .all()
    )
    for row in formato_rows:
        per_formato[row[0]] = int(row[1])

    return {
        "totale_confezionamenti": totale,
        "totale_unita": int(unita),
        "totale_litri": float(litri),
        "costo_totale": float(costo),
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


@router.get("/", response_model=List[ConfezionamentoOut])
def list_confezionamenti(
    anno: Optional[int] = Query(None),
    formato: Optional[str] = Query(None),
    contenitore_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Confezionamento)
    if anno:
        query = query.filter(Confezionamento.anno_campagna == anno)
    if formato:
        query = query.filter(Confezionamento.formato == formato)
    if contenitore_id:
        query = query.filter(Confezionamento.contenitore_id == contenitore_id)

    confs = query.order_by(Confezionamento.data_confezionamento.desc()).all()
    return [_build_conf_out(c, db) for c in confs]


@router.get("/{conf_id}", response_model=ConfezionamentoOut)
def get_confezionamento(conf_id: int, db: Session = Depends(get_db)):
    c = db.query(Confezionamento).filter(Confezionamento.id == conf_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confezionamento non trovato.")
    return _build_conf_out(c, db)


@router.post("/", response_model=ConfezionamentoOut, status_code=status.HTTP_201_CREATED)
def create_confezionamento(data: ConfezionamentoCreate, db: Session = Depends(get_db)):
    if db.query(Confezionamento).filter(Confezionamento.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice confezionamento gia' esistente.")

    cont = db.query(Contenitore).filter(Contenitore.id == data.contenitore_id).first()
    if not cont:
        raise HTTPException(status_code=400, detail="Contenitore non trovato.")

    lotti_data = data.lotti
    conf_dict = data.model_dump(exclude={"lotti"})
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
def update_confezionamento(conf_id: int, data: ConfezionamentoUpdate, db: Session = Depends(get_db)):
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

    if lotti_data is not None:
        db.query(ConfezionamentoLotto).filter(ConfezionamentoLotto.confezionamento_id == conf_id).delete()
        for ld in lotti_data:
            cl = ConfezionamentoLotto(
                confezionamento_id=conf_id,
                lotto_id=ld["lotto_id"],
                litri_utilizzati=ld["litri_utilizzati"],
            )
            db.add(cl)

    db.commit()
    db.refresh(c)
    return _build_conf_out(c, db)


@router.delete("/{conf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_confezionamento(conf_id: int, db: Session = Depends(get_db)):
    c = db.query(Confezionamento).filter(Confezionamento.id == conf_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confezionamento non trovato.")
    db.query(ConfezionamentoLotto).filter(ConfezionamentoLotto.confezionamento_id == conf_id).delete()
    db.delete(c)
    db.commit()
