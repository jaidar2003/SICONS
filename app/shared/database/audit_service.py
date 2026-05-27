from typing import Any

from sqlalchemy.orm import Session

from app.shared.database.audit_models import AuditLog


def register_audit_log(
    db: Session,
    *,
    usuario_id: int | None,
    accion: str,
    recurso: str,
    recurso_id: str | None = None,
    cambios: dict[str, Any] | None = None,
    ip_address: str | None = None
) -> AuditLog:
    """
    Registra una accion en el log de auditoria.
    """
    log_entry = AuditLog(
        usuario_id=usuario_id,
        accion=accion,
        recurso=recurso,
        recurso_id=recurso_id,
        cambios=cambios,
        ip_address=ip_address
    )
    db.add(log_entry)
    db.flush()  # Usamos flush para no commitear la transaccion principal aqui
    return log_entry
