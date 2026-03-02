from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.categoria_costo_sql import CategoriaCosto
from app.models.costo_sql import Costo
from app.models.categoria_costo import CategoriaCostoCreate, CategoriaCostoUpdate, CategoriaCostoOut


router = APIRouter(prefix="/categorie-costo", tags=["categorie-costo"])

# Seed: categorie precaricate
SEED_CATEGORIE = [
    # Campagna
    ("LAV_TERRENO", "Lavorazione terreno", "campagna", 1),
    ("POTATURA", "Potatura e smaltimento", "campagna", 2),
    ("TRATTAMENTI", "Trattamenti fitosanitari", "campagna", 3),
    ("ENERGIA", "Energia e combustibili", "campagna", 4),
    ("MANODOPERA", "Manodopera extra", "campagna", 5),
    ("MATERIALI", "Materiali (bottiglie, etichette, tappi)", "campagna", 6),
    ("TRASPORTO", "Trasporti", "campagna", 7),
    ("STIPENDI_AMM", "Stipendi e amministrazione", "campagna", 8),
    ("AUTO", "Automezzi e carburante", "campagna", 9),
    ("ALTRO_CAMP", "Altro campagna", "campagna", 10),
    # Strutturale
    ("IRRIGAZIONE", "Impianto irrigazione", "strutturale", 11),
    ("OLIVETO", "Impianto oliveto", "strutturale", 12),
    ("ATTREZZATURE", "Macchinari e attrezzi", "strutturale", 13),
    ("STRUTTURE", "Magazzino, recinzioni, strade", "strutturale", 14),
    ("VEICOLI", "Acquisto veicoli", "strutturale", 15),
    ("ALTRO_STRUT", "Altro strutturale", "strutturale", 16),
]


def seed_categorie(db: Session):
    """Inserisce le categorie predefinite se la tabella e' vuota."""
    if db.query(CategoriaCosto).count() == 0:
        for codice, nome, tipo, ordine in SEED_CATEGORIE:
            cat = CategoriaCosto(codice=codice, nome=nome, tipo_costo=tipo, ordine=ordine)
            db.add(cat)
        db.commit()


@router.get("/", response_model=List[CategoriaCostoOut])
def list_categorie(
    tipo: Optional[str] = Query(None),
    attiva: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(CategoriaCosto)
    if tipo:
        query = query.filter(CategoriaCosto.tipo_costo == tipo)
    if attiva is not None:
        query = query.filter(CategoriaCosto.attiva == attiva)
    return query.order_by(CategoriaCosto.ordine, CategoriaCosto.nome).all()


@router.get("/{cat_id}", response_model=CategoriaCostoOut)
def get_categoria(cat_id: int, db: Session = Depends(get_db)):
    c = db.query(CategoriaCosto).filter(CategoriaCosto.id == cat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoria non trovata.")
    return c


@router.post("/", response_model=CategoriaCostoOut, status_code=status.HTTP_201_CREATED)
def create_categoria(data: CategoriaCostoCreate, db: Session = Depends(get_db)):
    if data.tipo_costo not in ("campagna", "strutturale"):
        raise HTTPException(status_code=400, detail="tipo_costo deve essere 'campagna' o 'strutturale'.")
    if db.query(CategoriaCosto).filter(CategoriaCosto.codice == data.codice).first():
        raise HTTPException(status_code=400, detail="Codice categoria gia' esistente.")

    c = CategoriaCosto(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{cat_id}", response_model=CategoriaCostoOut)
def update_categoria(cat_id: int, data: CategoriaCostoUpdate, db: Session = Depends(get_db)):
    c = db.query(CategoriaCosto).filter(CategoriaCosto.id == cat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoria non trovata.")

    update_data = data.model_dump(exclude_unset=True)

    if "codice" in update_data and update_data["codice"] != c.codice:
        if db.query(CategoriaCosto).filter(CategoriaCosto.codice == update_data["codice"], CategoriaCosto.id != cat_id).first():
            raise HTTPException(status_code=400, detail="Codice categoria gia' esistente.")

    if "tipo_costo" in update_data and update_data["tipo_costo"] not in ("campagna", "strutturale"):
        raise HTTPException(status_code=400, detail="tipo_costo deve essere 'campagna' o 'strutturale'.")

    for key, value in update_data.items():
        setattr(c, key, value)

    db.commit()
    db.refresh(c)
    return c


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(cat_id: int, db: Session = Depends(get_db)):
    c = db.query(CategoriaCosto).filter(CategoriaCosto.id == cat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoria non trovata.")

    in_use = db.query(Costo).filter(Costo.categoria_id == cat_id).first()
    if in_use:
        raise HTTPException(status_code=400, detail="Categoria in uso, non eliminabile. Disattivala invece.")

    db.delete(c)
    db.commit()
