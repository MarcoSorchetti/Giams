from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.raccolta_sql import Raccolta, RaccoltaParcella
from app.models.lotto_sql import LottoOlio
from app.models.parcella_sql import Parcella
from app.models.raccolta import (
    RaccoltaCreate, RaccoltaUpdate, RaccoltaOut, RaccoltaParcellaOut,
)


router = APIRouter(prefix="/raccolte", tags=["raccolte"])


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


@router.get("/", response_model=List[RaccoltaOut])
def list_raccolte(
    anno: Optional[int] = Query(None),
    parcella_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Raccolta)
    if anno:
        query = query.filter(Raccolta.anno_campagna == anno)
    if parcella_id:
        raccolta_ids = (
            db.query(RaccoltaParcella.raccolta_id)
            .filter(RaccoltaParcella.parcella_id == parcella_id)
            .subquery()
        )
        query = query.filter(Raccolta.id.in_(raccolta_ids))

    raccolte = query.order_by(Raccolta.data_raccolta.desc()).all()
    return [_build_raccolta_out(r, db) for r in raccolte]


@router.get("/{raccolta_id}", response_model=RaccoltaOut)
def get_raccolta(raccolta_id: int, db: Session = Depends(get_db)):
    r = db.query(Raccolta).filter(Raccolta.id == raccolta_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Raccolta non trovata.")
    return _build_raccolta_out(r, db)


@router.post("/", response_model=RaccoltaOut, status_code=status.HTTP_201_CREATED)
def create_raccolta(data: RaccoltaCreate, db: Session = Depends(get_db)):
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
