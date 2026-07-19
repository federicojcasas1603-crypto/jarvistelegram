"""
Despachador de acciones.

Responsabilidades:
    1. Recibir una Action validada y buscar el Command correspondiente.
    2. Ejecutar validación de parámetros específica del comando.
    3. Invocar execute() del comando y capturar el resultado.
    4. Manejar errores de ejecución de forma robusta.
    5. Registrar cada acción despachada en los logs.

Flujo:
    Action → validate() → ¿válido? → execute() → CommandResult
                                ↓
                          Resultado con errores

Diseño:
    El despachador tiene dos métodos separados:
    - validate(): Solo verifica que la acción sea ejecutable.
      Se usa ANTES de pedir confirmación al usuario.
    - execute(): Ejecuta el comando directamente.
      Se usa DESPUÉS de que el usuario confirma (o si no necesita confirmación).

    Esta separación permite al motor implementar flujos de confirmación
    sin duplicar lógica de validación.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from commands.base import CommandRegistry
from core.action_validator import ActionValidator, ValidationResult
from models.action import Action
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class Dispatcher:
    """
    Despachador central de acciones del sistema.

    Conecta las Actions (de la IA) con los Commands (implementaciones concretas).
    Usa ActionValidator para verificar seguridad y CommandRegistry para
    encontrar la implementación correcta.

    Example:
        >>> dispatcher = Dispatcher(registry, validator)
        >>> # Validar antes de ejecutar
        >>> validation = dispatcher.validate(action)
        >>> if validation.is_valid:
        ...     result = dispatcher.execute(action)
    """

    def __init__(self, registry: CommandRegistry, validator: ActionValidator) -> None:
        """
        Inicializa el despachador.

        Args:
            registry: Registro de comandos disponibles.
            validator: Validador de acciones con las políticas de seguridad.
        """
        self._registry = registry
        self._validator = validator

    def validate(self, action: Action) -> ValidationResult:
        """
        Valida una acción sin ejecutarla.

        Verifica whitelist, parámetros, tipos, rutas y programas.
        Retorna un ValidationResult que indica si la acción es segura
        para ejecutar y si requiere confirmación del usuario.

        Este método se llama ANTES de enviar la solicitud de confirmación
        al usuario, para rechazar acciones inválidas inmediatamente.

        Args:
            action: Acción a validar.

        Returns:
            ValidationResult con el resultado de la validación.
        """
        logger.debug("Validando acción: %s", action)

        # Validación general de seguridad (whitelist, tipos, rutas)
        result = self._validator.validate(action)

        if not result.is_valid:
            logger.warning(
                "Acción rechazada por validación: %s. Errores: %s",
                action.action,
                result.errors,
            )
            return result

        # Verificar que exista el comando en el registry
        command = self._registry.get(action.action)
        if command is None:
            return ValidationResult.invalid([
                f"No hay implementación registrada para la acción '{action.action}'. "
                f"Acciones disponibles: {sorted(self._registry.get_all().keys())}"
            ])

        # Validación específica del comando
        param_errors = command.validate_params(action.parameters)
        if param_errors:
            return ValidationResult.invalid(param_errors)

        logger.debug("Acción validada correctamente: %s", action)
        return result

    def execute(self, action: Action) -> CommandResult:
        """
        Ejecuta un comando a partir de una acción.

        Este método asume que la validación ya pasó (validate() fue llamado
        y retornó is_valid=True). No vuelve a validar por razones de
        rendimiento.

        Captura cualquier excepción que el comando lance y la convierte
        en un CommandResult.fail() para que el sistema nunca crashee.

        Args:
            action: Acción a ejecutar (ya validada).

        Returns:
            CommandResult con el resultado de la ejecución.
        """
        start_time = time.monotonic()

        logger.info("Ejecutando acción: %s", action)

        # Buscar el comando en el registry
        command = self._registry.get(action.action)
        if command is None:
            # Esto no debería pasar si validate() fue llamado antes,
            # pero es una protección adicional.
            error_msg = f"Comando no encontrado: '{action.action}'"
            logger.error(error_msg)
            return CommandResult.fail(message=error_msg)

        try:
            # Ejecutar el comando
            result = command.execute(action.parameters)

            # Calcular tiempo de ejecución
            elapsed = time.monotonic() - start_time

            if result.success:
                logger.info(
                    "Comando ejecutado: %s (%.2fs) - %s",
                    action.action,
                    elapsed,
                    result.message[:100],
                )
            else:
                logger.warning(
                    "Comando falló: %s (%.2fs) - Error: %s",
                    action.action,
                    elapsed,
                    result.error,
                )

            return result

        except Exception as e:
            elapsed = time.monotonic() - start_time
            error_msg = (
                f"Excepción no capturada al ejecutar '{action.action}': {type(e).__name__}: {e}"
            )
            logger.exception(error_msg)
            return CommandResult.fail(
                message=f"Error inesperado al ejecutar '{action.action}'. Revisa los logs.",
                error=error_msg,
            )

    def get_command_info(self) -> list[dict[str, str]]:
        """
        Retorna información de todos los comandos registrados.

        Útil para generar el system prompt dinámicamente y para debugging.

        Returns:
            Lista de diccionarios con 'name' y 'description' de cada comando.
        """
        info = []
        for name, command in sorted(self._registry.get_all().items()):
            info.append({
                "name": name,
                "description": command.description,
            })
        return info

    @property
    def registered_actions(self) -> list[str]:
        """Lista ordenada de nombres de acciones registradas."""
        return sorted(self._registry.get_all().keys())