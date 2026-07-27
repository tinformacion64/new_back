"""
Script utilitario de inicialización (Seeder).
Crea las tablas en la base de datos e inserta los registros iniciales requeridos:
- Área: Dirección General
- Cargo: Administrador de Sistema / Administrador
- Empleado: Administrador Sistema (email: admin@sistema.com, pass: Admin123!)
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

from sqlalchemy import Table, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from shared.infrastructure.database.connection import DatabaseConnection
from shared.infrastructure.security.security import get_password_hash

from modules.catalogos.infrastructure.persistence import (
    AreaRepositoryAdapter,
    CargoRepositoryAdapter,
    TipoComunicadoRepositoryAdapter,
    MedioRecepcionRepositoryAdapter,
    RolDestinatarioRepositoryAdapter,
    RolResponsableRepositoryAdapter,
    EstadoTareaRepositoryAdapter,
)
from modules.catalogos.domain.entities import Area, Cargo
from modules.personal.infrastructure.persistence import (
    EmpleadoRepositoryAdapter,
    HistorialEstatusRepositoryAdapter,
)
from modules.personal.domain.entities import Empleado
from modules.comunicados.infrastructure.persistence import ComunicadoRepositoryAdapter
from modules.tareas.infrastructure.persistence import TareaRepositoryAdapter
from modules.evidencias.infrastructure.persistence import EvidenciaRepositoryAdapter


def init_db_tables():
    """Registra todos los esquemas de tablas en metadata y ejecuta create_all."""
    area_repo = AreaRepositoryAdapter()
    cargo_repo = CargoRepositoryAdapter()
    tipo_repo = TipoComunicadoRepositoryAdapter()
    medio_repo = MedioRecepcionRepositoryAdapter()
    rol_dest_repo = RolDestinatarioRepositoryAdapter()
    rol_resp_repo = RolResponsableRepositoryAdapter()
    estado_repo = EstadoTareaRepositoryAdapter()
    empleado_repo = EmpleadoRepositoryAdapter()
    historial_repo = HistorialEstatusRepositoryAdapter()
    comunicado_repo = ComunicadoRepositoryAdapter()
    tarea_repo = TareaRepositoryAdapter()
    evidencia_repo = EvidenciaRepositoryAdapter()

    metadata = DatabaseConnection.get_metadata()

    # Registrar explícitamente la tabla intermedia EMPLEADO_CARGO en metadata
    if "EMPLEADO_CARGO" not in metadata.tables:
        Table(
            "EMPLEADO_CARGO",
            metadata,
            Column("idEmpleado", PG_UUID(as_uuid=True), primary_key=True),
            Column("idCargo", PG_UUID(as_uuid=True), primary_key=True),
        )

    # Forzar evaluación de propiedades .table y relacionales
    _ = [
        area_repo.table,
        cargo_repo.table,
        tipo_repo.table,
        medio_repo.table,
        rol_dest_repo.table,
        rol_resp_repo.table,
        estado_repo.table,
        empleado_repo.table,
        historial_repo.table,
        comunicado_repo.table,
        comunicado_repo.destinatario_table,
        tarea_repo.table,
        tarea_repo.responsable_table,
        evidencia_repo.table,
        evidencia_repo.tarea_evidencia_table,
    ]

    engine = DatabaseConnection.get_engine()
    metadata.create_all(bind=engine)
    print("🧱 Tablas de la base de datos creadas/verificadas correctamente con metadata.create_all().")


def seed():
    print("🌱 Iniciando proceso de seeding inicial...")

    # 0. Crear tablas automáticamente antes del seeding
    init_db_tables()

    area_repo = AreaRepositoryAdapter()
    cargo_repo = CargoRepositoryAdapter()
    empleado_repo = EmpleadoRepositoryAdapter()

    try:
        # 1. Crear Área "Dirección General"
        area = area_repo.get_by_nombre("Dirección General")
        if not area:
            new_area = Area(nombre="Dirección General")
            area = area_repo.add(new_area)
            print(f"✅ Área creada: 'Dirección General' (ID: {area.id})")
        else:
            print(f"ℹ️ Área ya existente: 'Dirección General' (ID: {area.id})")

        # 2. Crear Cargos ("Administrador de Sistema" y "Administrador")
        cargo_admin_sys = cargo_repo.get_by_nombre("Administrador de Sistema")
        if not cargo_admin_sys:
            cargo_admin_sys = cargo_repo.add(Cargo(nombre="Administrador de Sistema"))
            print(f"✅ Cargo creado: 'Administrador de Sistema' (ID: {cargo_admin_sys.id})")
        else:
            print(f"ℹ️ Cargo ya existente: 'Administrador de Sistema' (ID: {cargo_admin_sys.id})")

        cargo_admin = cargo_repo.get_by_nombre("Administrador")
        if not cargo_admin:
            cargo_admin = cargo_repo.add(Cargo(nombre="Administrador"))
            print(f"✅ Cargo creado: 'Administrador' (ID: {cargo_admin.id})")
        else:
            print(f"ℹ️ Cargo ya existente: 'Administrador' (ID: {cargo_admin.id})")

        # 3. Crear Estados de Tarea base si no existen
        estado_repo = EstadoTareaRepositoryAdapter()
        estados_base = ["asignada", "en proceso", "entregada", "vencida", "revisada", "rechazada", "cancelada"]
        for st_name in estados_base:
            if not estado_repo.get_by_nombre(st_name):
                from modules.catalogos.domain.entities import EstadoTarea
                estado_repo.add(EstadoTarea(nombre=st_name))
                print(f"✅ Estado de Tarea creado: '{st_name}'")

        # 4. Crear Empleado Administrador
        admin_email = "admin@sistema.com"
        admin_emp = empleado_repo.get_by_email(admin_email)
        if not admin_emp:
            admin_pw = os.getenv('ADMIN_INIT_PASSWORD', 'admin_local_dev_123')
            hashed_pw = get_password_hash(admin_pw)
            new_emp = Empleado(
                nombre="Administrador Sistema",
                email=admin_email,
                idArea=area.id,
                activo=True,
                password_hash=hashed_pw
            )
            admin_emp = empleado_repo.add_with_cargos(new_emp, [cargo_admin_sys.id, cargo_admin.id])
            print(f"✅ Empleado Admin creado con éxito:")
            print(f"   - Email: {admin_email}")
            print(f"   - Contraseña: [ADMIN_INIT_PASSWORD u ocultada por defecto]")
            print(f"   - ID Empleado: {admin_emp.id}")
        else:
            print(f"ℹ️ Empleado Admin ya existente (Email: {admin_email}, ID: {admin_emp.id})")

        print("\n🎉 Seeding completado exitosamente. ¡Ya puedes autenticarte!")

    except Exception as e:
        print(f"❌ Error durante el seeding de base de datos: {e}")
        raise


if __name__ == "__main__":
    seed()
