"""
Comando para resumir documentos de texto.

Uso desde Telegram: "Resume el archivo README.md".
"""

from __future__ import annotations

import logging
import os
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

MAX_LINES = 500


class SummarizeDocumentCommand(Command):
    """Lee y resume un documento de texto plano."""

    @property
    def name(self) -> str:
        return "summarize_document"

    @property
    def description(self) -> str:
        return "Resume el contenido de un documento de texto"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        path = os.path.expanduser(params.get("file_path", ""))

        if not os.path.exists(path):
            return CommandResult.fail(f"Archivo no encontrado: {path}")

        ext = os.path.splitext(path)[1].lower()
        text_extensions = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".log", ".xml", ".yml", ".yaml"}
        if ext and ext not in text_extensions:
            return CommandResult.fail(
                f"Tipo de archivo no soportado ({ext}). "
                f"Soportados: {', '.join(sorted(text_extensions))}"
            )

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= MAX_LINES:
                        break
                    lines.append(line.rstrip())

            content = "\n".join(lines)
            word_count = len(content.split())

            if word_count < 20:
                return CommandResult.ok(f"Contenido del archivo ({word_count} palabras):\n```\n{content}\n```")

            # Retornar el contenido para que la IA lo resuma
            summary_request = (
                f"Resume el siguiente documento de {word_count} palabras "
                f"({len(lines)} líneas) en los puntos más importantes:\n\n"
                f"```\n{content}\n```"
            )
            return CommandResult.ok(summary_request)

        except Exception as e:
            logger.exception("Error al leer documento")
            return CommandResult.fail(f"Error al leer el documento: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("file_path"):
            errors.append("El parámetro 'file_path' es obligatorio.")
        return errors


# Auto-registro
get_registry().register(SummarizeDocumentCommand())
