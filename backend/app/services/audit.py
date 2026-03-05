from sqlalchemy.orm import Session

from app.models.audit_log_sql import AuditLog


def log_audit(
    db: Session,
    *,
    user_id: int | None,
    username: str,
    azione: str,
    entita: str,
    entita_id: int | None = None,
    codice_entita: str | None = None,
    dettagli: str | None = None,
):
    """Registra un'azione nel log di audit."""
    entry = AuditLog(
        user_id=user_id,
        username=username,
        azione=azione,
        entita=entita,
        entita_id=entita_id,
        codice_entita=codice_entita,
        dettagli=dettagli,
    )
    db.add(entry)
    # Non fa commit — il chiamante gestisce la transazione
