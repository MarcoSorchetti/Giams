import csv
import io
import os
import shutil
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "../../../uploads")
COSTI_DIR = os.path.join(UPLOADS_DIR, "costi")
os.makedirs(COSTI_DIR, exist_ok=True)
from app.models.costo_sql import Costo
from app.models.categoria_costo_sql import CategoriaCosto
from app.models.fornitore_sql import Fornitore
from app.models.raccolta_sql import Raccolta
from app.models.lotto_sql import LottoOlio
from app.models.costo import CostoCreate, CostoUpdate, CostoOut
from app.models.pagination import paginate, paginated_response
from app.core.security import get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/costi", tags=["costi"])


def _next_codice_costo(anno: int, db: Session) -> str:
    """Genera il prossimo codice costo: C/001/2025, C/002/2025, ..."""
    last = (
        db.query(Costo)
        .filter(Costo.codice.like(f"C/%/{anno}"))
        .order_by(Costo.codice.desc())
        .with_for_update()
        .first()
    )
    if last:
        try:
            num = int(last.codice.split("/")[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"C/{num:03d}/{anno}"


def _fornitore_denominazione(f):
    if not f:
        return None
    if f.tipo_fornitore == "azienda":
        return f.ragione_sociale or ""
    parti = [f.nome or "", f.cognome or ""]
    return " ".join(p for p in parti if p)


def _build_costo_out(costo, db):
    cat = db.query(CategoriaCosto).filter(CategoriaCosto.id == costo.categoria_id).first()
    forn = None
    if costo.fornitore_id:
        forn = db.query(Fornitore).filter(Fornitore.id == costo.fornitore_id).first()

    quota = None
    if costo.anni_ammortamento and costo.anni_ammortamento > 0:
        quota = round(float(costo.importo_totale) / costo.anni_ammortamento, 2)

    return CostoOut(
        id=costo.id,
        codice=costo.codice,
        categoria_id=costo.categoria_id,
        categoria_nome=cat.nome if cat else None,
        categoria_tipo=cat.tipo_costo if cat else None,
        anno_campagna=costo.anno_campagna,
        descrizione=costo.descrizione,
        fornitore_id=costo.fornitore_id,
        fornitore_denominazione=_fornitore_denominazione(forn),
        data_fattura=costo.data_fattura,
        numero_fattura=costo.numero_fattura,
        tipo_documento=costo.tipo_documento,
        imponibile=float(costo.imponibile),
        iva_percentuale=float(costo.iva_percentuale),
        importo_iva=float(costo.importo_iva),
        importo_totale=float(costo.importo_totale),
        data_pagamento=costo.data_pagamento,
        modalita_pagamento=costo.modalita_pagamento,
        riferimento_pagamento=costo.riferimento_pagamento,
        stato_pagamento=costo.stato_pagamento,
        anni_ammortamento=costo.anni_ammortamento,
        quota_ammortamento=quota,
        documento=costo.documento,
        note=costo.note,
        created_at=costo.created_at,
        updated_at=costo.updated_at,
    )


@router.get("/next-codice")
def next_codice_costo(anno: int = Query(...), db: Session = Depends(get_db)):
    return {"codice": _next_codice_costo(anno, db)}


@router.get("/stats")
def costi_stats(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Costo)
    if anno:
        query = query.filter(Costo.anno_campagna == anno)

    totale_count = query.count()
    totale_importo = query.with_entities(func.sum(Costo.importo_totale)).scalar() or 0

    pagati = query.filter(Costo.stato_pagamento == "pagato").with_entities(func.sum(Costo.importo_totale)).scalar() or 0
    da_pagare = query.filter(Costo.stato_pagamento == "da_pagare").with_entities(func.sum(Costo.importo_totale)).scalar() or 0

    # Per tipo
    campagna_q = query.join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id).filter(CategoriaCosto.tipo_costo == "campagna")
    strutturale_q = query.join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id).filter(CategoriaCosto.tipo_costo == "strutturale")

    totale_campagna = campagna_q.with_entities(func.sum(Costo.importo_totale)).scalar() or 0
    totale_strutturale = strutturale_q.with_entities(func.sum(Costo.importo_totale)).scalar() or 0

    return {
        "totale_count": totale_count,
        "totale_importo": float(totale_importo),
        "totale_pagati": float(pagati),
        "totale_da_pagare": float(da_pagare),
        "totale_campagna": float(totale_campagna),
        "totale_strutturale": float(totale_strutturale),
    }


