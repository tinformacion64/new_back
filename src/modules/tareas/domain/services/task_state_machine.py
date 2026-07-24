"""
Máquina de Estados de Tarea (TaskStateMachine) con validación RBAC.
"""
from uuid import UUID
from typing import List, Optional
from shared.domain.exceptions import BusinessRuleViolationError


class TaskStateMachine:
    """
    Máquina de estados estricta para Tareas con Control de Acceso Basado en Roles (RBAC).
    """

    @staticmethod
    def validate_transition(
        current_state_name: str,
        target_state_name: str,
        user_id: UUID,
        user_roles: List[str],
        responsables: List[UUID],
        comunicado_creator_id: Optional[UUID] = None,
    ) -> None:
        """
        Valida que la transición sea lógica y que el usuario tenga los permisos adecuados.
        """
        curr = current_state_name.strip().upper().replace(" ", "_")
        target = target_state_name.strip().upper().replace(" ", "_")

        # 1. Estados Terminales: REVISADA y CANCELADA son inmutables
        if curr in ["REVISADA", "CANCELADA"]:
            raise BusinessRuleViolationError(
                f"La tarea se encuentra en el estado terminal '{curr}' y no se permiten más transiciones."
            )

        if curr == target:
            return

        # 2. De ASIGNADA a EN PROCESO
        if target == "EN_PROCESO":
            if curr == "ASIGNADA":
                if user_id not in responsables:
                    raise BusinessRuleViolationError(
                        "Solo los responsables asignados a la tarea pueden iniciarla (pasar a EN PROCESO)."
                    )

        # 3. De EN PROCESO, RECHAZADA o VENCIDA a ENTREGADA
        elif target == "ENTREGADA":
            if curr not in ["EN_PROCESO", "RECHAZADA", "VENCIDA"]:
                raise BusinessRuleViolationError(
                    f"No se puede entregar una evidencia si la tarea está en estado '{curr}'."
                )
            if user_id not in responsables:
                raise BusinessRuleViolationError(
                    "Solo los responsables asignados a la tarea pueden entregar evidencias (pasar a ENTREGADA)."
                )

        # 4. De ENTREGADA a REVISADA o RECHAZADA
        elif target in ["REVISADA", "RECHAZADA"]:
            if curr != "ENTREGADA" and target == "REVISADA":
                raise BusinessRuleViolationError(
                    f"No se puede revisar la tarea si no está entregada (estado actual: '{curr}')."
                )
            # Nota: de RECHAZADA a EN_PROCESO ya se maneja de forma natural, pero de ENTREGADA a RECHAZADA (regresa a EN_PROCESO) es la transición del Director.
            if not any(r and "director" in r.lower() for r in user_roles):
                raise BusinessRuleViolationError(
                    f"Solo los usuarios con rol 'Director' pueden marcar la tarea como '{target}'."
                )

        # 5. A CANCELADA: Solo Director o el creador/asignador (idEmpleadoRegistro del comunicado padre)
        elif target == "CANCELADA":
            is_director = any(r and "director" in r.lower() for r in user_roles)
            is_creator = comunicado_creator_id is not None and user_id == comunicado_creator_id
            if not (is_director or is_creator):
                raise BusinessRuleViolationError(
                    "Solo el director o el creador del comunicado original pueden cancelar la tarea."
                )
