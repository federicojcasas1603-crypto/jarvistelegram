"""
Validador de acciones estructuradas.

Responsabilidades:
    1. Verificar que la acción esté en la whitelist de acciones permitidas.
    2. Validar que los parámetros obligatorios estén presentes y sean del tipo correcto.
    3. Verificar que las rutas de archivos sean seguras (no en carpetas del sistema).
    4. Forzar confirmación en acciones destructivas.
    5. Rechazar acciones con programas prohibidos.

Flujo:
    Action (de la IA) → ActionValidator.validate() → ValidationResult
    Si el resultado es válido, el despachador ejecuta la acción.
    Si no es válido, el motor informa al usuario del error.

Decisiones de diseño:
    - Se separa la validación de la ejecución para mantener SRP.
    - El esquema de cada acción se define como un diccionario estático.
      Esto facilita agregar nuevas acciones sin modificar la lógica de validación.
    - ValidationResult es un dataclass que contiene tanto el éxito/fallo
      como un mensaje descriptivo para debugging y logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.action_schemas import ACTION_SCHEMAS
from core.security import SecurityPolicy
from models.action import Action


@dataclass
class ValidationResult:
    """
    Resultado de la validación de una acción.

    Attributes:
        is_valid: True si la acción pasó todas las validaciones.
        errors: Lista de mensajes de error. Vacía si is_valid=True.
        requires_confirmation: True si la acción necesita confirmación del usuario.
        sanitized_action: Acción con parámetros corregidos (si aplica).
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    sanitized_action: Action | None = None

    @classmethod
    def valid(cls, action: Action, requires_confirmation: bool = False) -> ValidationResult:
        """Crea un resultado de validación exitoso."""
        return cls(
            is_valid=True,
            requires_confirmation=requires_confirmation,
            sanitized_action=action,
        )

    @classmethod
    def invalid(cls, errors: list[str]) -> ValidationResult:
        """Crea un resultado de validación fallido."""
        return cls(is_valid=False, errors=errors)


class ActionValidator:
    """
    Validador de acciones estructuradas.

    Se instancia con una SecurityPolicy y se reutiliza para validar
    todas las acciones que llegan de la IA.

    Example:
        >>> policy = SecurityPolicy()
        >>> validator = ActionValidator(policy)
        >>> result = validator.validate(action)
        >>> if result.is_valid:
        ...     # ejecutar acción
    """

    def __init__(self, policy: SecurityPolicy) -> None:
        """
        Inicializa el validador con una política de seguridad.

        Args:
            policy: Instancia de SecurityPolicy con las reglas a aplicar.
        """
        self._policy = policy

    def validate(self, action: Action) -> ValidationResult:
        """
        Valida una acción completa contra todas las políticas de seguridad.

        Aplica las siguientes verificaciones en orden:
            1. La acción está en la whitelist.
            2. La acción tiene un esquema registrado.
            3. Los parámetros obligatorios están presentes.
            4. Los tipos de los parámetros son correctos.
            5. Las rutas de archivos son seguras.
            6. Los programas no están prohibidos.
            7. La acción requiere confirmación forzosa.

        Args:
            action: Instancia de Action a validar.

        Returns:
            ValidationResult con el resultado de la validación.
        """
        errors: list[str] = []

        # --- 1. Verificar whitelist ---
        if not self._policy.is_action_allowed(action.action):
            return ValidationResult.invalid([
                f"Acción no permitida: '{action.action}'. "
                f"Acciones disponibles: {sorted(self._policy.allowed_actions)}"
            ])

        # --- 2. Verificar esquema registrado ---
        schema = ACTION_SCHEMAS.get(action.action)
        if schema is None:
            return ValidationResult.invalid([
                f"No hay esquema de parámetros registrado para '{action.action}'. "
                f"Esto significa que el comando aún no está implementado."
            ])

        # --- 3. Verificar parámetros obligatorios ---
        required_params = schema["required"]
        for param_name, expected_type in required_params:
            if param_name not in action.parameters:
                errors.append(
                    f"Falta el parámetro obligatorio '{param_name}' "
                    f"para la acción '{action.action}'."
                )
                continue

            # --- 4. Verificar tipos ---
            param_value = action.parameters[param_name]
            if expected_type is not None and not isinstance(param_value, expected_type):
                errors.append(
                    f"El parámetro '{param_name}' debe ser de tipo "
                    f"{expected_type.__name__}, pero se recibió "
                    f"{type(param_value).__name__}."
                )

        # --- 5. Verificar rutas seguras ---
        path_params = ["path", "source", "destination", "file_path",
                       "script_path", "directory", "old_name", "new_name"]
        for param_name in path_params:
            if param_name in action.parameters:
                param_value = action.parameters[param_name]
                if isinstance(param_value, str) and not self._policy.is_path_safe(param_value):
                    errors.append(
                        f"La ruta '{param_value}' del parámetro '{param_name}' "
                        f"está en una zona protegida del sistema."
                    )

        # --- 6. Verificar programas prohibidos ---
        if "program" in action.parameters:
            program = action.parameters["program"]
            if isinstance(program, str) and not self._policy.is_program_allowed(program):
                errors.append(
                    f"El programa '{program}' está en la lista de programas "
                    f"prohibidos por seguridad."
                )

        # --- 7. Forzar confirmación ---
        needs_confirmation = self._policy.requires_confirmation(action.action)

        # --- 8. Verificar extensiones prohibidas ---
        for param_name in path_params:
            if param_name in action.parameters:
                param_value = action.parameters[param_name]
                if isinstance(param_value, str) and not self._policy.is_extension_safe(param_value):
                    errors.append(
                        f"La extensión del archivo en '{param_name}' "
                        f"('{Path(param_value).suffix}') no está permitida."
                    )

        # --- Retornar resultado ---
        if errors:
            return ValidationResult.invalid(errors)

        return ValidationResult.valid(action, requires_confirmation=needs_confirmation)

    def get_allowed_actions(self) -> list[str]:
        """
        Retorna la lista ordenada de acciones permitidas.

        Útil para generar el system prompt de la IA de forma dinámica.
        La IA solo debe conocer las acciones que realmente puede ejecutar.

        Returns:
            Lista de strings con los nombres de las acciones permitidas.
        """
        return sorted(self._policy.allowed_actions)