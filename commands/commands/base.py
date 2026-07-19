"""
Clase base abstracta para todos los comandos y registro central.

Todas las implementaciones de comandos (system.py, files.py, etc.)
heredan de Command e implementan execute().

Patrón de diseño:
    Se usa el patrón Command + Registry. Cada comando concreto se registra
    en el CommandRegistry al momento de importarse. El despachador solo
    necesita hacer registry.get("nombre_accion") para obtener el comando
    correspondiente y ejecutarlo.

    Esto permite:
    - Agregar nuevos comandos creando un archivo e importándolo.
    - No modificar el despachador al agregar comandos.
    - Mantener cada comando independiente y testeable.

Flujo de ejecución:
    Dispatcher → registry.get(action_name) → command.execute(params) → CommandResult
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class Command(ABC):
    """
    Clase abstracta base para todos los comandos.

    Cada comando concreto DEBE:
        1. Definir la propiedad 'name' (str): nombre que usa el dispatcher.
        2. Definir la propiedad 'description' (str): descripción legible.
        3. Implementar execute(params) -> CommandResult: la lógica real.

    Cada comando PUEDE:
        1. Sobreescribir validate_params() para validación personalizada.
        2. Sobreescribir requires_confirmation() para forzar confirmación.

    Example:
        >>> class HelloCommand(Command):
        ...     @property
        ...     def name(self) -> str:
        ...         return "hello"
        ...     @property
        ...     def description(self) -> str:
        ...         return "Saluda al usuario"
        ...     def execute(self, params: dict) -> CommandResult:
        ...         return CommandResult.ok("¡Hola mundo!")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre único del comando.

        Debe coincidir exactamente con el nombre que la IA usa en el
        campo 'action' del JSON. También debe coincidir con las claves
        de ACTION_SCHEMAS en core/action_schemas.py.

        Returns:
            Nombre del comando como string.
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Descripción legible del comando.

        Se usa en el system prompt para que la IA sepa qué hace cada
        comando y cuándo utilizarlo. Debe ser clara y concisa.

        Returns:
            Descripción del comando como string.
        """
        ...

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> CommandResult:
        """
        Ejecuta la lógica concreta del comando.

        Este es el método principal que el despachador invoca.
        El comando recibe los parámetros validados y debe retornar
        un CommandResult con el resultado de la operación.

        Args:
            params: Diccionario con los parámetros de la acción.
                    Ya fueron validados por el ActionValidator antes
                    de llegar aquí.

        Returns:
            CommandResult con el resultado de la ejecución.
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validación adicional de parámetros específica del comando.

        Se ejecuta DESPUÉS de la validación general del ActionValidator.
        Se usa para reglas de negocio que solo aplican a este comando.

        Por defecto retorna una lista vacía (sin errores).
        Sobreescribir en subclases cuando se necesite validación extra.

        Args:
            params: Diccionario con los parámetros a validar.

        Returns:
            Lista vacía si todo está correcto. Lista con mensajes de error
            si hay problemas.
        """
        return []

    def __str__(self) -> str:
        return f"Command({self.name}: {self.description})"


class CommandRegistry:
    """
    Registro central de comandos disponibles.

    Mapea nombres de acciones a instancias de Command.
    Es singleton: toda la aplicación usa la misma instancia.

    El registro se llena al importar los módulos de comandos.
    Cada módulo llama a registry.register() con su instancia.

    Example:
        >>> registry = CommandRegistry()
        >>> registry.register(SystemInfoCommand())
        >>> command = registry.get("system_info")
        >>> command.name
        'system_info'
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """
        Registra un comando en el registro.

        Si ya existe un comando con el mismo nombre, se sobreescribe
        y se emite un warning en los logs. Esto permite overrides
        en tests o configuraciones personalizadas.

        Args:
            command: Instancia de un subclase de Command.

        Raises:
            TypeError: Si el argumento no es una instancia de Command.
        """
        if not isinstance(command, Command):
            raise TypeError(
                f"Se esperaba una instancia de Command, se recibió "
                f"{type(command).__name__}."
            )

        if command.name in self._commands:
            logger.warning(
                "Comando '%s' ya estaba registrado. Sobreescriendo. "
                "Registrado originalmente: %s",
                command.name,
                self._commands[command.name].__class__.__name__,
            )

        self._commands[command.name] = command
        logger.debug("Comando registrado: %s (%s)", command.name, command.__class__.__name__)

    def get(self, name: str) -> Command | None:
        """
        Obtiene un comando por su nombre.

        Args:
            name: Nombre de la acción a buscar.

        Returns:
            La instancia de Command correspondiente, o None si no existe.
        """
        return self._commands.get(name)

    def has(self, name: str) -> bool:
        """
        Verifica si existe un comando registrado con ese nombre.

        Args:
            name: Nombre de la acción a verificar.

        Returns:
            True si el comando existe en el registro.
        """
        return name in self._commands

    def get_all(self) -> dict[str, Command]:
        """
        Retorna una copia del diccionario de comandos registrados.

        Returns:
            Diccionario con nombre -> Command.
        """
        return dict(self._commands)

    @property
    def count(self) -> int:
        """Número de comandos registrados."""
        return len(self._commands)

    def __repr__(self) -> str:
        names = sorted(self._commands.keys())
        return f"CommandRegistry({self.count} commands: {names})"


# ============================================
# INSTANCIA SINGLETON
# ============================================
# Toda la aplicación usa esta misma instancia.
# Se importa con: from commands import get_registry
_global_registry: CommandRegistry | None = None


def get_registry() -> CommandRegistry:
    """
    Retorna la instancia global del registro de comandos.

    Crea la instancia en la primera llamada (lazy singleton).

    Returns:
        Instancia singleton de CommandRegistry.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandRegistry()
    return _global_registry
