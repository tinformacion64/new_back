"""
Componentes de seguridad: JWT, hash de contraseñas y dependencias de autenticación.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import settings
from .exceptions import AuthenticationError, TokenExpiredError


# Contexto para hash de contraseñas con bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad para JWT
security_scheme = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que una contraseña en texto plano coincida con su hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt.
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT con los datos proporcionados.
    Incluye idEmpleado, email y roles/cargos en el payload.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verifica y decodifica un token JWT.
    Lanza excepción si el token es inválido o expiró.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("El token ha expirado")
    except JWTError:
        raise AuthenticationError("Token inválido")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Dependencia de FastAPI que extrae y verifica el usuario del token JWT.
    Retorna el payload del token con idEmpleado, email y roles.
    """
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        return payload
    except (AuthenticationError, TokenExpiredError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependencia que verifica que el usuario esté activo consultando la base de datos.
    """
    from uuid import UUID
    from modules.personal.infrastructure.persistence import EmpleadoRepositoryAdapter

    id_empleado = current_user.get("idEmpleado")
    if not id_empleado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene id de empleado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = EmpleadoRepositoryAdapter()
    empleado = repo.get_by_id(UUID(id_empleado))
    print(f"[AUTH] Verificando activo para empleado {id_empleado}: encontrado={empleado is not None}, activo={getattr(empleado, 'activo', None)}")
    if empleado is None or not empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_roles(allowed_roles: List[str]):
    """
    Dependencia de FastAPI que exige que el usuario autenticado tenga
    al menos uno de los roles/cargos indicados (por nombre, ej. "Director").
    Requiere que el JWT incluya "cargos_nombres" (generado en el login).
    Uso: Depends(require_roles(["Administrador", "Director"]))
    """
    def checker(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        user_roles = current_user.get("cargos_nombres", [])
        allowed_lower = [a.lower() for a in allowed_roles]
        if not any(role and any(allowed in role.lower() for allowed in allowed_lower) for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere alguno de estos roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return checker