@router.get("/stats/per-categoria")
def costi_per_categoria(
    anno: int = Query(...),
    db: Session = Depends(get_db),
):
    """Dettaglio costi per categoria con ammortamento strutturale."""
    categorie = []

    # Raccolta (voce campagna)
    costo_raccolta = float(
        db.query(func.sum(Raccolta.costo_totale_raccolta))
        .filter(Raccolta.anno_campagna == anno)
        .scalar() or 0
    )
    if costo_raccolta > 0:
        categorie.append({"nome": "Raccolta", "tipo": "campagna", "importo": round(costo_raccolta, 2)})

    # Molitura (voce campagna)
    costo_molitura = float(
        db.query(func.sum(LottoOlio.costo_totale_molitura))
        .filter(LottoOlio.anno_campagna == anno)
        .scalar() or 0
    )
    if costo_molitura > 0:
        categorie.append({"nome": "Molitura", "tipo": "campagna", "importo": round(costo_molitura, 2)})

    # Costi campagna per categoria (escludi Raccolta/Molitura, gia' conteggiati sopra)
    camp_rows = (
        db.query(CategoriaCosto.nome, func.sum(Costo.importo_totale))
        .join(Costo, Costo.categoria_id == CategoriaCosto.id)
        .filter(Costo.anno_campagna == anno, CategoriaCosto.tipo_costo == "campagna")
        .filter(CategoriaCosto.nome.notin_(["Raccolta", "Molitura"]))
        .group_by(CategoriaCosto.nome)
        .all()
    )
    for nome, tot in camp_rows:
        categorie.append({"nome": nome, "tipo": "campagna", "importo": round(float(tot), 2)})

    # Costi strutturali con ammortamento (competenza per anno)
    strutturali = (
        db.query(Costo, CategoriaCosto.nome.label("cat_nome"))
        .join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id)
        .filter(CategoriaCosto.tipo_costo == "strutturale")
        .all()
    )
    strut_map = {}
    for s, cat_nome in strutturali:
        competenza = 0.0
        if s.anni_ammortamento and s.anni_ammortamento > 0:
            anno_inizio = s.anno_campagna
            anno_fine = anno_inizio + s.anni_ammortamento - 1
            if anno_inizio <= anno <= anno_fine:
                competenza = float(s.importo_totale) / s.anni_ammortamento
        elif s.anno_campagna == anno:
            competenza = float(s.importo_totale)
        if competenza > 0:
            if cat_nome not in strut_map:
                strut_map[cat_nome] = 0.0
            strut_map[cat_nome] += competenza

    for nome, importo in strut_map.items():
        categorie.append({"nome": nome, "tipo": "strutturale", "importo": round(importo, 2)})

    # Totali
    tot_camp = sum(c["importo"] for c in categorie if c["tipo"] == "campagna")
    tot_strut = sum(c["importo"] for c in categorie if c["tipo"] == "strutturale")
    totale = tot_camp + tot_strut

    # Percentuali
    for c in categorie:
        c["percentuale"] = round(c["importo"] / totale * 100, 1) if totale > 0 else 0

    # Ordina per importo decrescente
    categorie.sort(key=lambda x: x["importo"], reverse=True)

    return {
        "anno": anno,
        "costi_campagna": round(tot_camp, 2),
        "costi_strutturali": round(tot_strut, 2),
        "totale": round(totale, 2),
        "categorie": categorie,
    }


