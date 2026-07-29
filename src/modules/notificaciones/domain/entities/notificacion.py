from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from typing import Optional
from shared.domain.base_entity import BaseEntity

@dataclass
class Notificacion(BaseEntity):
    idEmpleadoDestino: UUID
    tipo: str
    mensaje: str
    idReferencia: Optional[UUID] = None
    leida: bool = False
    fechaCreacion: Optional[datetime] = None