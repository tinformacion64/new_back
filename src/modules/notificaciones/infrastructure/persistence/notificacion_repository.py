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

    def add(self, notificacion: Notificacion) -> Notificacion:
        """Agrega una notificación y retorna la entidad persistida."""
        with self._get_session() as session:
            stmt = insert(self.table).values(
                idNotificacion=notificacion.id or uuid4(),
                idEmpleadoDestino=notificacion.idEmpleadoDestino,
                tipo=notificacion.tipo,
                mensaje=notificacion.mensaje,
                idReferencia=notificacion.idReferencia,
                leida=False,
                fechaCreacion=datetime.now(timezone.utc),
            ).returning(self.table)
            row = session.execute(stmt).fetchone()
            session.commit()
            return self._row_to_notificacion(row)

    def get_by_id(self, id: UUID) -> Optional[Notificacion]:
        """Obtiene una notificación por su ID."""
        with self._get_session() as session:
            stmt = select(self.table).where(self.table.c.idNotificacion == id)
            row = session.execute(stmt).fetchone()
            return self._row_to_notificacion(row) if row else None

    def get_by_empleado(self, idEmpleado: UUID, skip: int = 0, limit: int = 100) -> List[Notificacion]:
        """Obtiene las notificaciones de un empleado con paginación."""
        with self._get_session() as session:
            stmt = (
                select(self.table)
                .where(self.table.c.idEmpleadoDestino == idEmpleado)
                .order_by(self.table.c.fechaCreacion.desc())
                .offset(skip)
                .limit(limit)
            )
            rows = session.execute(stmt).fetchall()
            return [self._row_to_notificacion(r) for r in rows]

    def get_no_leidas_by_empleado(self, idEmpleado: UUID) -> List[Notificacion]:
        """Obtiene las notificaciones no leídas de un empleado."""
        with self._get_session() as session:
            stmt = select(self.table).where(
                self.table.c.idEmpleadoDestino == idEmpleado,
                self.table.c.leida == False,
            )
            rows = session.execute(stmt).fetchall()
            return [self._row_to_notificacion(r) for r in rows]

    def marcar_leida(self, id: UUID, idEmpleado: UUID) -> Notificacion:
        """Marca una notificación como leída."""
        with self._get_session() as session:
            stmt = (
                update(self.table)
                .where(self.table.c.idNotificacion == id, self.table.c.idEmpleadoDestino == idEmpleado)
                .values(leida=True)
                .returning(self.table)
            )
            row = session.execute(stmt).fetchone()
            session.commit()
            if row is None:
                raise ValueError("Notificacion no encontrada")
            return self._row_to_notificacion(row)
