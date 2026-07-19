"""
Comandos para gestión de archivos: buscar, copiar, mover, renombrar, eliminar, leer.

Cada acción es una subclase de Command que se auto-registra.
Uso desde Telegram: "Busca archivos .pdf", "Copia archivo X a Y".
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

# Límite de líneas para lectura de archivos de texto
MAX_READ_LINES = 500


class SearchFilesCommand(Command):
    """Busca archivos por nombre en un directorio."""

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return "Busca archivos por nombre en el sistema"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        query = params.get("query", "").strip()
        directory = params.get("directory", ".")
        recursive = params.get("recursive", True)

        if not query:
            return CommandResult.fail("Se requiere un término de búsqueda.")

        directory = os.path.expanduser(directory)
        if not os.path.isdir(directory):
            return CommandResult.fail(f"Directorio no encontrado: {directory}")

        try:
            matches = []
            pattern = f"*{query}*"
            search_func = Path(directory).rglob if recursive else Path(directory).glob

            for path in search_func(pattern):
                if len(matches) >= 20:
                    break
                rel = os.path.relpath(path, directory)
                size = path.stat().st_size if path.is_file() else 0
                matches.append(f"  {'📁' if path.is_dir() else '📄'} {rel} ({self._fmt_size(size)})")

            if not matches:
                return CommandResult.ok(f"No se encontraron archivos con '{query}' en {directory}")

            result = f"Archivos encontrados ({len(matches)}):\n" + "\n".join(matches)
            if len(matches) >= 20:
                result += "\n... (máximo 20 resultados)"
            return CommandResult.ok(result)

        except Exception as e:
            logger.exception("Error al buscar archivos")
            return CommandResult.fail(f"Error al buscar: {e}")

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


class CopyFileCommand(Command):
    """Copia un archivo de origen a destino."""

    @property
    def name(self) -> str:
        return "copy_file"

    @property
    def description(self) -> str:
        return "Copia un archivo de una ubicación a otra"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        src = os.path.expanduser(params.get("source", ""))
        dst = os.path.expanduser(params.get("destination", ""))

        if not os.path.exists(src):
            return CommandResult.fail(f"Archivo de origen no encontrado: {src}")

        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
                shutil.copy2(src, dst)
            logger.info("Archivo copiado: %s -> %s", src, dst)
            return CommandResult.ok(f"Archivo copiado a: {dst}")
        except Exception as e:
            logger.exception("Error al copiar archivo")
            return CommandResult.fail(f"Error al copiar: {e}")


class MoveFileCommand(Command):
    """Mueve un archivo de origen a destino."""

    @property
    def name(self) -> str:
        return "move_file"

    @property
    def description(self) -> str:
        return "Mueve un archivo de una ubicación a otra"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        src = os.path.expanduser(params.get("source", ""))
        dst = os.path.expanduser(params.get("destination", ""))

        if not os.path.exists(src):
            return CommandResult.fail(f"Archivo de origen no encontrado: {src}")

        try:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            shutil.move(src, dst)
            logger.info("Archivo movido: %s -> %s", src, dst)
            return CommandResult.ok(f"Archivo movido a: {dst}")
        except Exception as e:
            logger.exception("Error al mover archivo")
            return CommandResult.fail(f"Error al mover: {e}")


class RenameFileCommand(Command):
    """Renombra un archivo."""

    @property
    def name(self) -> str:
        return "rename_file"

    @property
    def description(self) -> str:
        return "Renombra un archivo"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        old = os.path.expanduser(params.get("old_name", ""))
        new_name = params.get("new_name", "")

        if not os.path.exists(old):
            return CommandResult.fail(f"Archivo no encontrado: {old}")

        try:
            dst = os.path.join(os.path.dirname(old), new_name)
            os.rename(old, dst)
            logger.info("Archivo renombrado: %s -> %s", old, dst)
            return CommandResult.ok(f"Archivo renombrado a: {new_name}")
        except Exception as e:
            logger.exception("Error al renombrar archivo")
            return CommandResult.fail(f"Error al renombrar: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("old_name"):
            errors.append("El parámetro 'old_name' es obligatorio.")
        if not params.get("new_name"):
            errors.append("El parámetro 'new_name' es obligatorio.")
        return errors


class DeleteFileCommand(Command):
    """Elimina un archivo (requiere confirmación)."""

    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return "Elimina un archivo (requiere confirmación)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        path = os.path.expanduser(params.get("path", ""))

        if not os.path.exists(path):
            return CommandResult.fail(f"Archivo no encontrado: {path}")

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            logger.info("Archivo eliminado: %s", path)
            return CommandResult.ok(f"Archivo eliminado: {path}")
        except Exception as e:
            logger.exception("Error al eliminar archivo")
            return CommandResult.fail(f"Error al eliminar: {e}")

    def requires_confirmation(self) -> bool:
        return True


class ReadFileCommand(Command):
    """Lee el contenido de un archivo de texto."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Lee el contenido de un archivo de texto"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        path = os.path.expanduser(params.get("file_path", ""))
        max_lines = params.get("max_lines", MAX_READ_LINES)

        if not os.path.exists(path):
            return CommandResult.fail(f"Archivo no encontrado: {path}")

        if os.path.getsize(path) > 5 * 1024 * 1024:
            return CommandResult.fail("El archivo es demasiado grande (>5MB). Usa max_lines para limitar.")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncado después de {max_lines} líneas)")
                        break
                    lines.append(line.rstrip())

            content = "\n".join(lines)
            return CommandResult.ok(f"Contenido de {os.path.basename(path)}:\n```\n{content}\n```")
        except Exception as e:
            logger.exception("Error al leer archivo")
            return CommandResult.fail(f"Error al leer el archivo: {e}")


class SendFileCommand(Command):
    """Marca un archivo para enviarlo por Telegram."""

    @property
    def name(self) -> str:
        return "send_file"

    @property
    def description(self) -> str:
        return "Envía un archivo por Telegram"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        path = os.path.expanduser(params.get("file_path", ""))

        if not os.path.exists(path):
            return CommandResult.fail(f"Archivo no encontrado: {path}")

        if os.path.getsize(path) > 50 * 1024 * 1024:
            return CommandResult.fail("El archivo es demasiado grande (>50MB) para enviar por Telegram.")

        logger.info("Archivo preparado para envío: %s", path)
        return CommandResult.ok(f"Enviando archivo: {os.path.basename(path)}", send_file=path)


# Auto-registro
get_registry().register(SearchFilesCommand())
get_registry().register(CopyFileCommand())
get_registry().register(MoveFileCommand())
get_registry().register(RenameFileCommand())
get_registry().register(DeleteFileCommand())
get_registry().register(ReadFileCommand())
get_registry().register(SendFileCommand())
