"""
Comando para tomar capturas de pantalla.

Uso desde Telegram: "Toma una captura de pantalla".
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from PIL import ImageGrab

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "JarvisScreenshots")


class TakeScreenshotCommand(Command):
    """Toma una captura de pantalla y la prepara para enviar."""

    @property
    def name(self) -> str:
        return "take_screenshot"

    @property
    def description(self) -> str:
        return "Toma una captura de pantalla de todo el escritorio"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)

            screenshot = ImageGrab.grab()
            screenshot.save(filepath)

            logger.info("Captura guardada: %s", filepath)
            return CommandResult.ok(
                f"Captura tomada: {filename}",
                send_file=filepath,
            )
        except Exception as e:
            logger.exception("Error al tomar captura")
            return CommandResult.fail(f"Error al tomar captura: {e}")


# Auto-registro
get_registry().register(TakeScreenshotCommand())
