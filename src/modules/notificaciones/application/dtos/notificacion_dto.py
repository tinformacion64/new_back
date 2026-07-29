from pydantic import BaseModel
from uuid import UUID

class NotificacionResponse(BaseModel):
    id: str
    idEmpleadoDestino: str
    tipo: str
    mensaje: str
    idReferencia: str | None = None
    leida: bool
    fechaCreacion: str | None = None

    model_config = {
        "from_attributes": True
    }