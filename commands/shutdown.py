"""
Comandos de apagado, reinicio y suspensión del sistema.

Uso desde Telegram: "Apaga la PC", "Reinicia", "Suspender".
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class ShutdownCommand(Command):
    """Apaga el sistema."""

    @property
    def name(self) -> str:
        return "shutdown"

    @property
    def description(self) -> str:
        return "Apaga o reinicia el sistema (requiere confirmación)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        action_type = params.get("action_type", "shutdown")

        try:
            if action_type == "restart":
                subprocess.run(["shutdown", "/r", "/t", "10"], check=True)
                logger.info("Reinicio programado en 10 segundos")
                return CommandResult.ok("Reinicio programado en 10 segundos.")
            elif action_type == "suspend":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
                logger.info("Sistema suspendido")
                return CommandResult.ok("Sistema suspendido.")
            else:
                subprocess.run(["shutdown", "/s", "/t", "10"], check=True)
                logger.info("Apagado programado en 10 segundos")
                return CommandResult.ok("Apagado programado en 10 segundos. Cancela con: shutdown /a")
        except Exception as e:
            logger.exception("Error al ejecutar %s", action_type)
            return CommandResult.fail(f"Error al {action_type}: {e}")

    def requires_confirmation(self) -> bool:
        return True


class RestartCommand(Command):
    """Reinicia el sistema."""

    @property
    def name(self) -> str:
        return "restart"

    @property
    def description(self) -> str:
        return "Reinicia el sistema (requiere confirmación)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            subprocess.run(["shutdown", "/r", "/t", "10"], check=True)
            logger.info("Reinicio programado en 10 segundos")
            return CommandResult.ok("Reinicio programado en 10 segundos.")
        except Exception as e:
            logger.exception("Error al reiniciar")
            return CommandResult.fail(f"Error al reiniciar: {e}")

    def requires_confirmation(self) -> bool:
        return True


class SuspendCommand(Command):
    """Suspende el sistema."""

    @property
    def name(self) -> str:
        return "suspend"

    @property
    def description(self) -> str:
        return "Suspende el sistema (requiere confirmación)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
            logger.info("Sistema suspendido")
            return CommandResult.ok("Sistema suspendido.")
        except Exception as e:
            logger.exception("Error al suspender")
            return CommandResult.fail(f"Error al suspender: {e}")

    def requires_confirmation(self) -> bool:
        return True


# Auto-registro
get_registry().register(ShutdownCommand())
get_registry().register(RestartCommand())
get_registry().register(SuspendCommand())
