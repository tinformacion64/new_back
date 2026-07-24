"""
Router de API para el recurso Tarea (Sección V SGC2I).
"""
from uuid import UUID
from typing import List, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from ....domain.entities import Tarea
from ....domain.ports import TareaRepository
from ....domain.services import TaskStateMachine
from ....infrastructure.persistence import TareaRepositoryAdapter
from ....application.dtos import (
    TareaCreateRequest,
    TareaResponse,
    ResponsableResponse,
    EvidenciaResponse,
)
from ....application.use_cases import CreateTareaUseCase, TransicionEstadoTareaUseCase

from modules.comunicados.domain.ports import ComunicadoRepository
from modules.comunicados.infrastructure.persistence import ComunicadoRepositoryAdapter
from modules.catalogos.domain.ports import EstadoTareaRepository, RolResponsableRepository
from modules.catalogos.infrastructure.persistence import (
    EstadoTareaRepositoryAdapter,
    RolResponsableRepositoryAdapter,
)

from shared.infrastructure.security.security import get_current_active_user, require_roles
from shared.domain.exceptions import BusinessRuleViolationError

router = APIRouter(prefix="/tareas", tags=["tareas"])


def get_tarea_repository() -> TareaRepository:
    return TareaRepositoryAdapter()


def get_comunicado_repository() -> ComunicadoRepository:
    return ComunicadoRepositoryAdapter()


def get_estado_tarea_repository() -> EstadoTareaRepository:
    return EstadoTareaRepositoryAdapter()


def get_rol_responsable_repository() -> RolResponsableRepository:
    return RolResponsableRepositoryAdapter()


def _compute_estado_nombre(estado_real_nombre: str, fecha_entrega: datetime) -> str:
    """
    VENCIDA es una transición calculada (no persistida): si la tarea sigue
    en ASIGNADA o EN_PROCESO y ya pasó su fechaEntrega, se muestra como
    VENCIDA en la respuesta, sin alterar el valor guardado en BD.
    """
    normalizado = estado_real_nombre.strip().upper().replace(" ", "_")
    if normalizado in ("ASIGNADA", "EN_PROCESO"):
        ahora = datetime.now(timezone.utc)
        entrega = fecha_entrega
        if entrega.tzinfo is None:
            entrega = entrega.replace(tzinfo=timezone.utc)
        if entrega < ahora:
            return "VENCIDA"
    return estado_real_nombre


def _to_response(tarea: Tarea, estado_tarea_repository: Any, repository: TareaRepository) -> TareaResponse:
    estado = estado_tarea_repository.get_by_id(tarea.idEstadoTarea)
    estado_nombre = estado.nombre if estado is not None else "DESCONOCIDO"
    responsables = repository.get_responsables_detallados(tarea.id)
    evidencias = repository.get_evidencias(tarea.id)
    return TareaResponse(
        id=tarea.id,
        idComunicado=tarea.idComunicado,
        idEstadoTarea=tarea.idEstadoTarea,
        resumenActividad=tarea.resumenActividad,
        descripcion=tarea.descripcion,
        fechaEntrega=tarea.fechaEntrega,
        fechaRegistro=tarea.fechaRegistro,
        estado=_compute_estado_nombre(estado_nombre, tarea.fechaEntrega),
        responsables=[
            ResponsableResponse(
                idEmpleado=r["idEmpleado"],
                nombre=r["nombre"]
            )
            for r in responsables
        ],
        evidencias=[
            EvidenciaResponse(
                idArchivoEvidencia=ev["idArchivoEvidencia"],
                doi=ev["doi"],
                nombreOriginal=ev["nombreOriginal"],
                urlArchivo=ev["urlArchivo"],
                fechaRegistro=ev["fechaRegistro"],
                descripcion=ev["descripcion"],
                elaboradorNombre=ev["elaboradorNombre"],
            )
            for ev in evidencias
        ]
    )


@router.post("/", response_model=TareaResponse, status_code=status.HTTP_201_CREATED)
async def create_tarea(
    request: TareaCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
    rol_responsable_repository: RolResponsableRepository = Depends(get_rol_responsable_repository),
) -> TareaResponse:
    """
    Crea una nueva tarea derivada de un comunicado.
    Valida fechas contra el comunicado padre e inyecta el estado inicial 'asignada'.
    Requiere JWT válido (usuario autenticado).
    """
    use_case = CreateTareaUseCase(
        repository, comunicado_repository, estado_tarea_repository, rol_responsable_repository
    )
    try:
        tarea = use_case.execute(
            idComunicado=request.idComunicado,
            resumenActividad=request.resumenActividad,
            descripcion=request.descripcion,
            fechaEntrega=request.fechaEntrega,
            responsables=request.responsables,
            colaboradores=request.colaboradores,
        )
        return _to_response(tarea, estado_tarea_repository, repository)
    except (BusinessRuleViolationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[TareaResponse])