@router.get("/stats/campagna")
def costi_campagna_stats(
    anno: int = Query(...),
    db: Session = Depends(get_db),
):
    """Stats aggregato: costi raccolta + molitura + costi aggiuntivi + ammortamenti."""
    # Costi raccolta
    costo_raccolta = (
        db.query(func.sum(Raccolta.costo_totale_raccolta))
        .filter(Raccolta.anno_campagna == anno)
        .scalar() or 0
    )

    # Costi molitura
    costo_molitura = (
        db.query(func.sum(LottoOlio.costo_totale_molitura))
        .filter(LottoOlio.anno_campagna == anno)
        .scalar() or 0
    )

    # Costi campagna aggiuntivi (escludi Raccolta/Molitura, gia' conteggiati sopra)
    costi_campagna = (
        db.query(func.sum(Costo.importo_totale))
        .join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id)
        .filter(Costo.anno_campagna == anno, CategoriaCosto.tipo_costo == "campagna")
        .filter(CategoriaCosto.nome.notin_(["Raccolta", "Molitura"]))
        .scalar() or 0
    )

    # Quote ammortamento strutturali attive per quest'anno
    strutturali = (
        db.query(Costo)
        .join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id)
        .filter(CategoriaCosto.tipo_costo == "strutturale", Costo.anni_ammortamento > 0)
        .all()
    )
    quota_ammortamento = 0.0
    for s in strutturali:
        anno_inizio = s.anno_campagna
        anno_fine = anno_inizio + s.anni_ammortamento - 1
        if anno_inizio <= anno <= anno_fine:
            quota_ammortamento += float(s.importo_totale) / s.anni_ammortamento

    # Strutturali con ammortamento 0 (costo intero nell'anno)
    strutturali_anno = (
        db.query(func.sum(Costo.importo_totale))
        .join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id)
        .filter(
            Costo.anno_campagna == anno,
            CategoriaCosto.tipo_costo == "strutturale",
            Costo.anni_ammortamento == 0,
        )
        .scalar() or 0
    )

    totale_produzione = (
        float(costo_raccolta)
        + float(costo_molitura)
        + float(costi_campagna)
        + round(quota_ammortamento, 2)
        + float(strutturali_anno)
    )

    return {
        "anno": anno,
        "costo_raccolta": float(costo_raccolta),
        "costo_molitura": float(costo_molitura),
        "costi_campagna": float(costi_campagna),
        "quota_ammortamento": round(quota_ammortamento, 2),
        "costi_strutturali_anno": float(strutturali_anno),
        "totale_produzione": round(totale_produzione, 2),
    }


@router.get("/anni")
def costi_anni(db: Session = Depends(get_db)):
    anni = (
        db.query(Costo.anno_campagna)
        .distinct()
        .order_by(Costo.anno_campagna.desc())
        .all()
    )
    return [a[0] for a in anni]


@router.get("/export/csv")
def export_costi_csv(
    anno: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    categoria_id: Optional[int] = Query(None),
    stato: Optional[str] = Query(None),
    fornitore_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Costo)
    if anno:
        query = query.filter(Costo.anno_campagna == anno)
    if categoria_id:
        query = query.filter(Costo.categoria_id == categoria_id)
    if stato:
        query = query.filter(Costo.stato_pagamento == stato)
    if fornitore_id:
        query = query.filter(Costo.fornitore_id == fornitore_id)
    if tipo:
        query = query.join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id).filter(CategoriaCosto.tipo_costo == tipo)

    costi = query.order_by(Costo.data_fattura.desc()).all()

    cat_ids = list({c.categoria_id for c in costi if c.categoria_id})
    forn_ids = list({c.fornitore_id for c in costi if c.fornitore_id})
    cat_map = {}
    if cat_ids:
        for cat in db.query(CategoriaCosto).filter(CategoriaCosto.id.in_(cat_ids)).all():
            cat_map[cat.id] = cat
    forn_map = {}
    if forn_ids:
        for f in db.query(Fornitore).filter(Fornitore.id.in_(forn_ids)).all():
            forn_map[f.id] = f

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Codice", "Data Fattura", "Anno", "Tipo", "Categoria", "Descrizione",
        "Fornitore", "N. Fattura", "Imponibile", "IVA %", "Importo IVA",
        "Importo Totale", "Stato Pagamento", "Data Pagamento", "Note",
    ])
    for c in costi:
        cat = cat_map.get(c.categoria_id)
        forn = forn_map.get(c.fornitore_id) if c.fornitore_id else None
        writer.writerow([
            c.codice, str(c.data_fattura) if c.data_fattura else "",
            c.anno_campagna, cat.tipo_costo if cat else "", cat.nome if cat else "",
            c.descrizione or "", _fornitore_denominazione(forn) or "",
            c.numero_fattura or "", f"{float(c.imponibile):.2f}",
            f"{float(c.iva_percentuale):.0f}", f"{float(c.importo_iva):.2f}",
            f"{float(c.importo_totale):.2f}", c.stato_pagamento or "",
            str(c.data_pagamento) if c.data_pagamento else "", c.note or "",
        ])

    filename = f"Costi_{anno or 'tutti'}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/")
