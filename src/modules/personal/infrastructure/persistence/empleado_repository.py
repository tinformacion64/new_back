"""
Adaptador de persistencia para el repositorio de Empleados.
Usa SQLAlchemy Core con SQL crudo.
"""
from uuid import UUID
from typing import List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import Table, Column, String, Boolean, insert, select, update
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from ...domain.entities import Empleado, HistorialEstatus, AccionHistorial
from ...domain.ports import EmpleadoRepository, HistorialEstatusRepository
from shared.infrastructure.database.connection import DatabaseConnection


class EmpleadoRepositoryAdapter(EmpleadoRepository):
    """
    Implementación concreta del repositorio de Empleados.
    Usa SQLAlchemy Core con SQL crudo, respetando el esquema existente.
    """
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
    
    @contextmanager
    def _get_session(self):
        """
        Provee una sesión: reutiliza la inyectada (self._session) si existe,
        o abre y cierra una nueva con manejo ACID (commit/rollback) si no.
        """
        if self._session is not None:
            yield self._session
        else:
            with DatabaseConnection.get_session() as session:
                yield session
    
    @property
    def table(self) -> Table:
        """Define la tabla EMPLEADO según el esquema SQL."""
        metadata = DatabaseConnection.get_metadata()
        if "EMPLEADO" in metadata.tables:
            return metadata.tables["EMPLEADO"]
        return Table(
            "EMPLEADO",
            metadata,
            Column("idEmpleado", PG_UUID(as_uuid=True), primary_key=True),
            Column("nombre", String(100), nullable=False),
            Column("email", String(150), unique=True, nullable=False),
            Column("idArea", PG_UUID(as_uuid=True), nullable=False),
            Column("activo", Boolean, default=True),
            Column("fechaRegistro", String),  # Se maneja como TIMESTAMP
            Column("password_hash", String(255)),  # No está en el SQL original
        )
    
    def add(self, empleado: Empleado) -> Empleado:
        """Agrega un empleado y retorna la entidad persistida."""
        with self._get_session() as session:
            stmt = insert(self.table).values(
                idEmpleado=empleado.id,
                nombre=empleado.nombre,
                email=empleado.email,
                idArea=empleado.idArea,
                activo=empleado.activo,
                password_hash=empleado.password_hash
            ).returning(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
            )
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            return Empleado(
                id=row.idEmpleado,
                nombre=row.nombre,
                email=row.email,
                idArea=row.idArea,
                activo=row.activo,
                fechaRegistro=row.fechaRegistro,
                password_hash=empleado.password_hash,
            )
    
    def add_with_cargos(self, empleado: Empleado, cargo_ids: List[UUID]) -> Empleado:
        """
        Agrega un empleado y le asigna los cargos indicados (EMPLEADO_CARGO)
        en una sola transacción ACID (commit único al final, rollback si
        cualquier paso falla).
        """
        with self._get_session() as session:
            try:
                stmt = insert(self.table).values(
                    idEmpleado=empleado.id,
                    nombre=empleado.nombre,
                    email=empleado.email,
                    idArea=empleado.idArea,
                    activo=empleado.activo,
                    password_hash=empleado.password_hash
                ).returning(
                    self.table.c.idEmpleado,
                    self.table.c.nombre,
                    self.table.c.email,
                    self.table.c.idArea,
                    self.table.c.activo,
                    self.table.c.fechaRegistro,
                )
                
                result = session.execute(stmt)
                row = result.fetchone()
                
                if cargo_ids:
                    metadata = DatabaseConnection.get_metadata()
                    if "EMPLEADO_CARGO" in metadata.tables:
                        cargo_table = metadata.tables["EMPLEADO_CARGO"]
                    else:
                        cargo_table = Table(
                            "EMPLEADO_CARGO",
                            metadata,
                            Column("idEmpleado", PG_UUID(as_uuid=True), primary_key=True),
                            Column("idCargo", PG_UUID(as_uuid=True), primary_key=True),
                        )
                    for cargo_id in cargo_ids:
                        session.execute(
                            insert(cargo_table).values(
                                idEmpleado=row.idEmpleado,
                                idCargo=cargo_id,
                            )
                        )
                
                if self._session is not None:
                    session.commit()
                
                return Empleado(
                    id=row.idEmpleado,
                    nombre=row.nombre,
                    email=row.email,
                    idArea=row.idArea,
                    activo=row.activo,
                    fechaRegistro=row.fechaRegistro,
                    password_hash=empleado.password_hash,
                )
            except Exception:
                session.rollback()
                raise
    
    def get_by_id(self, id: UUID) -> Optional[Empleado]:
        """Obtiene un empleado por su ID."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
            ).where(self.table.c.idEmpleado == id)
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            if row is None:
                return None
            
            return Empleado(
                id=row.idEmpleado,
                nombre=row.nombre,
                email=row.email,
                idArea=row.idArea,
                activo=row.activo,
                fechaRegistro=row.fechaRegistro,
                password_hash=None,  # No se expone el hash
            )
    
    def get_by_email(self, email: str) -> Optional[Empleado]:
        """Obtiene un empleado por su email."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
                self.table.c.password_hash,
            ).where(self.table.c.email == email)
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            if row is None:
                return None
            
            return Empleado(
                id=row.idEmpleado,
                nombre=row.nombre,
                email=row.email,
                idArea=row.idArea,
                activo=row.activo,
                fechaRegistro=row.fechaRegistro,
                password_hash=row.password_hash,
            )
    
    def get_all(self) -> List[Empleado]:
        """Obtiene todos los empleados."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
            )
            
            result = session.execute(stmt)
            rows = result.fetchall()
            
            return [
                Empleado(
                    id=row.idEmpleado,
                    nombre=row.nombre,
                    email=row.email,
                    idArea=row.idArea,
                    activo=row.activo,
                    fechaRegistro=row.fechaRegistro,
                    password_hash=None,
                )
                for row in rows
            ]
    
    def get_by_activo(self, activo: bool) -> List[Empleado]:
        """Obtiene empleados filtrados por estatus activo."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
            ).where(self.table.c.activo == activo)
            
            result = session.execute(stmt)
            rows = result.fetchall()
            
            return [
                Empleado(
                    id=row.idEmpleado,
                    nombre=row.nombre,
                    email=row.email,
                    idArea=row.idArea,
                    activo=row.activo,
                    fechaRegistro=row.fechaRegistro,
                    password_hash=None,
                )
                for row in rows
            ]
    
    def update(self, empleado: Empleado) -> Empleado:
        """Actualiza un empleado existente."""
        with self._get_session() as session:
            stmt = update(self.table).where(
                self.table.c.idEmpleado == empleado.id
            ).values(
                nombre=empleado.nombre,
                email=empleado.email,
                idArea=empleado.idArea,
                activo=empleado.activo,
                password_hash=empleado.password_hash,
            ).returning(
                self.table.c.idEmpleado,
                self.table.c.nombre,
                self.table.c.email,
                self.table.c.idArea,
                self.table.c.activo,
                self.table.c.fechaRegistro,
            )
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            return Empleado(
                id=row.idEmpleado,
                nombre=row.nombre,
                email=row.email,
                idArea=row.idArea,
                activo=row.activo,
                fechaRegistro=row.fechaRegistro,
                password_hash=empleado.password_hash,
            )
    
    def update_estatus(
        self, 
        id: UUID, 
        activo: bool, 
        idEmpleadoModifica: UUID
    ) -> Empleado:
        """
        Actualiza el estatus de un empleado y crea registro en HISTORIAL_ESTATUS.
        Usa transacción ACID con rollback en caso de fallos.
        """
        with DatabaseConnection.get_session() as session:
            try:
                # Actualizar el estatus del empleado
                stmt = update(self.table).where(
                    self.table.c.idEmpleado == id
                ).values(
                    activo=activo
                ).returning(
                    self.table.c.idEmpleado,
                    self.table.c.nombre,
                    self.table.c.email,
                    self.table.c.idArea,
                    self.table.c.activo,
                    self.table.c.fechaRegistro,
                )
                
                result = session.execute(stmt)
                row = result.fetchone()
                
                # Crear registro en HISTORIAL_ESTATUS
                historial_repo = HistorialEstatusRepositoryAdapter(session)
                accion = AccionHistorial.DESACTIVACION if not activo else AccionHistorial.REACTIVACION
                
                historial = HistorialEstatus(
                    idEmpleadoAfectado=id,
                    idEmpleadoModifica=idEmpleadoModifica,
                    accion=accion,
                )
                historial_repo.add(historial)
                
                session.commit()
                
                return Empleado(
                    id=row.idEmpleado,
                    nombre=row.nombre,
                    email=row.email,
                    idArea=row.idArea,
                    activo=row.activo,
                    fechaRegistro=row.fechaRegistro,
                    password_hash=None,
                )
            except Exception:
                session.rollback()
                raise
    
    def get_cargos(self, idEmpleado: UUID) -> List[UUID]:
        """
        Obtiene los IDs de cargos asignados a un empleado.
        """
        with self._get_session() as session:
            metadata = DatabaseConnection.get_metadata()
            if "EMPLEADO_CARGO" in metadata.tables:
                empleado_cargo_table = metadata.tables["EMPLEADO_CARGO"]
            else:
                empleado_cargo_table = Table(
                    "EMPLEADO_CARGO",
                    metadata,
                    Column("idEmpleado", PG_UUID(as_uuid=True), primary_key=True),
                    Column("idCargo", PG_UUID(as_uuid=True), primary_key=True),
                )
            
            stmt = select(empleado_cargo_table.c.idCargo).where(
                empleado_cargo_table.c.idEmpleado == idEmpleado
            )
            
            result = session.execute(stmt)
            rows = result.fetchall()
            
            results = []
            for row in rows:
                id_c = getattr(row, "idCargo", None)
                if id_c is None:
                    id_c = getattr(row, "idcargo", None)
                if id_c is not None:
                    results.append(id_c)
            return results


