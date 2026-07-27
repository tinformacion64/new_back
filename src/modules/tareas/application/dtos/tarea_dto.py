"""
DTOs para la gestión de Tareas (Sección V SGC2I).
"""
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponsableIn(BaseModel):
    """Esquema de entrada para un responsable en el payload."""
    idResponsable: UUID = Field(..., description="UUID del empleado responsable")
    idRolResponsable: UUID = Field(..., description="UUID del rol de responsable")


class TareaCreateRequest(BaseModel):
    """
    Payload de entrada para la creación de una Tarea.
    NO incluye idEstadoTarea ni fechaRegistro en la petición.
    """
    idComunicado: UUID = Field(..., description="UUID del comunicado padre")
    resumenActividad: str = Field(..., max_length=255, description="Resumen breve de la actividad")
    descripcion: str = Field(..., description="Descripción detallada de la tarea")
    fechaEntrega: datetime = Field(..., description="Fecha y hora de compromiso de entrega")
    responsables: List[UUID] = Field(
        ..., min_items=1, description="Lista de UUIDs de los responsables asignados"
    )
    colaboradores: List[UUID] = Field(
        default_factory=list, description="Lista de UUIDs de los colaboradores de apoyo"
    )

    @field_validator("resumenActividad", "descripcion")
    @classmethod
    def not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El campo no puede estar vacío ni contener solo espacios")
        return value.strip()


class ResponsableResponse(BaseModel):
    """DTO de respuesta para un responsable."""
    idEmpleado: UUID
    nombre: str

    model_config = ConfigDict(from_attributes=True)


class EvidenciaResponse(BaseModel):
    """DTO de respuesta para una evidencia vinculada a una tarea."""
    idArchivoEvidencia: UUID
    doi: str
    nombreOriginal: str
    urlArchivo: str
    fechaRegistro: Optional[datetime] = None  # Mapeado explícito para serialización
    descripcion: str
    elaboradorNombre: str

    model_config = ConfigDict(from_attributes=True)


class TareaResponse(BaseModel):
    """DTO de respuesta para una Tarea creada/consultada."""
    id: UUID
    idComunicado: UUID
    idEstadoTarea: UUID
    resumenActividad: str
    descripcion: str
    fechaEntrega: datetime
    fechaRegistro: Optional[datetime] = None
    estado: Optional[str] = None
    responsables: List[ResponsableResponse] = Field(default_factory=list)
    evidencias: List[EvidenciaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