async def list_tareas(
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> List[TareaResponse]:
    """Lista todas las tareas."""
    tareas = repository.get_all()
    return [_to_response(t, estado_tarea_repository, repository) for t in tareas]


@router.get("/{tarea_id}", response_model=TareaResponse)
async def get_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """
    Obtiene una tarea por ID.
    Efecto automático: si quien consulta es responsable de la tarea y el
    estado real actual es ASIGNADA, se transiciona automáticamente a
    EN_PROCESO (PATCH automático al acceder, regla V.2).
    """
    tarea = repository.get_by_id(tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    estado_actual = estado_tarea_repository.get_by_id(tarea.idEstadoTarea)
    es_responsable = repository.is_responsable(tarea_id, UUID(current_user["idEmpleado"]))

    if (
        es_responsable
        and estado_actual is not None
        and estado_actual.nombre.strip().upper().replace(" ", "_") == "ASIGNADA"
    ):
        use_case = TransicionEstadoTareaUseCase(repository, estado_tarea_repository)
        tarea = use_case.execute(tarea_id, "EN_PROCESO")

    return _to_response(tarea, estado_tarea_repository, repository)


@router.get("/{tarea_id}/responsables", response_model=List[dict])
async def get_responsables(
    tarea_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
) -> List[dict]:
    """Obtiene los responsables de una tarea."""
    tarea = repository.get_by_id(tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    responsables = repository.get_responsables(tarea_id)
    return [
        {"idResponsable": str(r["idResponsable"]), "idRolResponsable": str(r["idRolResponsable"])}
        for r in responsables
    ]


class EstadoUpdateRequest(BaseModel):
    estado: str


def _transicionar(
    tarea_id: UUID,
    nombre_estado_destino: str,
    repository: TareaRepository,
    estado_tarea_repository: EstadoTareaRepository,
    current_user: dict,
    comunicado_repository: Any,
) -> TareaResponse:
    # 1. Obtener la tarea
    tarea = repository.get_by_id(tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # 2. Obtener estado actual
    estado_actual = estado_tarea_repository.get_by_id(tarea.idEstadoTarea)
    estado_actual_nombre = estado_actual.nombre if estado_actual is not None else "DESCONOCIDO"

    # 3. Obtener responsables de la tarea
    responsables_db = repository.get_responsables(tarea_id)
    responsables_ids = [r["idResponsable"] for r in responsables_db]

    # 4. Obtener creador del comunicado
    comunicado = comunicado_repository.get_by_id(tarea.idComunicado)
    comunicado_creator_id = comunicado.idEmpleadoRegistro if comunicado is not None else None

    # 5. Extraer info del usuario del JWT
    user_id = UUID(current_user["idEmpleado"])
    user_roles = current_user.get("cargos_nombres", [])

    # 6. Validar transición con la Máquina de Estados (TaskStateMachine)
    try:
        TaskStateMachine.validate_transition(
            current_state_name=estado_actual_nombre,
            target_state_name=nombre_estado_destino,
            user_id=user_id,
            user_roles=user_roles,
            responsables=responsables_ids,
            comunicado_creator_id=comunicado_creator_id
        )
    except BusinessRuleViolationError as e:
        if "Solo los usuarios con rol" in str(e) or "Solo los responsables" in str(e) or "Solo el director" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 7. Ejecutar transición
    use_case = TransicionEstadoTareaUseCase(repository, estado_tarea_repository)
    try:
        updated_tarea = use_case.execute(tarea_id, nombre_estado_destino)
        return _to_response(updated_tarea, estado_tarea_repository, repository)
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{tarea_id}/estado", response_model=TareaResponse)
async def update_tarea_estado(
    tarea_id: UUID,
    request: EstadoUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """Actualiza el estado de una tarea aplicando validaciones de Máquina de Estados y RBAC."""
    return _transicionar(
        tarea_id,
        request.estado,
        repository,
        estado_tarea_repository,
        current_user,
        comunicado_repository
    )


@router.patch("/{tarea_id}/revisar", response_model=TareaResponse)
async def revisar_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(require_roles(["Director"])),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """Aprueba/cierra la tarea (REVISADA). Solo rol Director."""
    return _transicionar(
        tarea_id,
        "REVISADA",
        repository,
        estado_tarea_repository,
        current_user,
        comunicado_repository
    )


@router.patch("/{tarea_id}/rechazar", response_model=TareaResponse)
async def rechazar_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(require_roles(["Director"])),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """Rechaza la tarea y la regresa a EN_PROCESO. Solo rol Director."""
    return _transicionar(
        tarea_id,
        "EN_PROCESO",
        repository,
        estado_tarea_repository,
        current_user,
        comunicado_repository
    )


@router.patch("/{tarea_id}/cancelar", response_model=TareaResponse)
async def cancelar_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(require_roles(["Director"])),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """Cancela la tarea, sin solicitar evidencias. Solo rol Director."""
    return _transicionar(
        tarea_id,
        "CANCELADA",
        repository,
        estado_tarea_repository,
        current_user,
        comunicado_repository
    )


@router.patch("/{tarea_id}/en-proceso", response_model=TareaResponse)
async def iniciar_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: TareaRepository = Depends(get_tarea_repository),
    comunicado_repository: ComunicadoRepository = Depends(get_comunicado_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> TareaResponse:
    """Cambia el estado de la tarea a EN_PROCESO. Requiere usuario autenticado."""
    return _transicionar(
        tarea_id,
        "EN_PROCESO",
        repository,
        estado_tarea_repository,
        current_user,
        comunicado_repository
    )