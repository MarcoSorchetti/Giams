import os
import shutil
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from sqlalchemy import or_

from app.database import get_db
from app.models.contenitore_sql import Contenitore
from app.models.contenitore import ContenitoreCreate, ContenitoreUpdate, ContenitoreOut
from app.models.pagination import paginate, paginated_response

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "../../../uploads")
CONTENITORI_DIR = os.path.join(UPLOADS_DIR, "contenitori")
os.makedirs(CONTENITORI_DIR, exist_ok=True)

router = APIRouter(prefix="/contenitori", tags=["contenitori"])


def _to_out(c: Contenitore) -> ContenitoreOut:
    return ContenitoreOut(
        id=c.id,
        codice=c.codice,
        descrizione=c.descrizione,
        capacita_litri=float(c.capacita_litri),
        foto=c.foto,
        attivo=c.attivo,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("/")
def list_contenitori(
    search: Optional[str] = Query(None, alias="q"),
    tutti: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Contenitore)
    if not tutti:
        query = query.filter(Contenitore.attivo == True)  # noqa: E712

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Contenitore.codice.ilike(like),
                Contenitore.descrizione.ilike(like),
            )
        )

    query = query.order_by(Contenitore.descrizione)
    items, total, pg, pp, pages = paginate(query, page, per_page)
    return paginated_response([_to_out(c) for c in items], total, pg, pp, pages)


@router.get("/{cont_id}", response_model=ContenitoreOut)
def get_contenitore(cont_id: int, db: Session = Depends(get_db)):
    c = db.query(Contenitore).filter(Contenitore.id == cont_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenitore non trovato.")
    return _to_out(c)


@router.post("/", response_model=ContenitoreOut, status_code=status.HTTP_201_CREATED)
def create_contenitore(data: ContenitoreCreate, db: Session = Depends(get_db)):
    if db.query(Contenitore).filter(Contenitore.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice contenitore gia' esistente.")

    c = Contenitore(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.put("/{cont_id}", response_model=ContenitoreOut)
def update_contenitore(cont_id: int, data: ContenitoreUpdate, db: Session = Depends(get_db)):
    c = db.query(Contenitore).filter(Contenitore.id == cont_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenitore non trovato.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice" in update_data and update_data["codice"] != c.codice:
        if db.query(Contenitore).filter(Contenitore.codice == update_data["codice"], Contenitore.id != cont_id).first():
            raise HTTPException(status_code=400, detail="Codice contenitore gia' esistente.")

    for key, value in update_data.items():
        setattr(c, key, value)

    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{cont_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contenitore(cont_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    from app.models.confezionamento_sql import Confezionamento

    c = db.query(Contenitore).filter(Contenitore.id == cont_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenitore non trovato.")

    utilizzi = (
        db.query(Confezionamento.codice, Confezionamento.data_confezionamento)
        .filter(Confezionamento.contenitore_id == cont_id)
        .order_by(Confezionamento.data_confezionamento.desc())
        .all()
    )

    if utilizzi and not force:
        elenco = ", ".join(
            f"{u.codice} ({u.data_confezionamento.strftime('%d/%m/%Y')})" for u in utilizzi
        )
        return JSONResponse(status_code=409, content={
            "detail": f"Contenitore utilizzato in {len(utilizzi)} confezionamento/i: {elenco}. "
                       "Eliminandolo, i confezionamenti resteranno senza contenitore associato.",
            "conflict_type": "contenitore_in_uso",
            "num_utilizzi": len(utilizzi),
            "confezionamenti": [{"codice": u.codice,
                                  "data": u.data_confezionamento.strftime("%d/%m/%Y")} for u in utilizzi],
        })

    if c.foto:
        foto_path = os.path.join(UPLOADS_DIR, c.foto)
        if os.path.exists(foto_path):
            os.remove(foto_path)

    db.delete(c)
    db.commit()


@router.post("/{cont_id}/foto", response_model=ContenitoreOut)
def upload_foto(cont_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    c = db.query(Contenitore).filter(Contenitore.id == cont_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenitore non trovato.")

    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Tipo file non supportato. Usa JPG, PNG, WebP o GIF.")

    if c.foto:
        old_path = os.path.join(UPLOADS_DIR, c.foto)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{c.codice}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(CONTENITORI_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    c.foto = f"contenitori/{filename}"
    db.commit()
    db.refresh(c)
    return _to_out(c)
