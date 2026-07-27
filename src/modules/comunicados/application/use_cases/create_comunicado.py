"""
Use case para crear comunicados (Sección IV SGC2I).
"""
from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...domain.entities import Comunicado
from ...domain.ports import ComunicadoRepository
from shared.domain.exceptions import BusinessRuleViolationError


class CreateComunicadoUseCase:
    """
    Caso de uso para registrar un nuevo comunicado y sus destinatarios.

    Valida: folioDoi único, idEmisor (empleado activo), idTipoComunicado
    e idMedioRecepcion (catálogos existentes y no archivados), y cada
    idRolDestinatario (catálogo existente). idEmpleadoRegistro y
    fechaRegistro NUNCA vienen del payload: se inyectan desde el JWT
    (idEmpleadoRegistro) y desde la base de datos (fechaRegistro).
    """

    def __init__(
        self,
        repository: ComunicadoRepository,
        empleado_repository: Optional[Any] = None,
        tipo_comunicado_repository: Optional[Any] = None,
        medio_recepcion_repository: Optional[Any] = None,
        rol_destinatario_repository: Optional[Any] = None,
    ):
        self._repository = repository
        self._empleado_repository = empleado_repository
        self._tipo_comunicado_repository = tipo_comunicado_repository
        self._medio_recepcion_repository = medio_recepcion_repository
        self._rol_destinatario_repository = rol_destinatario_repository

    def execute(
        self,
        folioDoi: str,
        numComunicado: str,
        tema: str,
        fechaEmision: datetime,
        fechaRecepcion: datetime,
        idEmisor: UUID,
        idTipoComunicado: UUID,
        idMedioRecepcion: UUID,
        idEmpleadoRegistro: UUID,
        destinatarios: List[Dict[str, Any]],
        archivos: Optional[List[Dict[str, str]]] = None,
    ) -> Comunicado:
        # folioDoi único (verificación explícita de negocio, además de la
        # constraint UNIQUE de la base de datos)
        if self._repository.get_by_folio_doi(folioDoi) is not None:
            raise BusinessRuleViolationError(
                f"Ya existe un comunicado con folioDoi {folioDoi}"
            )

        # idEmisor debe ser un empleado activo
        if self._empleado_repository is not None:
            emisor = self._empleado_repository.get_by_id(idEmisor)
            if emisor is None:
                raise BusinessRuleViolationError(
                    f"El emisor {idEmisor} no existe"
                )
            if not emisor.activo:
                raise BusinessRuleViolationError(
                    f"El emisor {idEmisor} no está activo"
                )

        # idTipoComunicado debe existir y no estar archivado
        if self._tipo_comunicado_repository is not None:
            tipo = self._tipo_comunicado_repository.get_by_id(idTipoComunicado)
            if tipo is None:
                raise BusinessRuleViolationError(
                    f"El tipo de comunicado {idTipoComunicado} no existe"
                )
            if tipo.archivado:
                raise BusinessRuleViolationError(
                    f"El tipo de comunicado {idTipoComunicado} está archivado"
                )

        # idMedioRecepcion debe existir y no estar archivado
        if self._medio_recepcion_repository is not None:
            medio = self._medio_recepcion_repository.get_by_id(idMedioRecepcion)
            if medio is None:
                raise BusinessRuleViolationError(
                    f"El medio de recepción {idMedioRecepcion} no existe"
                )
            if medio.archivado:
                raise BusinessRuleViolationError(
                    f"El medio de recepción {idMedioRecepcion} está archivado"
                )

        # Cada idRolDestinatario debe existir en el catálogo
        if self._rol_destinatario_repository is not None:
            for dest in destinatarios:
                rol_id = dest["idRolDestinatario"]
                if self._rol_destinatario_repository.get_by_id(rol_id) is None:
                    raise BusinessRuleViolationError(
                        f"El rol de destinatario {rol_id} no existe"
                    )

        # Resolver url del primer archivo para fallback
        first_url = None
        if archivos and len(archivos) > 0:
            first_url = archivos[0]["urlArchivo"]

        # Crear la entidad (valida fechaRecepcion >= fechaEmision, longitudes, etc.)
        comunicado = Comunicado(
            folioDoi=folioDoi,
            numComunicado=numComunicado,
            tema=tema,
            fechaEmision=fechaEmision,
            fechaRecepcion=fechaRecepcion,
            idEmisor=idEmisor,
            idTipoComunicado=idTipoComunicado,
            idMedioRecepcion=idMedioRecepcion,
            idEmpleadoRegistro=idEmpleadoRegistro,
            archivoUrl=first_url,
        )

        # Insertar comunicado + destinatarios en una sola transacción
        return self._repository.add_with_destinatarios(comunicado, destinatarios, archivos=archivos)