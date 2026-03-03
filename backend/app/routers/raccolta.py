from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.raccolta_sql import Raccolta, RaccoltaParcella
from app.models.lotto_sql import LottoOlio
from app.models.parcella_sql import Parcella
from app.models.raccolta import (
    RaccoltaCreate, RaccoltaUpdate, RaccoltaOut, RaccoltaParcellaOut,
)
from app.models.pagination import paginate, paginated_response


router = APIRouter(prefix="/raccolte", tags=["raccolte"])


def _next_codice_raccolta(anno: int, db: Session) -> str:
    """Genera il prossimo codice raccolta: R/001/2025, R/002/2025, ..."""
    prefix = f"R/"
    suffix = f"/{anno}"
    last = (
        db.query(Raccolta)
        .filter(Raccolta.codice.like(f"R/%/{anno}"))
        .order_by(Raccolta.codice.desc())
        .first()
    )
    if last:
        try:
            num = int(last.codice.split("/")[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"{prefix}{num:03d}{suffix}"


def _build_raccolta_out(raccolta, db):
    """Costruisce RaccoltaOut con dettagli parcelle, flag lotto e resa."""
    dettagli = (
        db.query(RaccoltaParcella, Parcella.codice, Parcella.nome)
        .join(Parcella, RaccoltaParcella.parcella_id == Parcella.id)
        .filter(RaccoltaParcella.raccolta_id == raccolta.id)
        .all()
    )
    parcelle_out = [
        RaccoltaParcellaOut(
            id=rp.id,
            parcella_id=rp.parcella_id,
            kg_olive=float(rp.kg_olive),
            parcella_codice=codice,
            parcella_nome=nome,
        )
        for rp, codice, nome in dettagli
    ]
    lotto = db.query(LottoOlio).filter(LottoOlio.raccolta_id == raccolta.id).first()
    return RaccoltaOut(
        id=raccolta.id,
        codice=raccolta.codice,
        data_raccolta=raccolta.data_raccolta,
        anno_campagna=raccolta.anno_campagna,
        kg_olive_totali=float(raccolta.kg_olive_totali),
        metodo_raccolta=raccolta.metodo_raccolta,
        maturazione=raccolta.maturazione,
        num_operai=raccolta.num_operai,
        ore_lavoro=float(raccolta.ore_lavoro) if raccolta.ore_lavoro else None,
        costo_manodopera=float(raccolta.costo_manodopera) if raccolta.costo_manodopera else None,
        costo_noleggio=float(raccolta.costo_noleggio) if raccolta.costo_noleggio else None,
        costo_totale_raccolta=float(raccolta.costo_totale_raccolta) if raccolta.costo_totale_raccolta else None,
        note=raccolta.note,
        parcelle=parcelle_out,
        ha_lotto=lotto is not None,
        lotto_litri=float(lotto.litri_olio) if lotto else None,
        lotto_kg_olio=float(lotto.kg_olio) if lotto and lotto.kg_olio else None,
        lotto_resa=float(lotto.resa_percentuale) if lotto and lotto.resa_percentuale else None,
        created_at=raccolta.created_at,
        updated_at=raccolta.updated_at,
    )


@router.get("/next-codice")
def next_codice_raccolta(anno: int = Query(...), db: Session = Depends(get_db)):
    """Restituisce il prossimo codice raccolta per l'anno indicato."""
    return {"codice": _next_codice_raccolta(anno, db)}


@router.get("/stats")
def raccolte_stats(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Raccolta)
    if anno:
        query = query.filter(Raccolta.anno_campagna == anno)

    totale = query.count()
    kg = query.with_entities(func.sum(Raccolta.kg_olive_totali)).scalar() or 0
    costo = query.with_entities(func.sum(Raccolta.costo_totale_raccolta)).scalar() or 0

    return {
        "totale_raccolte": totale,
        "totale_kg": float(kg),
        "media_kg": round(float(kg) / totale, 1) if totale > 0 else 0,
        "costo_totale": float(costo),
    }


@router.get("/anni")
def raccolte_anni(db: Session = Depends(get_db)):
    """Restituisce gli anni campagna disponibili nelle raccolte."""
    anni = (
        db.query(Raccolta.anno_campagna)
        .distinct()
        .order_by(Raccolta.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


@router.get("/")
def list_raccolte(
    anno: Optional[int] = Query(None),
    parcella_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Raccolta)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Raccolta.codice.ilike(term),
            )
        )
    if anno:
        query = query.filter(Raccolta.anno_campagna == anno)
    if parcella_id:
        sub_ids = (
            db.query(RaccoltaParcella.raccolta_id)
            .filter(RaccoltaParcella.parcella_id == parcella_id)
            .subquery()
        )
        query = query.filter(Raccolta.id.in_(sub_ids))

    query = query.order_by(Raccolta.data_raccolta.desc())
    raccolte, total, pg, pp, pages = paginate(query, page, per_page)
    if not raccolte:
        return paginated_response([], total, pg, pp, pages)

    raccolta_ids = [r.id for r in raccolte]

    # Pre-carica parcelle per tutte le raccolte
    all_dettagli = (
        db.query(RaccoltaParcella, Parcella.codice, Parcella.nome)
        .join(Parcella, RaccoltaParcella.parcella_id == Parcella.id)
        .filter(RaccoltaParcella.raccolta_id.in_(raccolta_ids))
        .all()
    )
    parcelle_map = {}
    for rp, codice, nome in all_dettagli:
        parcelle_map.setdefault(rp.raccolta_id, []).append(
            RaccoltaParcellaOut(
                id=rp.id, parcella_id=rp.parcella_id,
                kg_olive=float(rp.kg_olive),
                parcella_codice=codice, parcella_nome=nome,
            )
        )

    # Pre-carica lotti per tutte le raccolte
    all_lotti = db.query(LottoOlio).filter(LottoOlio.raccolta_id.in_(raccolta_ids)).all()
    lotti_map = {l.raccolta_id: l for l in all_lotti}

    result = []
    for r in raccolte:
        lotto = lotti_map.get(r.id)
        result.append(RaccoltaOut(
            id=r.id, codice=r.codice, data_raccolta=r.data_raccolta,
            anno_campagna=r.anno_campagna,
            kg_olive_totali=float(r.kg_olive_totali),
            metodo_raccolta=r.metodo_raccolta, maturazione=r.maturazione,
            num_operai=r.num_operai,
            ore_lavoro=float(r.ore_lavoro) if r.ore_lavoro else None,
            costo_manodopera=float(r.costo_manodopera) if r.costo_manodopera else None,
            costo_noleggio=float(r.costo_noleggio) if r.costo_noleggio else None,
            costo_totale_raccolta=float(r.costo_totale_raccolta) if r.costo_totale_raccolta else None,
            note=r.note, parcelle=parcelle_map.get(r.id, []),
            ha_lotto=lotto is not None,
            lotto_litri=float(lotto.litri_olio) if lotto else None,
            lotto_kg_olio=float(lotto.kg_olio) if lotto and lotto.kg_olio else None,
            lotto_resa=float(lotto.resa_percentuale) if lotto and lotto.resa_percentuale else None,
            created_at=r.created_at, updated_at=r.updated_at,
        ))
    return paginated_response(result, total, pg, pp, pages)


@router.get("/{raccolta_id}", response_model=RaccoltaOut)
def get_raccolta(raccolta_id: int, db: Session = Depends(get_db)):
    r = db.query(Raccolta).filter(Raccolta.id == raccolta_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Raccolta non trovata.")
    return _build_raccolta_out(r, db)


@router.post("/", response_model=RaccoltaOut, status_code=status.HTTP_201_CREATED)
def create_raccolta(data: RaccoltaCreate, db: Session = Depends(get_db)):
    # Auto-genera codice se non fornito
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_raccolta(data.anno_campagna, db)

    if db.query(Raccolta).filter(Raccolta.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice raccolta gia' esistente.")

    parcelle_data = data.parcelle
    raccolta_dict = data.model_dump(exclude={"parcelle"})
    r = Raccolta(**raccolta_dict)
    db.add(r)
    db.flush()

    for pd in parcelle_data:
        rp = RaccoltaParcella(raccolta_id=r.id, parcella_id=pd.parcella_id, kg_olive=pd.kg_olive)
        db.add(rp)

    db.commit()
    db.refresh(r)
    return _build_raccolta_out(r, db)


@router.put("/{raccolta_id}", response_model=RaccoltaOut)
def update_raccolta(raccolta_id: int, data: RaccoltaUpdate, db: Session = Depends(get_db)):
    r = db.query(Raccolta).filter(Raccolta.id == raccolta_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Raccolta non trovata.")

    update_data = data.model_dump(exclude_unset=True)
    parcelle_data = update_data.pop("parcelle", None)

    if "codice" in update_data and update_data["codice"] != r.codice:
        if db.query(Raccolta).filter(Raccolta.codice == update_data["codice"], Raccolta.id != raccolta_id).first():
            raise HTTPException(status_code=400, detail="Codice raccolta gia' esistente.")

    for key, value in update_data.items():
        setattr(r, key, value)

    if parcelle_data is not None:
        db.query(RaccoltaParcella).filter(RaccoltaParcella.raccolta_id == raccolta_id).delete()
        for pd in parcelle_data:
            rp = RaccoltaParcella(
                raccolta_id=raccolta_id,
                parcella_id=pd["parcella_id"],
                kg_olive=pd["kg_olive"],
            )
            db.add(rp)

    db.commit()
    db.refresh(r)
    return _build_raccolta_out(r, db)


@router.delete("/{raccolta_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_raccolta(raccolta_id: int, db: Session = Depends(get_db)):
    r = db.query(Raccolta).filter(Raccolta.id == raccolta_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Raccolta non trovata.")
    db.query(RaccoltaParcella).filter(RaccoltaParcella.raccolta_id == raccolta_id).delete()
    lotto = db.query(LottoOlio).filter(LottoOlio.raccolta_id == raccolta_id).first()
    if lotto:
        db.delete(lotto)
    db.delete(r)
    db.commit()
