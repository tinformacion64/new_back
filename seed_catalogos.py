"""
Script utilitario de inicialización de Catálogos (Seeder).
Inserta de forma segura los Estados de Tarea y Cargos iniciales del sistema.
"""
import sys
import os
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Cargar .env de forma robusta desde la raíz del proyecto
root_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path)

# Asegurar que 'src' esté en el sys.path
sys.path.insert(0, os.path.join(root_dir, "src"))

from shared.infrastructure.database.connection import DatabaseConnection
from modules.catalogos.infrastructure.persistence import (
    EstadoTareaRepositoryAdapter,
    CargoRepositoryAdapter,
)
from modules.catalogos.domain.entities import EstadoTarea, Cargo


def seed():
    print("🌱 Iniciando seeder de catálogos fijos...")
    
    # Asegurarse de que el motor y metadatos estén inicializados
    engine = DatabaseConnection.get_engine()
    metadata = DatabaseConnection.get_metadata()
    
    estado_repo = EstadoTareaRepositoryAdapter()
    cargo_repo = CargoRepositoryAdapter()
    
    # Asegurarnos de que las tablas existan
    _ = [estado_repo.table, cargo_repo.table]
    metadata.create_all(bind=engine)
    
    # 1. Sembrar ESTADO_TAREA
    estados_fijos = [
        "ASIGNADA",
        "EN PROCESO",
        "ENTREGADA",
        "VENCIDA",
        "REVISADA",
        "RECHAZADA",
        "CANCELADA",
    ]
    
    print("\n--- Sembrando ESTADO_TAREA ---")
    for nombre_estado in estados_fijos:
        # Se busca con normalización
        estado_db = estado_repo.get_by_nombre(nombre_estado)
        if not estado_db:
            new_estado = EstadoTarea(nombre=nombre_estado.lower())
            estado_repo.add(new_estado)
            print(f"✅ Creado Estado: '{nombre_estado}'")
        else:
            print(f"ℹ️ Ya existe Estado: '{nombre_estado}'")
            
    # 2. Sembrar CARGO
    cargos_fijos = [
        "Administrador",
        "Director",
        "Docente",
    ]
    
    print("\n--- Sembrando CARGO ---")
    for nombre_cargo in cargos_fijos:
        cargo_db = cargo_repo.get_by_nombre(nombre_cargo)
        if not cargo_db:
            new_cargo = Cargo(nombre=nombre_cargo)
            cargo_repo.add(new_cargo)
            print(f"✅ Creado Cargo: '{nombre_cargo}'")
        else:
            print(f"ℹ️ Ya existe Cargo: '{nombre_cargo}'")
            
    print("\n🎉 Seeding de catálogos completado exitosamente.")


if __name__ == "__main__":
    seed()
