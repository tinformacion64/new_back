"""
Configuración de la aplicación.
Carga variables de entorno y define configuraciones por defecto.
"""
import os
from dotenv import load_dotenv

# Cargar .env de forma robusta desde la raíz del proyecto
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
parent_root = os.path.dirname(project_root)
dotenv_path = os.path.join(parent_root, ".env")
load_dotenv(dotenv_path)

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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()