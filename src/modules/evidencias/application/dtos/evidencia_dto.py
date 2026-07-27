"""
DTOs para la gestión de Evidencias (Fase 3 / Sección V SGC2I).
"""
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArchivoCreateDTO(BaseModel):
    """DTO para crear un archivo vinculado con urlArchivo y nombreOriginal."""
    urlArchivo: str = Field(..., description="URL del archivo subido a Cloudinary")
    nombreOriginal: str = Field(..., description="Nombre original del archivo")


class EvidenciaCreateRequest(BaseModel):
    """
    Payload de entrada para registrar una Evidencia.
    NO incluye idElaborador (inyectado del JWT) ni fechaRegistro.
    """
    idTarea: UUID = Field(..., description="UUID de la tarea a la que pertenece la evidencia")
    doi: str = Field(..., max_length=100, description="DOI único de la evidencia")
    descripcion: str = Field(..., description="Descripción detallada de la evidencia")
    archivos: Optional[List[ArchivoCreateDTO]] = Field(default=None, description="Lista de archivos subidos para la evidencia")

    @field_validator("doi", "descripcion")
    @classmethod
    def not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El campo no puede estar vacío ni contener solo espacios")
        return value.strip()


class EvidenciaResponse(BaseModel):
    """DTO de respuesta para una Evidencia creada/consultada."""
    id: UUID
    doi: str
    descripcion: str
    urlArchivo: str
    nombreOriginal: str
    idElaborador: UUID
    fechaRegistro: Optional[datetime] = None
    idTarea: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
