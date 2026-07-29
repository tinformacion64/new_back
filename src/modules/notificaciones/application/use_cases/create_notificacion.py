from uuid import UUID
from ...domain.ports import NotificacionRepository
from ...domain.entities import Notificacion


class CreateNotificacionUseCase:
    def __init__(self, repository: NotificacionRepository):
        self._repository = repository

    def execute(
        self,
        idEmpleadoDestino: UUID,
        tipo: str,
        mensaje: str,
        idReferencia: UUID = None,
    ) -> Notificacion:
        notificacion = Notificacion(
            idEmpleadoDestino=idEmpleadoDestino,
            tipo=tipo,
            mensaje=mensaje,
            idReferencia=idReferencia,
        )
        return self._repository.add(notificacion)
