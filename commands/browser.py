"""
Comando para abrir URLs en el navegador predeterminado.

Uso desde Telegram: "Abre google.com", "Busca en YouTube recetas de pasta".
"""

from __future__ import annotations

import logging
import webbrowser
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class OpenURLCommand(Command):
    """Comando que abre una URL en el navegador."""

    @property
    def name(self) -> str:
        return "open_url"

    @property
    def description(self) -> str:
        return "Abre una URL o página web en el navegador"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        url = params.get("url", "").strip()

        if not url:
            return CommandResult.fail("No se especificó una URL.")

        # Agregar protocolo si falta
        if not url.startswith(("http://", "https://", "www.")):
            if "." in url:
                url = f"https://{url}"
            else:
                # Podría ser una búsqueda, usar Google
                url = f"https://www.google.com/search?q={url.replace(' ', '+')}"

        try:
            webbrowser.open(url)
            logger.info("URL abierta: %s", url)
            return CommandResult.ok(f"Página abierta: {url}")
        except Exception as e:
            logger.exception("Error al abrir URL %s", url)
            return CommandResult.fail(f"Error al abrir la página: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        url = params.get("url")
        if not url or not str(url).strip():
            errors.append("El parámetro 'url' es obligatorio.")
        return errors


# Auto-registro
get_registry().register(OpenURLCommand())
