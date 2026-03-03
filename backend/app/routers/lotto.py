from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.lotto_sql import LottoOlio
from app.models.raccolta_sql import Raccolta
from app.models.lotto import LottoCreate, LottoUpdate, LottoOut
from app.models.pagination import paginate, paginated_response


router = APIRouter(prefix="/lotti", tags=["lotti"])


def _next_codice_lotto(anno: int, db: Session) -> str:
    """Genera il prossimo codice lotto: O/001/2025, O/002/2025, ..."""
    last = (
        db.query(LottoOlio)
        .filter(LottoOlio.codice_lotto.like(f"O/%/{anno}"))
        .order_by(LottoOlio.codice_lotto.desc())
        .first()
    )
    if last:
        try:
            num = int(last.codice_lotto.split("/")[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"O/{num:03d}/{anno}"


def _build_lotto_out(lotto, db):
    """Costruisce LottoOut con codice raccolta."""
    raccolta = db.query(Raccolta).filter(Raccolta.id == lotto.raccolta_id).first()
    return LottoOut(
        id=lotto.id,
        codice_lotto=lotto.codice_lotto,
        raccolta_id=lotto.raccolta_id,
        raccolta_codice=raccolta.codice if raccolta else None,
        anno_campagna=lotto.anno_campagna,
        data_molitura=lotto.data_molitura,
        frantoio=lotto.frantoio,
        kg_olive=float(lotto.kg_olive),
        litri_olio=float(lotto.litri_olio),
        kg_olio=float(lotto.kg_olio) if lotto.kg_olio else None,
        resa_percentuale=float(lotto.resa_percentuale) if lotto.resa_percentuale else None,
        acidita=float(lotto.acidita) if lotto.acidita else None,
        perossidi=float(lotto.perossidi) if lotto.perossidi else None,
        polifenoli=lotto.polifenoli,
        tipo_olio=lotto.tipo_olio,
        certificazione=lotto.certificazione,
        costo_frantoio=float(lotto.costo_frantoio) if lotto.costo_frantoio else None,
        costo_trasporto=float(lotto.costo_trasporto) if lotto.costo_trasporto else None,
        costo_totale_molitura=float(lotto.costo_totale_molitura) if lotto.costo_totale_molitura else None,
        stato=lotto.stato,
        note=lotto.note,
        created_at=lotto.created_at,
        updated_at=lotto.updated_at,
    )


@router.get("/next-codice")
def next_codice_lotto(anno: int = Query(...), db: Session = Depends(get_db)):
    """Restituisce il prossimo codice lotto per l'anno indicato."""
    return {"codice": _next_codice_lotto(anno, db)}


@router.get("/stats")
def lotti_stats(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LottoOlio)
    if anno:
        query = query.filter(LottoOlio.anno_campagna == anno)

    totale = query.count()
    litri = query.with_entities(func.sum(LottoOlio.litri_olio)).scalar() or 0
    kg_olio = query.with_entities(func.sum(LottoOlio.kg_olio)).scalar() or 0
    kg = query.with_entities(func.sum(LottoOlio.kg_olive)).scalar() or 0
    costo = query.with_entities(func.sum(LottoOlio.costo_totale_molitura)).scalar() or 0

    resa_media = round(float(litri) / float(kg) * 100, 1) if float(kg) > 0 else 0

    per_tipo = {}
    tipo_rows = (
        query.with_entities(LottoOlio.tipo_olio, func.count(LottoOlio.id))
        .group_by(LottoOlio.tipo_olio)
        .all()
    )
    for row in tipo_rows:
        per_tipo[row[0]] = row[1]

    return {
        "totale_lotti": totale,
        "totale_kg_olive": float(kg),
        "totale_litri": float(litri),
        "totale_kg_olio": float(kg_olio),
        "resa_media": resa_media,
        "costo_totale": float(costo),
        "per_tipo": per_tipo,
    }


@router.get("/anni")
def lotti_anni(db: Session = Depends(get_db)):
    """Restituisce gli anni campagna disponibili nei lotti."""
    anni = (
        db.query(LottoOlio.anno_campagna)
        .distinct()
        .order_by(LottoOlio.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


@router.get("/")
def list_lotti(
    anno: Optional[int] = Query(None),
    tipo_olio: Optional[str] = Query(None),
    stato: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(LottoOlio)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                LottoOlio.codice_lotto.ilike(term),
                LottoOlio.tipo_olio.ilike(term),
            )
        )
    if anno:
        query = query.filter(LottoOlio.anno_campagna == anno)
    if tipo_olio:
        query = query.filter(LottoOlio.tipo_olio == tipo_olio)
    if stato:
        query = query.filter(LottoOlio.stato == stato)

    query = query.order_by(LottoOlio.data_molitura.desc())
    lotti, total, pg, pp, pages_count = paginate(query, page, per_page)
    if not lotti:
        return paginated_response([], total, pg, pp, pages_count)

    # Pre-carica raccolte in batch
    raccolta_ids = list({l.raccolta_id for l in lotti if l.raccolta_id})
    raccolte_map = {}
    if raccolta_ids:
        for r in db.query(Raccolta).filter(Raccolta.id.in_(raccolta_ids)).all():
            raccolte_map[r.id] = r

    result = []
    for lotto in lotti:
        raccolta = raccolte_map.get(lotto.raccolta_id)
        result.append(LottoOut(
            id=lotto.id, codice_lotto=lotto.codice_lotto,
            raccolta_id=lotto.raccolta_id,
            raccolta_codice=raccolta.codice if raccolta else None,
            anno_campagna=lotto.anno_campagna, data_molitura=lotto.data_molitura,
            frantoio=lotto.frantoio, kg_olive=float(lotto.kg_olive),
            litri_olio=float(lotto.litri_olio),
            kg_olio=float(lotto.kg_olio) if lotto.kg_olio else None,
            resa_percentuale=float(lotto.resa_percentuale) if lotto.resa_percentuale else None,
            acidita=float(lotto.acidita) if lotto.acidita else None,
            perossidi=float(lotto.perossidi) if lotto.perossidi else None,
            polifenoli=lotto.polifenoli, tipo_olio=lotto.tipo_olio,
            certificazione=lotto.certificazione,
            costo_frantoio=float(lotto.costo_frantoio) if lotto.costo_frantoio else None,
            costo_trasporto=float(lotto.costo_trasporto) if lotto.costo_trasporto else None,
            costo_totale_molitura=float(lotto.costo_totale_molitura) if lotto.costo_totale_molitura else None,
            stato=lotto.stato, note=lotto.note,
            created_at=lotto.created_at, updated_at=lotto.updated_at,
        ))
    return paginated_response(result, total, pg, pp, pages_count)


@router.get("/{lotto_id}", response_model=LottoOut)
def get_lotto(lotto_id: int, db: Session = Depends(get_db)):
    l = db.query(LottoOlio).filter(LottoOlio.id == lotto_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lotto non trovato.")
    return _build_lotto_out(l, db)


@router.post("/", response_model=LottoOut, status_code=status.HTTP_201_CREATED)
def create_lotto(data: LottoCreate, db: Session = Depends(get_db)):
    # Auto-genera codice se non fornito
    if not data.codice_lotto or data.codice_lotto.strip() == "":
        data.codice_lotto = _next_codice_lotto(data.anno_campagna, db)

    if db.query(LottoOlio).filter(LottoOlio.codice_lotto == data.codice_lotto).first():
        raise HTTPException(status_code=400, detail="Codice lotto gia' esistente.")

    raccolta = db.query(Raccolta).filter(Raccolta.id == data.raccolta_id).first()
    if not raccolta:
        raise HTTPException(status_code=400, detail="Raccolta non trovata.")

    existing = db.query(LottoOlio).filter(LottoOlio.raccolta_id == data.raccolta_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Questa raccolta ha gia' un lotto associato.")

    lotto_data = data.model_dump()
    if lotto_data.get("kg_olive") and lotto_data.get("litri_olio"):
        lotto_data["resa_percentuale"] = round(lotto_data["litri_olio"] / lotto_data["kg_olive"] * 100, 2)

    l = LottoOlio(**lotto_data)
    db.add(l)
    db.commit()
    db.refresh(l)
    return _build_lotto_out(l, db)


@router.put("/{lotto_id}", response_model=LottoOut)
def update_lotto(lotto_id: int, data: LottoUpdate, db: Session = Depends(get_db)):
    l = db.query(LottoOlio).filter(LottoOlio.id == lotto_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lotto non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice_lotto" in update_data and update_data["codice_lotto"] != l.codice_lotto:
        if db.query(LottoOlio).filter(LottoOlio.codice_lotto == update_data["codice_lotto"], LottoOlio.id != lotto_id).first():
            raise HTTPException(status_code=400, detail="Codice lotto gia' esistente.")

    for key, value in update_data.items():
        setattr(l, key, value)

    if l.kg_olive and l.litri_olio:
        l.resa_percentuale = round(float(l.litri_olio) / float(l.kg_olive) * 100, 2)

    db.commit()
    db.refresh(l)
    return _build_lotto_out(l, db)


@router.delete("/{lotto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lotto(lotto_id: int, db: Session = Depends(get_db)):
    l = db.query(LottoOlio).filter(LottoOlio.id == lotto_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lotto non trovato.")
    db.delete(l)
    db.commit()
