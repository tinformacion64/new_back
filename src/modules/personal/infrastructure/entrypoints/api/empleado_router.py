"""
Router de API para el recurso Empleado.
Endpoints: /api/empleado (login, create) y /api/empleado/{id}/estatus
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, ConfigDict

from ....domain.entities import Empleado
from ....domain.ports import EmpleadoRepository
from ....infrastructure.persistence import EmpleadoRepositoryAdapter
from ....application.use_cases import (
    LoginEmpleadoUseCase,
    CreateEmpleadoUseCase,
    UpdateEmpleadoEstatusUseCase,
    ChangePasswordUseCase,
)
from modules.catalogos.domain.ports import AreaRepository, CargoRepository
from modules.catalogos.infrastructure.persistence import (
    AreaRepositoryAdapter,
    CargoRepositoryAdapter,
)
from shared.infrastructure.security.security import (
    get_current_user,
    get_current_active_user,
    require_roles,
)
from shared.infrastructure.security.rate_limiter import rate_limiter
from shared.domain.exceptions import BusinessRuleViolationError


router = APIRouter(prefix="/api/empleado", tags=["empleados"])


# DTOs
class LoginRequest(BaseModel):
    """Request para login de empleado."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response del login."""
    access_token: str
    token_type: str
    empleado: dict


class CreateEmpleadoRequest(BaseModel):
    """Request para crear empleado."""
    nombre: str
    email: EmailStr
    password: Optional[str] = None
    idArea: UUID
    cargos: List[UUID] = []
    acceso_sistema: bool = True


class EmpleadoResponse(BaseModel):
    """Response con datos de empleado."""
    id: str
    nombre: str
    email: str
    idArea: str
    activo: bool
    cargos: List[str] = []


def get_empleado_repository() -> EmpleadoRepository:
    """Factory para obtener el repositorio de empleados."""
    return EmpleadoRepositoryAdapter()


def get_area_repository() -> AreaRepository:
    """Factory para obtener el repositorio de áreas (catálogos)."""
    return AreaRepositoryAdapter()


def get_cargo_repository() -> CargoRepository:
    """Factory para obtener el repositorio de cargos (catálogos)."""
    return CargoRepositoryAdapter()


