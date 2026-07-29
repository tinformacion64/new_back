from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ...domain.entities import Notificacion
from ...domain.ports import NotificacionRepository
from ...infrastructure.persistence import NotificacionRepositoryAdapter
from ...application.dtos import NotificacionResponse

from shared.infrastructure.security.security import get_current_active_user

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def get_notificacion_repository() -> NotificacionRepository:
    return NotificacionRepositoryAdapter()


@router.get("/", response_model=List[NotificacionResponse])
async def list_notificaciones(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_active_user),
    repository: NotificacionRepository = Depends(get_notificacion_repository),) -> List[NotificacionResponse]:
    idEmpleado = UUID(current_user["idEmpleado"])
    notificaciones = repository.get_by_empleado(idEmpleado, skip=skip, limit=limit)
    return [
        NotificacionResponse(
            id=str(n.id),
            idEmpleadoDestino=str(n.idEmpleadoDestino),
            tipo=n.tipo,
            mensaje=n.mensaje,
            idReferencia=str(n.idReferencia) if n.idReferencia else None,
            leida=n.leida,
            fechaCreacion=n.fechaCreacion.isoformat() if n.fechaCreacion else None,
        )
        for n in notificaciones
    ]


@router.patch("/{id}/leida", response_model=NotificacionResponse)
async def marcar_leida(
    id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: NotificacionRepository = Depends(get_notificacion_repository),) -> NotificacionResponse:
    idEmpleado = UUID(current_user["idEmpleado"])
    try:
        notificacion = repository.marcar_leida(id, idEmpleado)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    return NotificacionResponse(
        id=str(notificacion.id),
        idEmpleadoDestino=str(notificacion.idEmpleadoDestino),
        tipo=notificacion.tipo,
        mensaje=notificacion.mensaje,
        idReferencia=str(notificacion.idReferencia) if notificacion.idReferencia else None,
        leida=notificacion.leida,
        fechaCreacion=notificacion.fechaCreacion.isoformat() if notificacion.fechaCreacion else None,
    )


@router.get("/no-leidas/count")
async def contar_no_leidas(
    current_user: dict = Depends(get_current_active_user),
    repository: NotificacionRepository = Depends(get_notificacion_repository),) -> dict:
    idEmpleado = UUID(current_user["idEmpleado"])
    no_leidas = repository.get_no_leidas_by_empleado(idEmpleado)
    return {"count": len(no_leidas)}