def list_costi(
    anno: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    categoria_id: Optional[int] = Query(None),
    stato: Optional[str] = Query(None),
    fornitore_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("data_fattura"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Costo)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Costo.codice.ilike(term),
                Costo.descrizione.ilike(term),
                Costo.numero_fattura.ilike(term),
            )
        )
    if anno:
        query = query.filter(Costo.anno_campagna == anno)
    if categoria_id:
        query = query.filter(Costo.categoria_id == categoria_id)
    if stato:
        query = query.filter(Costo.stato_pagamento == stato)
    if fornitore_id:
        query = query.filter(Costo.fornitore_id == fornitore_id)
    if tipo:
        query = query.join(CategoriaCosto, Costo.categoria_id == CategoriaCosto.id).filter(CategoriaCosto.tipo_costo == tipo)

    # Ordinamento dinamico
    _sort_cols = {
        "codice": Costo.codice,
        "data_fattura": Costo.data_fattura,
        "descrizione": Costo.descrizione,
        "importo_totale": Costo.importo_totale,
        "stato_pagamento": Costo.stato_pagamento,
    }
    col = _sort_cols.get(sort_by, Costo.data_fattura)
    query = query.order_by(col.desc() if sort_dir == "desc" else col.asc())
    costi, total, pg, pp, pages_count = paginate(query, page, per_page)
    if not costi:
        return paginated_response([], total, pg, pp, pages_count)

    # Pre-carica categorie e fornitori in batch
    cat_ids = list({c.categoria_id for c in costi if c.categoria_id})
    forn_ids = list({c.fornitore_id for c in costi if c.fornitore_id})

    cat_map = {}
    if cat_ids:
        for cat in db.query(CategoriaCosto).filter(CategoriaCosto.id.in_(cat_ids)).all():
            cat_map[cat.id] = cat

    forn_map = {}
    if forn_ids:
        for f in db.query(Fornitore).filter(Fornitore.id.in_(forn_ids)).all():
            forn_map[f.id] = f

    result = []
    for costo in costi:
        cat = cat_map.get(costo.categoria_id)
        forn = forn_map.get(costo.fornitore_id) if costo.fornitore_id else None
        quota = None
        if costo.anni_ammortamento and costo.anni_ammortamento > 0:
            quota = round(float(costo.importo_totale) / costo.anni_ammortamento, 2)
        result.append(CostoOut(
            id=costo.id, codice=costo.codice,
            categoria_id=costo.categoria_id,
            categoria_nome=cat.nome if cat else None,
            categoria_tipo=cat.tipo_costo if cat else None,
            anno_campagna=costo.anno_campagna, descrizione=costo.descrizione,
            fornitore_id=costo.fornitore_id,
            fornitore_denominazione=_fornitore_denominazione(forn),
            data_fattura=costo.data_fattura, numero_fattura=costo.numero_fattura,
            tipo_documento=costo.tipo_documento,
            imponibile=float(costo.imponibile),
            iva_percentuale=float(costo.iva_percentuale),
            importo_iva=float(costo.importo_iva),
            importo_totale=float(costo.importo_totale),
            data_pagamento=costo.data_pagamento,
            modalita_pagamento=costo.modalita_pagamento,
            riferimento_pagamento=costo.riferimento_pagamento,
            stato_pagamento=costo.stato_pagamento,
            anni_ammortamento=costo.anni_ammortamento,
            quota_ammortamento=quota,
            documento=costo.documento, note=costo.note,
            created_at=costo.created_at, updated_at=costo.updated_at,
        ))
    return paginated_response(result, total, pg, pp, pages_count)