@router.post("/login", response_model=LoginResponse)
@rate_limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    repository: EmpleadoRepository = Depends(get_empleado_repository),
    cargo_repository: CargoRepository = Depends(get_cargo_repository),
) -> LoginResponse:
    """
    Login de empleado.
    Limitado a 5 peticiones/minuto por IP.
    No requiere autenticación previa.
    """
    use_case = LoginEmpleadoUseCase(repository, cargo_repository)
    
    try:
        result = use_case.execute(
            email=login_data.email,
            password=login_data.password,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/", response_model=List[EmpleadoResponse])
async def list_empleados(
    activo: Optional[bool] = None,
    current_user: dict = Depends(get_current_active_user),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
) -> List[EmpleadoResponse]:
    """
    Lista todos los empleados, permitiendo filtrar por estatus activo.
    """
    if activo is not None:
        empleados = repository.get_by_activo(activo)
    else:
        empleados = repository.get_all()
        
    cargo_repo = CargoRepositoryAdapter()
    res = []
    for emp in empleados:
        cargo_ids = repository.get_cargos(emp.id)
        cargo_nombres = []
        for c_id in cargo_ids:
            c = cargo_repo.get_by_id(c_id)
            if c:
                cargo_nombres.append(c.nombre)
        res.append(
            EmpleadoResponse(
                id=str(emp.id),
                nombre=emp.nombre,
                email=emp.email,
                idArea=str(emp.idArea),
                activo=emp.activo,
                cargos=cargo_nombres,
            )
        )
    return res


@router.post("/", response_model=EmpleadoResponse, status_code=201)
async def create_empleado(
    request: CreateEmpleadoRequest,
    current_user: dict = Depends(require_roles(["Administrador", "Director"])),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
    area_repository: AreaRepository = Depends(get_area_repository),
    cargo_repository: CargoRepository = Depends(get_cargo_repository),
) -> EmpleadoResponse:
    """
    Crea un nuevo empleado.
    Solo roles "Administrador"/"Director" pueden usarlo.
    Requiere JWT válido.
    """
    use_case = CreateEmpleadoUseCase(repository, area_repository, cargo_repository)
    
    try:
        empleado = use_case.execute(
            nombre=request.nombre,
            email=request.email,
            password=request.password,
            idArea=request.idArea,
            cargos=request.cargos,
            acceso_sistema=request.acceso_sistema,
        )
        
        cargo_ids = repository.get_cargos(empleado.id)
        cargo_nombres = []
        for c_id in cargo_ids:
            c = cargo_repository.get_by_id(c_id)
            if c:
                cargo_nombres.append(c.nombre)

        return EmpleadoResponse(
            id=str(empleado.id),
            nombre=empleado.nombre,
            email=empleado.email,
            idArea=str(empleado.idArea),
            activo=empleado.activo,
            cargos=cargo_nombres,
        )
    except BusinessRuleViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{empleado_id}/estatus", response_model=EmpleadoResponse)
async def update_empleado_estatus(
    empleado_id: UUID,
    activo: bool,
    current_user: dict = Depends(require_roles(["Director"])),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
) -> EmpleadoResponse:
    """
    Actualiza el estatus (activo) de un empleado.
    Solo roles "Director" pueden usarlo.
    Crea automáticamente un registro en HISTORIAL_ESTATUS.
    El idEmpleadoModifica viene del JWT, no del request.
    """
    use_case = UpdateEmpleadoEstatusUseCase(repository)
    
    try:
        use_case.execute(
            id=empleado_id,
            activo=activo,
            idEmpleadoModifica=UUID(current_user["idEmpleado"]),
        )
        
        # Obtener el empleado actualizado
        empleado = repository.get_by_id(empleado_id)
        
        cargo_ids = repository.get_cargos(empleado.id)
        cargo_nombres = []
        cargo_repo = CargoRepositoryAdapter()
        for c_id in cargo_ids:
            c = cargo_repo.get_by_id(c_id)
            if c:
                cargo_nombres.append(c.nombre)

        return EmpleadoResponse(
            id=str(empleado.id),
            nombre=empleado.nombre,
            email=empleado.email,
            idArea=str(empleado.idArea),
            activo=empleado.activo,
            cargos=cargo_nombres,
        )
    except BusinessRuleViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class ChangePasswordRequest(BaseModel):
    """Request para cambiar la contraseña del empleado."""
    nueva_password: str


@router.patch("/{empleado_id}/password")
async def change_password(
    empleado_id: UUID,
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
) -> dict:
    """
    Cambia la contraseña del empleado autenticado.
    El empleado solo puede cambiar su propia contraseña, a menos que
    sea Administrador o Director.
    """
    cargos = current_user.get("cargos_nombres", [])
    id_empleado_actual = UUID(current_user["idEmpleado"])
    es_admin_o_director = any(
        role and ("administrador" in role.lower() or "director" in role.lower())
        for role in cargos
    )

    if empleado_id != id_empleado_actual and not es_admin_o_director:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cambiar la contraseña de otro empleado",
        )

    use_case = ChangePasswordUseCase(repository)

    try:
        use_case.execute(
            empleado_id=empleado_id,
            nueva_password=request.nueva_password,
        )
        return {"message": "Contraseña actualizada correctamente"}
    except BusinessRuleViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class ToggleStatusRequest(BaseModel):
    """Request para cambiar de estatus a un empleado."""
    id_administrador: Optional[UUID] = None


class HistorialEstatusResponse(BaseModel):
    """Response con datos de historial de estatus."""
    id: str
    idEmpleadoAfectado: str
    idEmpleadoModifica: str
    accion: str
    fechaRegistro: Optional[str] = None
    modifierNombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmpleadoDetalleResponse(BaseModel):
    """Response con detalle de empleado e historial de estatus."""
    id: str
    nombre: str
    email: str
    idArea: str
    activo: bool
    cargos: List[str] = []
    historial: List[HistorialEstatusResponse] = []


