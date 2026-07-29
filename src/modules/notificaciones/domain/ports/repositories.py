from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional

from ..entities import Notificacion


class NotificacionRepository(ABC):
    @abstractmethod
    def add(self, notificacion: Notificacion) -> Notificacion:
        pass

    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[Notificacion]:
        pass

    @abstractmethod
    def get_by_empleado(self, idEmpleado: UUID, skip: int = 0, limit: int = 100) -> List[Notificacion]:
        pass

    @abstractmethod
    def get_no_leidas_by_empleado(self, idEmpleado: UUID) -> List[Notificacion]:
        pass

    @abstractmethod
    def marcar_leida(self, id: UUID, idEmpleado: UUID) -> Notificacion:
        pass