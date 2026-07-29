"""
Use case para cambiar la contraseña de un empleado.
Valida reglas mínimas y guarda el hash usando hash_password() de security.py.
"""
from uuid import UUID

from ...domain.ports import EmpleadoRepository
from ...domain.entities import Empleado
from shared.domain.exceptions import BusinessRuleViolationError
from shared.infrastructure.security.security import get_password_hash, verify_password


class ChangePasswordUseCase:
    """
    Caso de uso para cambiar la contraseña de un empleado.
    Aplica reglas de validación y hashing con bcrypt.
    """
    
    def __init__(self, repository: EmpleadoRepository):
        self._repository = repository
    
    def execute(self, empleado_id: UUID, nueva_password: str) -> None:
        """
        Cambia la contraseña del empleado.
        Valida complejidad y guarda el hash (nunca el texto plano).
        """
        if not nueva_password or len(nueva_password.strip()) < 8:
            raise BusinessRuleViolationError(
                "La contraseña debe tener al menos 8 caracteres"
            )
        
        empleado = self._repository.get_by_id(empleado_id)
        if empleado is None:
            raise BusinessRuleViolationError(f"Empleado con ID {empleado_id} no encontrado")
        
        hashed = get_password_hash(nueva_password)
        
        empleado.password_hash = hashed
        empleado_actualizado = self._repository.update(empleado)
        
        return empleado_actualizado
    
    def reset_password(self, empleado_id: UUID) -> str:
        """
        Genera una contraseña temporal, la hashea y la retorna.
        Solo para uso administrativo.
        """
        import random
        import string
        
        empleado = self._repository.get_by_id(empleado_id)
        if empleado is None:
            raise BusinessRuleViolationError(f"Empleado con ID {empleado_id} no encontrado")
        
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        hashed = get_password_hash(temp_password)
        
        empleado.password_hash = hashed
        self._repository.update(empleado)
        
        return temp_password