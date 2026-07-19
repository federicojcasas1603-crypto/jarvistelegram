"""
Comando para crear carpetas.

Uso desde Telegram: "Crea una carpeta llamada Proyectos en Documentos".
"""

from __future__ import annotations

import logging
import os
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class CreateFolderCommand(Command):
    """Crea una carpeta en la ubicación especificada."""

    @property
    def name(self) -> str:
        return "create_folder"

    @property
    def description(self) -> str:
        return "Crea una carpeta nueva"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        path = os.path.expanduser(params.get("path", ""))

        if not path:
            return CommandResult.fail("No se especificó la ruta de la carpeta.")

        try:
            os.makedirs(path, exist_ok=True)
            logger.info("Carpeta creada: %s", path)
            return CommandResult.ok(f"Carpeta creada: {path}")
        except Exception as e:
            logger.exception("Error al crear carpeta")
            return CommandResult.fail(f"Error al crear la carpeta: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("path"):
            errors.append("El parámetro 'path' es obligatorio.")
        return errors


# Auto-registro
get_registry().register(CreateFolderCommand())
