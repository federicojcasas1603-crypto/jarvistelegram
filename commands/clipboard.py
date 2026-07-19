"""
Comandos para leer y escribir en el portapapeles.

Uso desde Telegram: "¿Qué hay en el portapapeles?", "Copia esto al portapapeles".
"""

from __future__ import annotations

import logging
from typing import Any

import pyperclip

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class ClipboardReadCommand(Command):
    """Comando que lee el contenido del portapapeles."""

    @property
    def name(self) -> str:
        return "clipboard_read"

    @property
    def description(self) -> str:
        return "Lee el contenido actual del portapapeles"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            content = pyperclip.paste()
            if not content or not content.strip():
                return CommandResult.ok("El portapapeles está vacío.")
            # Truncar si es muy largo
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncado)"
            logger.info("Portapapeles leído (%d caracteres)", len(content))
            return CommandResult.ok(f"Contenido del portapapeles:\n{content}")
        except Exception as e:
            logger.exception("Error al leer portapapeles")
            return CommandResult.fail(f"Error al leer el portapapeles: {e}")


class ClipboardWriteCommand(Command):
    """Comando que escribe en el portapapeles."""

    @property
    def name(self) -> str:
        return "clipboard_write"

    @property
    def description(self) -> str:
        return "Escribe un texto en el portapapeles"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        text = params.get("text", "")
        if not text:
            return CommandResult.fail("No se especificó texto para copiar.")

        try:
            pyperclip.copy(str(text))
            logger.info("Texto copiado al portapapeles (%d caracteres)", len(str(text)))
            return CommandResult.ok(f"Texto copiado al portapapeles.")
        except Exception as e:
            logger.exception("Error al escribir en portapapeles")
            return CommandResult.fail(f"Error al escribir en el portapapeles: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        text = params.get("text")
        if not text or not str(text).strip():
            errors.append("El parámetro 'text' es obligatorio.")
        return errors


# Auto-registro
get_registry().register(ClipboardReadCommand())
get_registry().register(ClipboardWriteCommand())
