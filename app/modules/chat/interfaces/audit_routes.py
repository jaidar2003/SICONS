from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.chat.interfaces.schemas import (
    ChatAuditLogRead,
    ChatAuditMetricsRead,
    ChatDeterminismCanonicalReportRead,
    ChatDeterminismReportRead,
)
from app.shared.database.audit_models import AuditLog
from app.shared.database.session import get_db


def build_audit_router(
    *,
    audit_log_read: Callable[[AuditLog, str | None], ChatAuditLogRead],
    build_metrics: Callable[[list[AuditLog]], ChatAuditMetricsRead],
    build_determinism: Callable[[list[AuditLog], int], ChatDeterminismReportRead],
    build_canonical: Callable[[list[AuditLog]], ChatDeterminismCanonicalReportRead],
) -> APIRouter:
    router = APIRouter()

    @router.get("/auditoria", response_model=list[ChatAuditLogRead])
    def listar_auditoria_chat(
        limit: int = Query(default=50, ge=1, le=200),
        tipo_intencion: str | None = Query(default=None),
        fallback_usado: bool | None = Query(default=None),
        usuario_id: int | None = Query(default=None, ge=1),
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user),
    ) -> list[ChatAuditLogRead]:
        if current_user.rol != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver la auditoria del asistente.")

        stmt = (
            select(AuditLog, Usuario.username)
            .outerjoin(Usuario, Usuario.id == AuditLog.usuario_id)
            .where(AuditLog.accion == "CHAT_QUERY")
            .where(AuditLog.recurso == "ChatConsulta")
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        if usuario_id is not None:
            stmt = stmt.where(AuditLog.usuario_id == usuario_id)
        if tipo_intencion:
            stmt = stmt.where(AuditLog.cambios["tipo_intencion"].as_string() == tipo_intencion)
        if fallback_usado is not None:
            stmt = stmt.where(AuditLog.cambios["fallback_usado"].as_boolean() == fallback_usado)

        rows = db.execute(stmt).all()
        return [audit_log_read(log, username) for log, username in rows]

    @router.get("/auditoria/metricas", response_model=ChatAuditMetricsRead)
    def obtener_metricas_auditoria_chat(
        limit: int = Query(default=500, ge=10, le=1000),
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user),
    ) -> ChatAuditMetricsRead:
        if current_user.rol != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver las metricas de auditoria.")
        logs = list(db.scalars(_audit_stmt(limit)))
        return build_metrics(logs)

    @router.get("/auditoria/determinismo", response_model=ChatDeterminismReportRead)
    def medir_determinismo_rag(
        limit: int = Query(default=200, ge=2, le=1000),
        limit_groups: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user),
    ) -> ChatDeterminismReportRead:
        if current_user.rol != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede medir determinismo del RAG.")
        logs = list(db.scalars(_audit_stmt(limit)))
        return build_determinism(logs, limit_groups)

    @router.get("/auditoria/determinismo/canonicas", response_model=ChatDeterminismCanonicalReportRead)
    def medir_determinismo_canonicas(
        limit: int = Query(default=500, ge=10, le=1000),
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user),
    ) -> ChatDeterminismCanonicalReportRead:
        if current_user.rol != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede medir la bateria canonica del RAG.")
        logs = list(db.scalars(_audit_stmt(limit)))
        return build_canonical(logs)

    return router


def _audit_stmt(limit: int):
    return (
        select(AuditLog)
        .where(AuditLog.accion == "CHAT_QUERY")
        .where(AuditLog.recurso == "ChatConsulta")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
