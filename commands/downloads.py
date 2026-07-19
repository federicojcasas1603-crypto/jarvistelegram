"""
Comando para organizar archivos de la carpeta de Descargas.

Uso desde Telegram: "Organiza mis descargas".
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

# Categorías de archivos por extensión
CATEGORIES: dict[str, list[str]] = {
    "Imágenes": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "Documentos": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "Música": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archivos comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Ejecutables": [".exe", ".msi", ".bat", ".cmd"],
    "Código": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h"],
}


def _get_category(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Otros"


class OrganizeDownloadsCommand(Command):
    """Organiza archivos de Descargas en carpetas por categoría."""

    @property
    def name(self) -> str:
        return "organize_downloads"

    @property
    def description(self) -> str:
        return "Organiza los archivos de la carpeta de Descargas por categoría"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        directory = params.get("directory") or os.path.join(os.path.expanduser("~"), "Downloads")

        if not os.path.isdir(directory):
            return CommandResult.fail(f"Carpeta no encontrada: {directory}")

        try:
            moved = 0
            skipped = 0
            categories_used: dict[str, int] = {}

            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)

                # Saltar carpetas y archivos ocultos
                if os.path.isdir(item_path) or item.startswith("."):
                    skipped += 1
                    continue

                category = _get_category(item)
                target_dir = os.path.join(directory, category)
                os.makedirs(target_dir, exist_ok=True)

                target_path = os.path.join(target_dir, item)
                if os.path.exists(target_path):
                    skipped += 1
                    continue

                shutil.move(item_path, target_path)
                moved += 1
                categories_used[category] = categories_used.get(category, 0) + 1

            if moved == 0:
                return CommandResult.ok("No hay archivos nuevos para organizar.")

            summary = f"Archivos organizados: {moved}\n"
            for cat, count in sorted(categories_used.items()):
                summary += f"  {cat}: {count}\n"
            if skipped:
                summary += f"\nSaltados (carpetas/existentes): {skipped}"

            logger.info("Descargas organizadas: %d archivos movidos", moved)
            return CommandResult.ok(summary)

        except Exception as e:
            logger.exception("Error al organizar descargas")
            return CommandResult.fail(f"Error al organizar: {e}")


# Auto-registro
get_registry().register(OrganizeDownloadsCommand())
