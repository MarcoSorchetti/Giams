from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.audit_log_sql import AuditLog
from app.models.pagination import paginate, paginated_response

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
def list_audit(
    username: Optional[str] = Query(None),
    azione: Optional[str] = Query(None),
    entita: Optional[str] = Query(None),
    codice_entita: Optional[str] = Query(None),
    data_da: Optional[str] = Query(None, description="YYYY-MM-DD"),
    data_a: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Elenco log di audit con filtri e paginazione."""
    q = db.query(AuditLog)

    if username:
        q = q.filter(AuditLog.username == username)
    if azione:
        q = q.filter(AuditLog.azione == azione)
    if entita:
        q = q.filter(AuditLog.entita == entita)
    if codice_entita:
        q = q.filter(AuditLog.codice_entita.ilike(f"%{codice_entita}%"))
    if data_da:
        q = q.filter(AuditLog.created_at >= f"{data_da} 00:00:00")
    if data_a:
        q = q.filter(AuditLog.created_at <= f"{data_a} 23:59:59")

    q = q.order_by(desc(AuditLog.created_at))

    items, total, pg, pp, pages = paginate(q, page, per_page)

    result = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "username": row.username,
            "azione": row.azione,
            "entita": row.entita,
            "entita_id": row.entita_id,
            "codice_entita": row.codice_entita,
            "dettagli": row.dettagli,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in items
    ]

    return paginated_response(result, total, pg, pp, pages)


@router.get("/azioni")
def azioni_disponibili():
    """Restituisce la lista delle azioni possibili per il filtro."""
    return ["creato", "modificato", "eliminato", "confermato", "spedito", "pagato"]


@router.get("/entita")
def entita_disponibili():
    """Restituisce la lista delle entita' possibili per il filtro."""
    return [
        "raccolta", "lotto", "costo", "vendita", "movimento",
        "confezionamento", "contenitore", "cliente", "fornitore", "utente",
    ]
