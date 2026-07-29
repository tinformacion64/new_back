"""
Interfaz de repositorio para el módulo de tareas.
"""
from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional, Dict, Any

from ..entities import Tarea


class TareaRepository(ABC):
    """
    Puerto para el repositorio de Tareas.
    """

    @abstractmethod
    def add_with_responsables(
        self, tarea: Tarea, responsables: List[Dict[str, Any]]
    ) -> Tarea:
        """
        Agrega una tarea y sus responsables (tabla puente TAREA_RESPONSABLE),
        todo en una sola transacción ACID.
        responsables: [{"idResponsable": UUID, "idRolResponsable": UUID}, ...]
        """
        pass

    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[Tarea]:
        """Obtiene una tarea por su ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[Tarea]:
        """Obtiene todas las tareas."""
        pass

    @abstractmethod
    def get_filtered(
        self,
        search: Optional[str] = None,
        id_estado: Optional[UUID] = None,
        id_comunicado: Optional[UUID] = None,
    ) -> List[Tarea]:
        """Obtiene tareas con filtros opcionales."""
        pass

    @abstractmethod
    def get_responsables(self, id_tarea: UUID) -> List[Dict[str, Any]]:
        """Obtiene los responsables de una tarea."""
        pass

    @abstractmethod
    def get_responsables_detallados(self, id_tarea: UUID) -> List[Dict[str, Any]]:
        """Obtiene los responsables detallados (idEmpleado, nombre) de una tarea."""
        pass

    @abstractmethod
    def get_evidencias(self, id_tarea: UUID) -> List[Dict[str, Any]]:
        """Obtiene las evidencias vinculadas a una tarea."""
        pass

    @abstractmethod
    def get_by_comunicado(self, id_comunicado: UUID) -> List[Tarea]:
        """Obtiene todas las tareas asociadas a un comunicado."""
        pass

    @abstractmethod
    def is_responsable(self, id_tarea: UUID, id_empleado: UUID) -> bool:
        """Indica si un empleado es responsable de una tarea."""
        pass

    @abstractmethod
    def update_estado(self, id_tarea: UUID, id_estado_tarea: UUID) -> Tarea:
        """Actualiza el estado de una tarea (único método de transición)."""
        pass