"""Utility condivisa per la generazione di codici sequenziali PREFIX/NNN/ANNO."""

from sqlalchemy.orm import Session


def next_codice_anno(prefix: str, model, column, anno: int, db: Session) -> str:
    """Genera il prossimo codice nel formato PREFIX/NNN/ANNO.

    Args:
        prefix: Prefisso del codice (es. "V", "C", "MV", "R", "O")
        model: Classe SQLAlchemy del modello
        column: Colonna SQLAlchemy del codice (es. Vendita.codice)
        anno: Anno campagna
        db: Sessione database
    """
    last = (
        db.query(model)
        .filter(column.like(f"{prefix}/%/{anno}"))
        .order_by(column.desc())
        .with_for_update()
        .first()
    )
    if last:
        try:
            val = getattr(last, column.key)
            num = int(val.split("/")[1]) + 1
        except (IndexError, ValueError, AttributeError):
            num = 1
    else:
        num = 1
    return f"{prefix}/{num:03d}/{anno}"
