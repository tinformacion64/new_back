"""
Middleware de protección universal de rutas (Regla I.6).
Exige un JWT válido en el header Authorization para TODAS las rutas,
sin excepción, salvo las explícitamente listadas en PUBLIC_PATHS.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import verify_token
from .exceptions import AuthenticationError, TokenExpiredError

# Únicas rutas públicas permitidas por la especificación y documentación de la API.
PUBLIC_PATHS = {
    "/",
    "/api/empleado/login",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que exige un JWT válido en el header Authorization
    para todas las rutas, excepto las definidas en PUBLIC_PATHS.
    Deja pasar peticiones OPTIONS sin token para no romper el
    preflight de CORS.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "No autenticado: falta el token JWT"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = verify_token(token)
            print(f"[AUTH_MIDDLEWARE] Token válido para ruta {request.url.path}, usuario: {payload.get('idEmpleado')}, roles: {payload.get('cargos_nombres')}")
        except (AuthenticationError, TokenExpiredError) as e:
            print(f"[AUTH_MIDDLEWARE] Token inválido para ruta {request.url.path}: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={"detail": str(e)},
            )

        # Disponible para los endpoints via request.state.current_user
        request.state.current_user = payload
        return await call_next(request)