@router.patch("/{empleado_id}/toggle-status", response_model=EmpleadoResponse)
async def toggle_empleado_status(
    empleado_id: UUID,
    request_data: Optional[ToggleStatusRequest] = None,
    id_administrador: Optional[UUID] = None,
    current_user: dict = Depends(get_current_active_user),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
) -> EmpleadoResponse:
    """
    Invierte el valor de activo del empleado y registra la acción en HISTORIAL_ESTATUS.
    """
    # 1. RBAC (Control de Acceso)
    cargos = current_user.get("cargos_nombres", [])
    print(f"DEBUG TOKEN CARGOS: {cargos}")
    if not any(role and ("administrador" in role.lower() or "director" in role.lower()) for role in cargos):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos requeridos (Administrador o Director) para alterar el estatus de un empleado."
        )

    # 2. Prevención de Auto-desactivación
    id_empleado_actual = UUID(current_user["idEmpleado"])
    if empleado_id == id_empleado_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes alterar tu propio estatus"
        )

    admin_id = None
    if request_data and request_data.id_administrador:
        admin_id = request_data.id_administrador
    elif id_administrador:
        admin_id = id_administrador
    else:
        admin_id = id_empleado_actual

    empleado = repository.get_by_id(empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    nuevo_activo = not empleado.activo

    try:
        repository.update_estatus(
            id=empleado_id,
            activo=nuevo_activo,
            idEmpleadoModifica=admin_id,
        )
        
        updated_emp = repository.get_by_id(empleado_id)
        cargo_ids = repository.get_cargos(empleado_id)
        cargo_nombres = []
        cargo_repo = CargoRepositoryAdapter()
        for c_id in cargo_ids:
            c = cargo_repo.get_by_id(c_id)
            if c:
                cargo_nombres.append(c.nombre)
        return EmpleadoResponse(
            id=str(updated_emp.id),
            nombre=updated_emp.nombre,
            email=updated_emp.email,
            idArea=str(updated_emp.idArea),
            activo=updated_emp.activo,
            cargos=cargo_nombres,
        )
    except BusinessRuleViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{empleado_id}", response_model=EmpleadoDetalleResponse)
async def get_empleado_detalle(
    empleado_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    repository: EmpleadoRepository = Depends(get_empleado_repository),
    cargo_repository: CargoRepository = Depends(get_cargo_repository),
) -> EmpleadoDetalleResponse:
    """
    Obtiene el detalle de un empleado con su historial de estatus ordenado desc.
    """
    empleado = repository.get_by_id(empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    cargo_ids = repository.get_cargos(empleado_id)
    cargo_nombres = []
    for c_id in cargo_ids:
        c = cargo_repository.get_by_id(c_id)
        if c:
            cargo_nombres.append(c.nombre)

    from modules.personal.infrastructure.persistence import HistorialEstatusRepositoryAdapter
    historial_repo = HistorialEstatusRepositoryAdapter()
    historial_items = historial_repo.get_by_empleado(empleado_id)

    return EmpleadoDetalleResponse(
        id=str(empleado.id),
        nombre=empleado.nombre,
        email=empleado.email,
        idArea=str(empleado.idArea),
        activo=empleado.activo,
        cargos=cargo_nombres,
        historial=[
            HistorialEstatusResponse(
                id=str(item.id),
                idEmpleadoAfectado=str(item.idEmpleadoAfectado),
                idEmpleadoModifica=str(item.idEmpleadoModifica),
                accion=item.accion.value,
                fechaRegistro=item.fechaRegistro.isoformat() if hasattr(item.fechaRegistro, "isoformat") else str(item.fechaRegistro) if item.fechaRegistro is not None else None,
                modifierNombre=repository.get_by_id(item.idEmpleadoModifica).nombre if repository.get_by_id(item.idEmpleadoModifica) else "Usuario Desconocido"
            )
            for item in historial_items
        ]
    )