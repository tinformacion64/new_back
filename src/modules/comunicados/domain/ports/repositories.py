"""
Interfaz de repositorio para el módulo de comunicados.
Define el contrato que debe implementar el adaptador de persistencia.
"""
from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional, Dict, Any

from ..entities import Comunicado


class ComunicadoRepository(ABC):
    """
    Puerto para el repositorio de Comunicados.
    """

    @abstractmethod
    def add_with_destinatarios(
        self, comunicado: Comunicado, destinatarios: List[Dict[str, Any]]
    ) -> Comunicado:
        """
        Agrega un comunicado y sus destinatarios (tabla puente
        COMUNICADO_DESTINATARIO), todo en una sola transacción ACID.
        destinatarios: [{"idDestinatario": UUID, "idRolDestinatario": UUID}, ...]
        """
        pass

    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[Comunicado]:
        """Obtiene un comunicado por su ID."""
        pass

    @abstractmethod
    def get_by_folio_doi(self, folio_doi: str) -> Optional[Comunicado]:
        """Obtiene un comunicado por su folioDoi (único)."""
        pass

    @abstractmethod
    def get_all(self) -> List[Comunicado]:
        """Obtiene todos los comunicados."""
        pass

    @abstractmethod
    def get_filtered(
        self,
        search: Optional[str] = None,
        id_tipo_comunicado: Optional[UUID] = None,
        id_area: Optional[UUID] = None,
    ) -> List[Comunicado]:
        """Obtiene comunicados con filtros opcionales."""
        pass

    @abstractmethod
    def get_destinatarios(self, id_comunicado: UUID) -> List[Dict[str, Any]]:
        """Obtiene los destinatarios de un comunicado."""
        pass