def _get_row_fecha(row) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get("fechaRegistro") or row.get("fecharegistro") or row.get("fecha_registro")
    if hasattr(row, "_mapping"):
        return row._mapping.get("fechaRegistro") or row._mapping.get("fecharegistro") or row._mapping.get("fecha_registro")
    return getattr(row, "fechaRegistro", None) or getattr(row, "fecharegistro", None) or getattr(row, "fecha_registro", None)


class HistorialEstatusRepositoryAdapter(HistorialEstatusRepository):
    """
    Implementación concreta del repositorio de Historial de Estatus.
    Usa SQLAlchemy Core con SQL crudo, respetando el esquema existente.
    """
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
    
    @contextmanager
    def _get_session(self):
        """
        Provee una sesión: reutiliza la inyectada (self._session) si existe,
        o abre y cierra una nueva con manejo ACID (commit/rollback) si no.
        """
        if self._session is not None:
            yield self._session
        else:
            with DatabaseConnection.get_session() as session:
                yield session
    
    @property
    def table(self) -> Table:
        """Define la tabla HISTORIAL_ESTATUS según el esquema SQL."""
        metadata = DatabaseConnection.get_metadata()
        if "HISTORIAL_ESTATUS" in metadata.tables:
            return metadata.tables["HISTORIAL_ESTATUS"]
        return Table(
            "HISTORIAL_ESTATUS",
            metadata,
            Column("idHistorial", PG_UUID(as_uuid=True), primary_key=True),
            Column("idEmpleadoAfectado", PG_UUID(as_uuid=True), nullable=False),
            Column("idEmpleadoModifica", PG_UUID(as_uuid=True), nullable=False),
            Column("accion", String(50), nullable=False),
            Column("fechaRegistro", String),
        )
    
    def add(self, historial: HistorialEstatus) -> HistorialEstatus:
        """Agrega un registro de historial y retorna la entidad persistida."""
        with self._get_session() as session:
            from datetime import datetime, timezone
            stmt = insert(self.table).values(
                idHistorial=historial.id,
                idEmpleadoAfectado=historial.idEmpleadoAfectado,
                idEmpleadoModifica=historial.idEmpleadoModifica,
                accion=historial.accion.value,
                fechaRegistro=datetime.now(timezone.utc),
            ).returning(
                self.table.c.idHistorial,
                self.table.c.idEmpleadoAfectado,
                self.table.c.idEmpleadoModifica,
                self.table.c.accion,
                self.table.c.fechaRegistro,
            )
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            fecha_reg = _get_row_fecha(row)
            
            return HistorialEstatus(
                id=row.idHistorial,
                idEmpleadoAfectado=row.idEmpleadoAfectado,
                idEmpleadoModifica=row.idEmpleadoModifica,
                accion=AccionHistorial(row.accion),
                fechaRegistro=fecha_reg,
            )
    
    def get_by_id(self, id: UUID) -> Optional[HistorialEstatus]:
        """Obtiene un registro de historial por su ID."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idHistorial,
                self.table.c.idEmpleadoAfectado,
                self.table.c.idEmpleadoModifica,
                self.table.c.accion,
                self.table.c.fechaRegistro,
            ).where(self.table.c.idHistorial == id)
            
            result = session.execute(stmt)
            row = result.fetchone()
            
            if row is None:
                return None
            
            fecha_reg = _get_row_fecha(row)
            
            return HistorialEstatus(
                id=row.idHistorial,
                idEmpleadoAfectado=row.idEmpleadoAfectado,
                idEmpleadoModifica=row.idEmpleadoModifica,
                accion=AccionHistorial(row.accion),
                fechaRegistro=fecha_reg,
            )
    
    def get_all(self) -> List[HistorialEstatus]:
        """Obtiene todos los registros de historial."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idHistorial,
                self.table.c.idEmpleadoAfectado,
                self.table.c.idEmpleadoModifica,
                self.table.c.accion,
                self.table.c.fechaRegistro,
            )
            
            result = session.execute(stmt)
            rows = result.fetchall()
            
            results = []
            for row in rows:
                fecha_reg = _get_row_fecha(row)
                results.append(
                    HistorialEstatus(
                        id=row.idHistorial,
                        idEmpleadoAfectado=row.idEmpleadoAfectado,
                        idEmpleadoModifica=row.idEmpleadoModifica,
                        accion=AccionHistorial(row.accion),
                        fechaRegistro=fecha_reg,
                    )
                )
            return results
    
    def get_by_empleado(self, idEmpleado: UUID) -> List[HistorialEstatus]:
        """Obtiene el historial de estatus de un empleado."""
        with self._get_session() as session:
            stmt = select(
                self.table.c.idHistorial,
                self.table.c.idEmpleadoAfectado,
                self.table.c.idEmpleadoModifica,
                self.table.c.accion,
                self.table.c.fechaRegistro,
            ).where(
                self.table.c.idEmpleadoAfectado == idEmpleado
            ).order_by(
                self.table.c.fechaRegistro.desc()
            )
            
            result = session.execute(stmt)
            rows = result.fetchall()
            
            results = []
            for row in rows:
                fecha_reg = _get_row_fecha(row)
                results.append(
                    HistorialEstatus(
                        id=row.idHistorial,
                        idEmpleadoAfectado=row.idEmpleadoAfectado,
                        idEmpleadoModifica=row.idEmpleadoModifica,
                        accion=AccionHistorial(row.accion),
                        fechaRegistro=fecha_reg,
                    )
                )
            return results