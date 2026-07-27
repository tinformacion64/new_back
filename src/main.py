"""
Punto de entrada principal de la aplicación.
Configura y ejecuta el servidor FastAPI.
"""
from fastapi import FastAPI, Request, Depends
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config.settings import settings
from shared.infrastructure.security.rate_limiter import (
    rate_limit_exception_handler,
    limiter,
)
from shared.infrastructure.security.auth_middleware import JWTAuthMiddleware

# Esquema de seguridad global para Swagger UI / OpenAPI
security_scheme = HTTPBearer(auto_error=False)

# Crear la aplicación FastAPI
app = FastAPI(
    title="API de Comunicados Institucionales",
    description="Sistema de gestión de comunicados, tareas y evidencias universitarias",
    version="1.0.0",
    dependencies=[Depends(security_scheme)]
)

# Configurar rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

# Protección universal de rutas (Regla I.6): JWT obligatorio en todas las
# rutas salvo /api/empleado/login y /health. Se registra ANTES de CORS en
# el código para que CORS quede como capa más externa y las peticiones
# OPTIONS de preflight no se vean bloqueadas.
app.add_middleware(JWTAuthMiddleware)

# Configurar CORS - dominio del frontend Next.js
# En producción, se debe especificar el origen exacto
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://127.0.0.1:3000",
        "https://*.vercel.app",  # Next.js en Vercel
        "https://*.netlify.app",  # Next.js en Netlify
        "https://sgc-2-i-frontend.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Routers del módulo de catálogos
from modules.catalogos.infrastructure.entrypoints.api import (
    area_router,
    cargo_router,
    tipo_comunicado_router,
    medio_recepcion_router,
    rol_destinatario_router,
    rol_responsable_router,
    estado_tarea_router,
)

# Router del módulo de personal
from modules.personal.infrastructure.entrypoints.api import empleado_router

# Router del módulo de comunicados
from modules.comunicados.infrastructure.entrypoints.api import comunicado_router

# Router del módulo de tareas
from modules.tareas.infrastructure.entrypoints.api import tarea_router

# Router del módulo de evidencias
from modules.evidencias.infrastructure.entrypoints.api import evidencia_router

# Registrar routers
app.include_router(area_router)
app.include_router(cargo_router)
app.include_router(tipo_comunicado_router)
app.include_router(medio_recepcion_router)
app.include_router(rol_destinatario_router)
app.include_router(rol_responsable_router)
app.include_router(estado_tarea_router)
app.include_router(empleado_router)
app.include_router(comunicado_router)
app.include_router(tarea_router)
app.include_router(evidencia_router)


@app.get("/")
async def root():
    """Endpoint raíz de la API."""
    return {
        "message": "API de Comunicados Institucionales",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Exception handlers para SQLAlchemy
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Manejador para errores de integridad (duplicados, FK inválidas, etc.).
    Retorna 409 Conflict con mensaje limpio e imprime el detalle en consola.
    """
    print(f"⚠️ INTEGRITY ERROR en {request.url.path}: {exc}")
    return JSONResponse(
        status_code=409,
        content={
            "detail": f"Conflicto: el recurso ya existe o viola una restricción de integridad ({str(exc)})"
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    Manejador genérico para errores de SQLAlchemy.
    Imprime el Traceback real en consola para depuración.
    """
    import traceback
    print(f"❌ ERROR REAL DE SQLALCHEMY en {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Error interno de base de datos: {str(exc)}"
        }
    )


@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud.
    No requiere autenticación.
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )