"""
Adaptador de almacenamiento en Cloudinary.
Implementa el puerto FileStoragePort para guardar archivos en la nube.
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, BinaryIO
from src.shared.infrastructure.storage.file_storage_adapter import FileStoragePort
from src.config.settings import settings


class CloudinaryStorageAdapter(FileStoragePort):
    """
    Adaptador que guarda archivos en Cloudinary en vez de disco local.
    Implementa la misma interfaz FileStoragePort para ser intercambiable.
    """
    
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
    
    def save(self, file_content: bytes, filename: str, content_type: str) -> str:
        """
        Sube el archivo a Cloudinary y retorna la URL pública.
        
        Args:
            file_content: bytes del archivo
            filename: nombre original (solo para referencia)
            content_type: tipo MIME (image/jpeg, application/pdf, etc.)
        
        Returns:
            URL segura del archivo en Cloudinary
        """
        # Determinar carpeta según tipo de archivo
        carpeta = self._determinar_carpeta(content_type)
        
        try:
            resultado = cloudinary.uploader.upload(
                file_content,
                folder=f"sgc2i/{carpeta}",
                resource_type="auto",
                public_id=self._generar_nombre(filename)
            )
            return resultado["secure_url"]
        except Exception as e:
            raise Exception(f"Error al subir a Cloudinary: {str(e)}")
    
    def get(self, file_path: str) -> Optional[bytes]:
        """
        Cloudinary no devuelve bytes directamente.
        Retorna None; el frontend accede por URL.
        """
        return None
    
    def delete(self, file_path: str) -> None:
        """
        Elimina un archivo de Cloudinary.
        
        Args:
            file_path: URL o public_id del archivo en Cloudinary
        """
        try:
            # Extraer public_id de la URL si es necesario
            public_id = self._extraer_public_id(file_path)
            cloudinary.uploader.destroy(public_id)
        except Exception as e:
            raise Exception(f"Error al eliminar de Cloudinary: {str(e)}")
    
    def _determinar_carpeta(self, content_type: str) -> str:
        """Determina la carpeta en Cloudinary según el tipo de archivo."""
        if content_type.startswith("image/"):
            return "imagenes"
        elif content_type == "application/pdf":
            return "documentos"
        else:
            return "evidencias"
    
    def _generar_nombre(self, filename: str) -> str:
        """Genera un nombre único para evitar colisiones."""
        import uuid
        extension = filename.split(".")[-1] if "." in filename else ""
        return f"{uuid.uuid4().hex[:12]}"
    
    def _extraer_public_id(self, url: str) -> str:
        """
        Extrae el public_id de una URL de Cloudinary.
        """
        # Remover extensión y dominio
        partes = url.split("/")
        # Encontrar la parte después de "upload/"
        for i, parte in enumerate(partes):
            if parte == "upload":
                # Tomar todo después de upload/ (puede tener v1, v2, etc.)
                ruta = "/".join(partes[i+1:])
                # Remover versión si existe (ej: v1234567890/)
                if ruta.startswith("v") and ruta[1:11].isdigit():
                    ruta = "/".join(ruta.split("/")[1:])
                # Remover extensión
                if "." in ruta:
                    ruta = ".".join(ruta.split(".")[:-1])
                return ruta
        return url