"""
Comandos para controlar música en Windows.

Uso desde Telegram: "Pon música", "Pausa la música", "Detén la música".
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class PlayMusicCommand(Command):
    """Reproduce música usando el reproductor predeterminado de Windows."""

    @property
    def name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return "Reproduce música o busca una canción"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        query = params.get("query", "").strip()

        try:
            # Usar el protocolo ms-windows-store para abrir Spotify o el reproductor
            if query:
                # Abrir navegador con búsqueda de YouTube Music
                import webbrowser
                url = f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
                webbrowser.open(url)
                logger.info("Buscando música en YouTube Music: %s", query)
                return CommandResult.ok(f"Buscando '{query}' en YouTube Music.")
            else:
                # Simular play con tecla multimedia
                import ctypes
                ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)  # MEDIA_PLAY_PAUSE
                logger.info("Reproducción de música iniciada")
                return CommandResult.ok("Reproducción de música activada.")

        except Exception as e:
            logger.exception("Error al reproducir música")
            return CommandResult.fail(f"Error al reproducir música: {e}")


class StopMusicCommand(Command):
    """Detiene la música."""

    @property
    def name(self) -> str:
        return "stop_music"

    @property
    def description(self) -> str:
        return "Detiene la reproducción de música"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            import ctypes
            # MEDIA_STOP = 0xB2
            ctypes.windll.user32.keybd_event(0xB2, 0, 0, 0)
            logger.info("Música detenida")
            return CommandResult.ok("Música detenida.")
        except Exception as e:
            logger.exception("Error al detener música")
            return CommandResult.fail(f"Error al detener la música: {e}")


class PauseMusicCommand(Command):
    """Pausa la música."""

    @property
    def name(self) -> str:
        return "pause_music"

    @property
    def description(self) -> str:
        return "Pausa la reproducción de música"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        try:
            import ctypes
            # MEDIA_PLAY_PAUSE = 0xB3
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            logger.info("Música pausada")
            return CommandResult.ok("Música pausada/reanudada.")
        except Exception as e:
            logger.exception("Error al pausar música")
            return CommandResult.fail(f"Error al pausar la música: {e}")


# Auto-registro
get_registry().register(PlayMusicCommand())
get_registry().register(StopMusicCommand())
get_registry().register(PauseMusicCommand())
