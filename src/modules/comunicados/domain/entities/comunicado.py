"""
Entidad Comunicado.
Representa un oficio/circular/comunicado institucional.
Mapeo 1:1 con la tabla COMUNICADO del esquema SQL.
"""
from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from typing import Optional

from shared.domain.base_entity import BaseEntity


@dataclass
class Comunicado(BaseEntity):
    # idComunicado -> id (heredado de BaseEntity)
    folioDoi: str  # VARCHAR(100) UNIQUE NOT NULL
    numComunicado: str  # VARCHAR(50) NOT NULL
    tema: str  # VARCHAR(200) NOT NULL
    fechaEmision: datetime  # TIMESTAMP WITH TIME ZONE NOT NULL
    fechaRecepcion: datetime  # TIMESTAMP WITH TIME ZONE NOT NULL
    idEmisor: UUID  # FK EMPLEADO
    idTipoComunicado: UUID  # FK TIPO_COMUNICADO
    idMedioRecepcion: UUID  # FK MEDIO_RECEPCION
    idEmpleadoRegistro: UUID  # FK EMPLEADO (inyectado del JWT, nunca del payload)
    fechaRegistro: Optional[datetime] = field(default=None)  # la asigna el servidor/DB
    areaEmisoraNombre: Optional[str] = field(default=None)
    empleadoRegistroNombre: Optional[str] = field(default=None)
    archivoUrl: Optional[str] = field(default=None)
    archivos: list = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validaciones de invariantes."""
        if not self.folioDoi or not self.folioDoi.strip():
            raise ValueError("El folioDoi no puede estar vacío")
        if len(self.folioDoi) > 100:
            raise ValueError("El folioDoi no puede exceder 100 caracteres")

        if not self.numComunicado or not self.numComunicado.strip():
            raise ValueError("El numComunicado no puede estar vacío")
        if len(self.numComunicado) > 50:
            raise ValueError("El numComunicado no puede exceder 50 caracteres")

        if not self.tema or not self.tema.strip():
            raise ValueError("El tema no puede estar vacío")
        if len(self.tema) > 200:
            raise ValueError("El tema no puede exceder 200 caracteres")

        if self.archivoUrl and len(self.archivoUrl) > 500:
            raise ValueError("La URL del archivo no puede exceder 500 caracteres")

        if self.fechaRecepcion < self.fechaEmision:
            raise ValueError(
                "fechaRecepcion no puede ser anterior a fechaEmision"
            )