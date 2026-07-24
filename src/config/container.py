"""
Contenedor de inyección de dependencias.
Registra y resuelve todas las dependencias del sistema.
"""
from typing import Dict, Any

from shared.infrastructure.database.connection import DatabaseConnection
from shared.infrastructure.storage.file_storage_adapter import FileStoragePort, LocalFileStorageAdapter
from shared.infrastructure.storage.cloudinary_storage_adapter import CloudinaryStorageAdapter
from shared.infrastructure.file_parsers.parser_factory import ParserFactory
from config.settings import settings


class Container:
    """
    Contenedor de dependencias.
    Implementa el patrón Service Locator para resolver dependencias.
    """
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_database_connection(cls) -> DatabaseConnection:
        """Obtiene la conexión a base de datos."""
        if "database" not in cls._instances:
            cls._instances["database"] = DatabaseConnection()
        return cls._instances["database"]
    
    @classmethod
    def get_file_storage(cls) -> FileStoragePort:
        """
        Obtiene el adaptador de almacenamiento de archivos.
        Usa LocalFileStorageAdapter o CloudinaryStorageAdapter
        según la configuración en settings.STORAGE_TYPE.
        """
        if "file_storage" not in cls._instances:
            if settings.STORAGE_TYPE == "cloudinary":
                cls._instances["file_storage"] = CloudinaryStorageAdapter()
            else:
                cls._instances["file_storage"] = LocalFileStorageAdapter(
                    base_path=settings.FILE_STORAGE_PATH
                )
        return cls._instances["file_storage"]
    
    @classmethod
    def get_parser_factory(cls) -> ParserFactory:
        """Obtiene la fábrica de parsers."""
        if "parser_factory" not in cls._instances:
            cls._instances["parser_factory"] = ParserFactory()
        return cls._instances["parser_factory"]
    
    @classmethod
    def clear(cls) -> None:
        """Limpia todas las instancias (útil para testing)."""
        cls._instances.clear()


# Instancia singleton del contenedor
container = Container()