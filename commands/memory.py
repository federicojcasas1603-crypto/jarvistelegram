"""
Comandos para guardar y recuperar datos de memoria.

Uso desde Telegram: "Recuerda que mi contraseña es X", "¿Qué contraseña tengo?".
"""

from __future__ import annotations

import logging
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult
from memory.memory_manager import save, recall, get_all

logger = logging.getLogger(__name__)


class SaveMemoryCommand(Command):
    """Guarda un dato en la memoria a largo plazo."""

    @property
    def name(self) -> str:
        return "save_memory"

    @property
    def description(self) -> str:
        return "Guarda un dato importante en la memoria del asistente"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        key = params.get("key", "").strip()
        value = params.get("value", "").strip()

        if not key:
            return CommandResult.fail("Se requiere una clave para guardar.")
        if not value:
            return CommandResult.fail("Se requiere un valor para guardar.")

        try:
            save(key, value)
            logger.info("Memoria guardada: %s = %s", key, value[:50])
            return CommandResult.ok(f"Guardado en memoria: '{key}' = '{value}'")
        except Exception as e:
            logger.exception("Error al guardar en memoria")
            return CommandResult.fail(f"Error al guardar en memoria: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("key"):
            errors.append("El parámetro 'key' es obligatorio.")
        if not params.get("value"):
            errors.append("El parámetro 'value' es obligatorio.")
        return errors


class RecallMemoryCommand(Command):
    """Recupera un dato de la memoria."""

    @property
    def name(self) -> str:
        return "recall_memory"

    @property
    def description(self) -> str:
        return "Recupera un dato guardado en la memoria del asistente"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        key = params.get("key", "").strip()

        if not key:
            # Mostrar todas las memorias
            all_memory = get_all()
            if not all_memory:
                return CommandResult.ok("La memoria está vacía. No hay datos guardados.")
            items = "\n".join(f"  {k}: {v}" for k, v in all_memory.items())
            return CommandResult.ok(f"Todos los datos en memoria:\n{items}")

        try:
            value = recall(key)
            if value is None:
                return CommandResult.ok(f"No hay nada guardado con la clave '{key}'.")
            return CommandResult.ok(f"'{key}' = '{value}'")
        except Exception as e:
            logger.exception("Error al recuperar de memoria")
            return CommandResult.fail(f"Error al recuperar de memoria: {e}")


# Auto-registro
get_registry().register(SaveMemoryCommand())
get_registry().register(RecallMemoryCommand())
