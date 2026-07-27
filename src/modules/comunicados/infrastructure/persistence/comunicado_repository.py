"""
Adaptador de persistencia para el repositorio de Comunicados.
Usa SQLAlchemy Core, respetando el esquema existente.
"""
from uuid import UUID
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import Table, Column, String, DateTime, insert, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from ...domain.entities import Comunicado
from ...domain.ports import ComunicadoRepository
from shared.infrastructure.database.connection import DatabaseConnection


class ComunicadoRepositoryAdapter(ComunicadoRepository):
    """
    Implementación concreta del repositorio de Comunicados.
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
        """Define la tabla COMUNICADO según el esquema SQL."""
        metadata = DatabaseConnection.get_metadata()
        if "COMUNICADO" in metadata.tables:
            return metadata.tables["COMUNICADO"]
        return Table(
            "COMUNICADO",
            metadata,
            Column("idComunicado", PG_UUID(as_uuid=True), primary_key=True),
            Column("folioDoi", String(100), unique=True, nullable=False),
            Column("numComunicado", String(50), nullable=False),
            Column("tema", String(200), nullable=False),
            Column("fechaEmision", DateTime(timezone=True), nullable=False),
            Column("fechaRecepcion", DateTime(timezone=True), nullable=False),
            Column("fechaRegistro", DateTime(timezone=True)),
            Column("idEmisor", PG_UUID(as_uuid=True), nullable=False),
            Column("idTipoComunicado", PG_UUID(as_uuid=True), nullable=False),
            Column("idMedioRecepcion", PG_UUID(as_uuid=True), nullable=False),
            Column("idEmpleadoRegistro", PG_UUID(as_uuid=True), nullable=False),
        )

    @property
    def destinatario_table(self) -> Table:
        """Define la tabla COMUNICADO_DESTINATARIO según el esquema SQL."""
        metadata = DatabaseConnection.get_metadata()
        if "COMUNICADO_DESTINATARIO" in metadata.tables:
            return metadata.tables["COMUNICADO_DESTINATARIO"]
        return Table(
            "COMUNICADO_DESTINATARIO",
            metadata,
            Column("idComunicado", PG_UUID(as_uuid=True), primary_key=True),
            Column("idDestinatario", PG_UUID(as_uuid=True), primary_key=True),
            Column("idRolDestinatario", PG_UUID(as_uuid=True), nullable=False),
        )

    @property
    def archivo_table(self) -> Table:
        """Define la tabla COMUNICADO_ARCHIVO según el esquema SQL."""
        metadata = DatabaseConnection.get_metadata()
        if "COMUNICADO_ARCHIVO" in metadata.tables:
            return metadata.tables["COMUNICADO_ARCHIVO"]
        return Table(
            "COMUNICADO_ARCHIVO",
            metadata,
            Column("idArchivo", PG_UUID(as_uuid=True), primary_key=True),
            Column("idComunicado", PG_UUID(as_uuid=True), nullable=False),
            Column("urlArchivo", String(500), nullable=False),
            Column("nombreOriginal", String(255), nullable=False),
            Column("fechaRegistro", DateTime(timezone=True)),
        )

    def add_with_destinatarios(
        self, comunicado: Comunicado, destinatarios: List[Dict[str, Any]], archivos: Optional[List[Dict[str, str]]] = None
    ) -> Comunicado:
        """
        Inserta el comunicado y sus destinatarios en una sola transacción
        ACID (commit único al final, rollback si cualquier paso falla).
        fechaRegistro NO se envía: la asigna la base de datos (DEFAULT
        CURRENT_TIMESTAMP), nunca el cliente.
        """
        with self._get_session() as session:
            try:
                stmt = insert(self.table).values(
                    idComunicado=comunicado.id,
                    folioDoi=comunicado.folioDoi,
                    numComunicado=comunicado.numComunicado,
                    tema=comunicado.tema,
                    fechaEmision=comunicado.fechaEmision,
                    fechaRecepcion=comunicado.fechaRecepcion,
                    idEmisor=comunicado.idEmisor,
                    idTipoComunicado=comunicado.idTipoComunicado,
                    idMedioRecepcion=comunicado.idMedioRecepcion,
                    idEmpleadoRegistro=comunicado.idEmpleadoRegistro,
                ).returning(
                    self.table.c.idComunicado,
                    self.table.c.folioDoi,
                    self.table.c.numComunicado,
                    self.table.c.tema,
                    self.table.c.fechaEmision,
                    self.table.c.fechaRecepcion,
                    self.table.c.fechaRegistro,
                    self.table.c.idEmisor,
                    self.table.c.idTipoComunicado,
                    self.table.c.idMedioRecepcion,
                    self.table.c.idEmpleadoRegistro,
                )
                result = session.execute(stmt)
                row = result.fetchone()

                for dest in destinatarios:
                    session.execute(
                        insert(self.destinatario_table).values(
                            idComunicado=row.idComunicado,
                            idDestinatario=dest["idDestinatario"],
                            idRolDestinatario=dest["idRolDestinatario"],
                        )
                    )

                if archivos:
                    import uuid
                    for file_info in archivos:
                        session.execute(
                            insert(self.archivo_table).values(
                                idArchivo=uuid.uuid4(),
                                idComunicado=row.idComunicado,
                                urlArchivo=file_info["urlArchivo"],
                                nombreOriginal=file_info["nombreOriginal"]
                            )
                        )
                elif comunicado.archivoUrl:
                    import uuid
                    session.execute(
                        insert(self.archivo_table).values(
                            idArchivo=uuid.uuid4(),
                            idComunicado=row.idComunicado,
                            urlArchivo=comunicado.archivoUrl,
                            nombreOriginal="documento_adjunto.pdf"
                        )
                    )

                if self._session is not None:
                    session.commit()

                # Popular archivos para el retorno de la entidad
                ret_archivos = archivos if archivos else []
                if not ret_archivos and comunicado.archivoUrl:
                    ret_archivos = [{"urlArchivo": comunicado.archivoUrl, "nombreOriginal": "documento_adjunto.pdf"}]

                return Comunicado(
                    id=row.idComunicado,
                    folioDoi=row.folioDoi,
                    numComunicado=row.numComunicado,
                    tema=comunicado.tema,
                    fechaEmision=row.fechaEmision,
                    fechaRecepcion=row.fechaRecepcion,
                    fechaRegistro=row.fechaRegistro,
                    idEmisor=row.idEmisor,
                    idTipoComunicado=row.idTipoComunicado,
                    idMedioRecepcion=row.idMedioRecepcion,
                    idEmpleadoRegistro=row.idEmpleadoRegistro,
                    archivoUrl=comunicado.archivoUrl,
                    archivos=ret_archivos
                )
            except Exception:
                session.rollback()
                raise

    def _get_archivos(self, session, id_comunicado: UUID) -> List[Dict[str, str]]:
        stmt = select(
            self.archivo_table.c.urlArchivo,
            self.archivo_table.c.nombreOriginal
        ).where(self.archivo_table.c.idComunicado == id_comunicado)
        rows = session.execute(stmt).fetchall()
        return [
            {"urlArchivo": row.urlArchivo, "nombreOriginal": row.nombreOriginal}
            for row in rows
        ]

    def get_by_id(self, id: UUID) -> Optional[Comunicado]:
        with self._get_session() as session:
            from modules.personal.infrastructure.persistence import EmpleadoRepositoryAdapter
            from modules.catalogos.infrastructure.persistence import AreaRepositoryAdapter
            
            emp_table = EmpleadoRepositoryAdapter().table
            area_table = AreaRepositoryAdapter().table
            archivo_table = self.archivo_table
            
            emisor_alias = emp_table.alias("emisor")
            registro_alias = emp_table.alias("registro")
            
            stmt = (
                select(
                    self.table,
                    area_table.c.nombre.label("area_emisora_nombre"),
                    registro_alias.c.nombre.label("empleado_registro_nombre"),
                    archivo_table.c.urlArchivo.label("archivo_url"),
                    archivo_table.c.nombreOriginal.label("archivo_nombre_original"),
                )
                .select_from(
                    self.table
                    .join(emisor_alias, self.table.c.idEmisor == emisor_alias.c.idEmpleado)
                    .join(area_table, emisor_alias.c.idArea == area_table.c.idArea)
                    .join(registro_alias, self.table.c.idEmpleadoRegistro == registro_alias.c.idEmpleado)
                    .outerjoin(archivo_table, self.table.c.idComunicado == archivo_table.c.idComunicado)
                )
                .where(self.table.c.idComunicado == id)
            )
            rows = session.execute(stmt).fetchall()
            if not rows:
                return None
            
            first_row = rows[0]
            com = Comunicado(
                id=first_row.idComunicado,
                folioDoi=first_row.folioDoi,
                numComunicado=first_row.numComunicado,
                tema=first_row.tema,
                fechaEmision=first_row.fechaEmision,
                fechaRecepcion=first_row.fechaRecepcion,
                fechaRegistro=first_row.fechaRegistro,
                idEmisor=first_row.idEmisor,
                idTipoComunicado=first_row.idTipoComunicado,
                idMedioRecepcion=first_row.idMedioRecepcion,
                idEmpleadoRegistro=first_row.idEmpleadoRegistro,
                areaEmisoraNombre=first_row.area_emisora_nombre,
                empleadoRegistroNombre=first_row.empleado_registro_nombre,
                archivoUrl=first_row.archivo_url,
                archivos=[]
            )
            
            for row in rows:
                if row.archivo_url:
                    com.archivos.append({
                        "urlArchivo": row.archivo_url,
                        "nombreOriginal": row.archivo_nombre_original
                    })
            return com

    def get_by_folio_doi(self, folio_doi: str) -> Optional[Comunicado]:
        with self._get_session() as session:
            from modules.personal.infrastructure.persistence import EmpleadoRepositoryAdapter
            from modules.catalogos.infrastructure.persistence import AreaRepositoryAdapter
            
            emp_table = EmpleadoRepositoryAdapter().table
            area_table = AreaRepositoryAdapter().table
            archivo_table = self.archivo_table
            
            emisor_alias = emp_table.alias("emisor")
            registro_alias = emp_table.alias("registro")
            
            stmt = (
                select(
                    self.table,
                    area_table.c.nombre.label("area_emisora_nombre"),
                    registro_alias.c.nombre.label("empleado_registro_nombre"),
                    archivo_table.c.urlArchivo.label("archivo_url"),
                    archivo_table.c.nombreOriginal.label("archivo_nombre_original"),
                )
                .select_from(
                    self.table
                    .join(emisor_alias, self.table.c.idEmisor == emisor_alias.c.idEmpleado)
                    .join(area_table, emisor_alias.c.idArea == area_table.c.idArea)
                    .join(registro_alias, self.table.c.idEmpleadoRegistro == registro_alias.c.idEmpleado)
                    .outerjoin(archivo_table, self.table.c.idComunicado == archivo_table.c.idComunicado)
                )
                .where(self.table.c.folioDoi == folio_doi)
            )
            rows = session.execute(stmt).fetchall()
            if not rows:
                return None
            
            first_row = rows[0]
            com = Comunicado(
                id=first_row.idComunicado,
                folioDoi=first_row.folioDoi,
                numComunicado=first_row.numComunicado,
                tema=first_row.tema,
                fechaEmision=first_row.fechaEmision,
                fechaRecepcion=first_row.fechaRecepcion,
                fechaRegistro=first_row.fechaRegistro,
                idEmisor=first_row.idEmisor,
                idTipoComunicado=first_row.idTipoComunicado,
                idMedioRecepcion=first_row.idMedioRecepcion,
                idEmpleadoRegistro=first_row.idEmpleadoRegistro,
                areaEmisoraNombre=first_row.area_emisora_nombre,
                empleadoRegistroNombre=first_row.empleado_registro_nombre,
                archivoUrl=first_row.archivo_url,
                archivos=[]
            )
            for row in rows:
                if row.archivo_url:
                    com.archivos.append({
                        "urlArchivo": row.archivo_url,
                        "nombreOriginal": row.archivo_nombre_original
                    })
            return com

    def get_all(self) -> List[Comunicado]:
        """Lista todos los comunicados de la bandeja principal."""
        with self._get_session() as session:
            from modules.personal.infrastructure.persistence import EmpleadoRepositoryAdapter
            from modules.catalogos.infrastructure.persistence import AreaRepositoryAdapter
            
            emp_table = EmpleadoRepositoryAdapter().table
            area_table = AreaRepositoryAdapter().table
            archivo_table = self.archivo_table
            
            emisor_alias = emp_table.alias("emisor")
            registro_alias = emp_table.alias("registro")
            
            stmt = (
                select(
                    self.table,
                    area_table.c.nombre.label("area_emisora_nombre"),
                    registro_alias.c.nombre.label("empleado_registro_nombre"),
                    archivo_table.c.urlArchivo.label("archivo_url"),
                    archivo_table.c.nombreOriginal.label("archivo_nombre_original"),
                )
                .select_from(
                    self.table
                    .join(emisor_alias, self.table.c.idEmisor == emisor_alias.c.idEmpleado)
                    .join(area_table, emisor_alias.c.idArea == area_table.c.idArea)
                    .join(registro_alias, self.table.c.idEmpleadoRegistro == registro_alias.c.idEmpleado)
                    .outerjoin(archivo_table, self.table.c.idComunicado == archivo_table.c.idComunicado)
                )
            )
            rows = session.execute(stmt).fetchall()
            
            comunicados_map = {}
            for row in rows:
                com_id = row.idComunicado
                if com_id not in comunicados_map:
                    comunicados_map[com_id] = Comunicado(
                        id=row.idComunicado,
                        folioDoi=row.folioDoi,
                        numComunicado=row.numComunicado,
                        tema=row.tema,
                        fechaEmision=row.fechaEmision,
                        fechaRecepcion=row.fechaRecepcion,
                        fechaRegistro=row.fechaRegistro,
                        idEmisor=row.idEmisor,
                        idTipoComunicado=row.idTipoComunicado,
                        idMedioRecepcion=row.idMedioRecepcion,
                        idEmpleadoRegistro=row.idEmpleadoRegistro,
                        areaEmisoraNombre=row.area_emisora_nombre,
                        empleadoRegistroNombre=row.empleado_registro_nombre,
                        archivoUrl=row.archivo_url,
                        archivos=[]
                    )
                if row.archivo_url:
                    comunicados_map[com_id].archivos.append({
                        "urlArchivo": row.archivo_url,
                        "nombreOriginal": row.archivo_nombre_original
                    })
            return list(comunicados_map.values())

    def get_destinatarios(self, id_comunicado: UUID) -> List[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(self.destinatario_table).where(
                self.destinatario_table.c.idComunicado == id_comunicado
            )
            rows = session.execute(stmt).fetchall()
            return [
                {
                    "idDestinatario": row.idDestinatario,
                    "idRolDestinatario": row.idRolDestinatario,
                }
                for row in rows
            ]