@router.get("/{costo_id}", response_model=CostoOut)
def get_costo(costo_id: int, db: Session = Depends(get_db)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Costo non trovato.")
    return _build_costo_out(c, db)


@router.post("/", response_model=CostoOut, status_code=status.HTTP_201_CREATED)
def create_costo(data: CostoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Auto-genera codice
    if not data.codice or data.codice.strip() == "":
        data.codice = _next_codice_costo(data.anno_campagna, db)

    if db.query(Costo).filter(Costo.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice costo gia' esistente.")

    # Verifica categoria
    cat = db.query(CategoriaCosto).filter(CategoriaCosto.id == data.categoria_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Categoria non trovata.")

    # Verifica fornitore se specificato
    if data.fornitore_id:
        forn = db.query(Fornitore).filter(Fornitore.id == data.fornitore_id).first()
        if not forn:
            raise HTTPException(status_code=400, detail="Fornitore non trovato.")

    # Calcolo IVA e totale
    costo_data = data.model_dump()
    imponibile = costo_data["imponibile"]
    iva_pct = costo_data["iva_percentuale"]
    costo_data["importo_iva"] = round(imponibile * iva_pct / 100, 2)
    costo_data["importo_totale"] = round(imponibile + costo_data["importo_iva"], 2)

    c = Costo(**costo_data)
    db.add(c)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="costo", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)
    return _build_costo_out(c, db)


@router.put("/{costo_id}", response_model=CostoOut)
def update_costo(costo_id: int, data: CostoUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Costo non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    # Verifica categoria se cambiata
    if "categoria_id" in update_data:
        cat = db.query(CategoriaCosto).filter(CategoriaCosto.id == update_data["categoria_id"]).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Categoria non trovata.")

    # Verifica fornitore se cambiato
    if "fornitore_id" in update_data and update_data["fornitore_id"]:
        forn = db.query(Fornitore).filter(Fornitore.id == update_data["fornitore_id"]).first()
        if not forn:
            raise HTTPException(status_code=400, detail="Fornitore non trovato.")

    # Se l'anno campagna cambia, rigenera il codice automaticamente
    if "anno_campagna" in update_data and update_data["anno_campagna"] != c.anno_campagna:
        update_data["codice"] = _next_codice_costo(update_data["anno_campagna"], db)

    for key, value in update_data.items():
        setattr(c, key, value)

    # Ricalcola IVA e totale
    imponibile = float(c.imponibile)
    iva_pct = float(c.iva_percentuale)
    c.importo_iva = round(imponibile * iva_pct / 100, 2)
    c.importo_totale = round(imponibile + float(c.importo_iva), 2)

    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="costo", entita_id=c.id, codice_entita=c.codice)
    db.commit()
    db.refresh(c)
    return _build_costo_out(c, db)


@router.delete("/{costo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_costo(costo_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Costo non trovato.")
    # Rimuovi documento allegato se presente
    if c.documento:
        old_path = os.path.join(UPLOADS_DIR, c.documento)
        if os.path.exists(old_path):
            os.remove(old_path)
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="costo", entita_id=costo_id, codice_entita=c.codice)
    db.delete(c)
    db.commit()


@router.post("/{costo_id}/documento", response_model=CostoOut)
def upload_documento(costo_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Costo non trovato.")

    allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Tipo file non supportato. Usa JPG, PNG o PDF.")

    # Rimuovi vecchio documento se presente
    if c.documento:
        old_path = os.path.join(UPLOADS_DIR, c.documento)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf"
    codice_safe = (c.codice or "").replace("/", "_")
    filename = f"{codice_safe}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(COSTI_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    c.documento = f"costi/{filename}"
    db.commit()
    db.refresh(c)
    return _build_costo_out(c, db)


@router.delete("/{costo_id}/documento", response_model=CostoOut)
def delete_documento(costo_id: int, db: Session = Depends(get_db)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Costo non trovato.")

    if c.documento:
        old_path = os.path.join(UPLOADS_DIR, c.documento)
        if os.path.exists(old_path):
            os.remove(old_path)
        c.documento = None
        db.commit()
        db.refresh(c)

    return _build_costo_out(c, db)


@router.get("/{costo_id}/documento/download")
def download_documento(costo_id: int, db: Session = Depends(get_db)):
    c = db.query(Costo).filter(Costo.id == costo_id).first()
    if not c or not c.documento:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    filepath = os.path.join(UPLOADS_DIR, c.documento)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File non trovato sul disco.")
    return FileResponse(filepath)
