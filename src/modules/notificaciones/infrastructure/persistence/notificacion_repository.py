from uuid import UUID
from typing import List, Optional
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import Table, Column, String, Boolean, DateTime, select, update, insert
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from ...domain.entities import Notificacion
from ...domain.ports import NotificacionRepository
from shared.infrastructure.database.connection import DatabaseConnection


class NotificacionRepositoryAdapter(NotificacionRepository):
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @contextmanager
    def _get_session(self):
        if self._session is not None:
            yield self._session
        else:
            with DatabaseConnection.get_session() as session:
                yield session

    @property
    def table(self) -> Table:
        metadata = DatabaseConnection.get_metadata()
        if "NOTIFICACION" in metadata.tables:
            return metadata.tables["NOTIFICACION"]
        return Table(
            "NOTIFICACION",
            metadata,
            Column("idNotificacion", PG_UUID(as_uuid=True), primary_key=True),
            Column("idEmpleadoDestino", PG_UUID(as_uuid=True), nullable=False),
            Column("tipo", String(50), nullable=False),
            Column("mensaje", String(500), nullable=False),
            Column("idReferencia", PG_UUID(as_uuid=True)),
            Column("leida", Boolean, default=False),
            Column("fechaCreacion", DateTime(timezone=True)),
        )

    def _row_to_notificacion(self, row) -> Notificacion:
        return Notificacion(
            id=row.idNotificacion,
            idEmpleadoDestino=row.idEmpleadoDestino,
            tipo=row.tipo,
            mensaje=row.mensaje,
            idReferencia=row.idReferencia,
            leida=row.leida,
            fechaCreacion=row.fechaCreacion,
        )
