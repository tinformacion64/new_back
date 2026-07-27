"""
Router de API para el recurso Evidencia (Sección V / Fase 3 SGC2I).
"""
import logging
import traceback
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ....domain.entities import Evidencia
from ....domain.ports import EvidenciaRepository
from ....infrastructure.persistence import EvidenciaRepositoryAdapter
from ....application.dtos import (
    EvidenciaCreateRequest,
    EvidenciaResponse,
    ArchivoResponse,
)
from ....application.use_cases import CreateEvidenciaUseCase

from modules.tareas.domain.ports import TareaRepository
from modules.tareas.infrastructure.persistence import TareaRepositoryAdapter
from modules.catalogos.domain.ports import EstadoTareaRepository
from modules.catalogos.infrastructure.persistence import EstadoTareaRepositoryAdapter

from shared.infrastructure.security.security import get_current_active_user
from shared.domain.exceptions import BusinessRuleViolationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidencias", tags=["evidencias"])


def get_evidencia_repository() -> EvidenciaRepository:
    return EvidenciaRepositoryAdapter()


def get_tarea_repository() -> TareaRepository:
    return TareaRepositoryAdapter()


def get_estado_tarea_repository() -> EstadoTareaRepository:
    return EstadoTareaRepositoryAdapter()


def _to_response(evidencia: Evidencia, id_tarea: UUID = None) -> EvidenciaResponse:
    return EvidenciaResponse(
        id=evidencia.id,
        doi=evidencia.doi,
        descripcion=evidencia.descripcion,
        urlArchivo=evidencia.urlArchivo,
        nombreOriginal=evidencia.nombreOriginal,
        idElaborador=evidencia.idElaborador,
        fechaRegistro=evidencia.fechaRegistro,
        idTarea=id_tarea,
        archivos=[
            ArchivoResponse(
                urlArchivo=evidencia.urlArchivo,
                nombreOriginal=evidencia.nombreOriginal
            )
        ] if evidencia.urlArchivo else [],
    )


@router.post("/", response_model=EvidenciaResponse, status_code=status.HTTP_201_CREATED)
async def create_evidencia(
    request: EvidenciaCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    repository: EvidenciaRepository = Depends(get_evidencia_repository),
    tarea_repository: TareaRepository = Depends(get_tarea_repository),
    estado_tarea_repository: EstadoTareaRepository = Depends(get_estado_tarea_repository),
) -> EvidenciaResponse:
    """
    Crea una nueva evidencia, la vincula a la tarea e inyecta el trigger lógico
    para actualizar el estado de la tarea padre a 'entregada'.
    idElaborador se inyecta desde el JWT de autenticación.
    """
    idElaborador = UUID(current_user["idEmpleado"])

    use_case = CreateEvidenciaUseCase(
        repository, tarea_repository, estado_tarea_repository
    )
    try:
        evidencia = use_case.execute(
            idTarea=request.idTarea,
            doi=request.doi,
            descripcion=request.descripcion,
            idElaborador=idElaborador,
            archivos=[a.model_dump() for a in request.archivos] if request.archivos is not None else None,
        )
        return _to_response(evidencia, id_tarea=request.idTarea)
    except (BusinessRuleViolationError, ValueError) as e:
        logger.warning("Regla de negocio o validación falló en POST /evidencias/: %s", e)
        print(f"⚠️ REGLA DE NEGOCIO / VALIDACIÓN EN EVIDENCIA: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"❌ ERROR REAL EN POST /evidencias/: {str(e)}")
        traceback.print_exc()
        logger.error("Error no controlado en POST /evidencias/: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error real del servidor: {str(e)}"
        )


@router.get("/", response_model=List[EvidenciaResponse])
async def list_evidencias(
    current_user: dict = Depends(get_current_active_user),
    repository: EvidenciaRepository = Depends(get_evidencia_repository),
) -> List[EvidenciaResponse]:
    """Lista todas las evidencias."""
    evidencias = repository.get_all()
    return [_to_response(e) for e in evidencias]


@router.get("/{evidencia_id}", response_model=EvidenciaResponse)
async def get_evidencia(
    evidencia_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: EvidenciaRepository = Depends(get_evidencia_repository),
) -> EvidenciaResponse:
    """Obtiene una evidencia por ID."""
    evidencia = repository.get_by_id(evidencia_id)
    if evidencia is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    return _to_response(evidencia)


@router.get("/tarea/{tarea_id}", response_model=List[EvidenciaResponse])
async def list_evidencias_por_tarea(
    tarea_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: EvidenciaRepository = Depends(get_evidencia_repository),
) -> List[EvidenciaResponse]:
    """Obtiene todas las evidencias vinculadas a una tarea."""
    evidencias = repository.get_by_tarea(tarea_id)
    return [_to_response(e, id_tarea=tarea_id) for e in evidencias]
