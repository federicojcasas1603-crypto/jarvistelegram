"""
Comandos para navegar por carpetas del sistema.

Uso desde Telegram: /ls, /cd C:/Users/feder/Documents
"""

from __future__ import annotations

import logging
import os
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

# Directorio actual por usuario (persiste en memoria)
_user_dirs: dict[int, str] = {}


class ListDirectoryCommand(Command):
    """Lista el contenido de una carpeta."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "Lista el contenido de una carpeta (como ls/dir)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        user_id = params.get("_user_id", 0)
        path = params.get("path", "").strip()

        current = _user_dirs.get(user_id, os.path.expanduser("~"))

        if not path:
            path = current
        else:
            path = os.path.expanduser(path)
            if not os.path.isabs(path):
                path = os.path.join(current, path)

        path = os.path.abspath(path)

        if not os.path.isdir(path):
            return CommandResult.fail(f"Carpeta no encontrada: {path}")

        try:
            items = []
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    items.append(f"  [DIR]  {name}/")
                else:
                    size = os.path.getsize(full)
                    items.append(f"  [FILE] {name}  ({self._fmt(size)})")

            if not items:
                return CommandResult.ok(f"Carpeta vacía: {path}")

            result = f"Contenido de {path}:\n" + "\n".join(items)
            result += f"\n\n{len(items)} elementos"
            return CommandResult.ok(result)

        except PermissionError:
            return CommandResult.fail(f"Sin permisos para leer: {path}")
        except Exception as e:
            return CommandResult.fail(f"Error al listar: {e}")

    @staticmethod
    def _fmt(size: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f}{u}"
            size /= 1024
        return f"{size:.1f}TB"


class ChangeDirectoryCommand(Command):
    """Cambia el directorio de trabajo del usuario."""

    @property
    def name(self) -> str:
        return "cd"

    @property
    def description(self) -> str:
        return "Cambia la carpeta de trabajo (como cd en terminal)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        user_id = params.get("_user_id", 0)
        path = params.get("path", "").strip()

        current = _user_dirs.get(user_id, os.path.expanduser("~"))

        if not path or path == "~":
            path = os.path.expanduser("~")
        elif path == "..":
            path = os.path.dirname(current)
        elif path == ".":
            path = current
        else:
            path = os.path.expanduser(path)
            # Si es ruta relativa, combinar con directorio actual
            if not os.path.isabs(path):
                path = os.path.join(current, path)

        path = os.path.abspath(path)

        if not os.path.isdir(path):
            return CommandResult.fail(f"Carpeta no encontrada: {path}")

        _user_dirs[user_id] = path
        return CommandResult.ok(f"Directorio actual: {path}")


# Auto-registro
get_registry().register(ListDirectoryCommand())
get_registry().register(ChangeDirectoryCommand())


class DirCommand(ListDirectoryCommand):
    """Alias de /ls para compatibilidad con style Windows."""

    @property
    def name(self) -> str:
        return "dir"


get_registry().register(DirCommand())
