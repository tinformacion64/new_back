"""
Configuración de la aplicación.
Carga variables de entorno y define configuraciones por defecto.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno.
    """
    
    # Base de datos
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "api_user"
    DB_PASSWORD: str = "api_password_seguro"
    DB_NAME: str = "comunicados_db"
    DATABASE_URL: str = "postgresql://api_user:api_password_seguro@localhost:5432/comunicados_db"
    DATABASE_ECHO: bool = False
    
    # Almacenamiento de archivos
    FILE_STORAGE_PATH: str = "storage"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # Seguridad
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
     # Almacenamiento
    STORAGE_TYPE: str = "local"  # "local" o "cloudinary"
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()