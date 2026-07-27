"""
Caso de uso para registrar evidencias y actualizar el estado de la tarea a 'entregada'.
"""
from uuid import UUID
from typing import Any, List, Dict, Optional

from ...domain.entities import Evidencia
from ...domain.ports import EvidenciaRepository
from modules.tareas.application.estado_lookup import find_estado_by_nombre
from shared.domain.exceptions import BusinessRuleViolationError


class CreateEvidenciaUseCase:
    """
    Caso de uso para crear una Evidencia y ejecutar el trigger lógico de actualización
    del estado de la Tarea padre a 'entregada'.
    """

    def __init__(
        self,
        repository: EvidenciaRepository,
        tarea_repository: Any,
        estado_tarea_repository: Any,
    ):
        self._repository = repository
        self._tarea_repository = tarea_repository
        self._estado_tarea_repository = estado_tarea_repository

    def execute(
        self,
        idTarea: UUID,
        doi: str,
        descripcion: str,
        idElaborador: UUID,
        archivos: Optional[List[Dict[str, str]]] = None,
    ) -> Evidencia:
        # 1. Validar que la tarea padre existe
        tarea = self._tarea_repository.get_by_id(idTarea)
        if tarea is None:
            raise BusinessRuleViolationError(f"La tarea {idTarea} no existe")

        # 2. Validar que el doi no esté duplicado
        if self._repository.get_by_doi(doi) is not None:
            raise BusinessRuleViolationError(f"Ya existe una evidencia con doi '{doi}'")

        # 3. Insertar evidencia y vinculación transaccionalmente
        saved_evidencias = self._repository.add_with_tarea_and_files(
            doi=doi,
            descripcion=descripcion,
            id_elaborador=idElaborador,
            id_tarea=idTarea,
            archivos=archivos,
        )

        # 4. TRIGGER LÓGICO: Obtener el UUID del estado "entregada" y actualizar la tarea padre
        estado_entregada = self._estado_tarea_repository.get_by_nombre("entregada")
        if estado_entregada is None:
            estado_entregada = find_estado_by_nombre(self._estado_tarea_repository, "ENTREGADA")

        self._tarea_repository.update_estado(idTarea, estado_entregada.id)

        return saved_evidencias[0]
