"""
Servicio de envío de archivos por Telegram.

Responsabilidades:
    1. Enviar documentos (archivos de cualquier tipo).
    2. Enviar fotos (capturas de pantalla, imágenes).
    3. Enviar mensajes de texto largos (divididos si es necesario).
    4. Verificar límites de Telegram antes de enviar.

Decisiones de diseño:
    - Se mantiene separado de los handlers para que cualquier módulo
      pueda enviar archivos sin importar directamente telegram.
    - Se usa una referencia al bot de Telegram que se inyecta al iniciar.
    - Se validan tamaños y formatos antes de intentar el envío.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Límites de Telegram
MAX_DOCUMENT_SIZE_MB = 50
MAX_PHOTO_SIZE_MB = 10
MAX_MESSAGE_LENGTH = 4096


class TelegramService:
    """
    Servicio para enviar contenido a través de Telegram.

    Proporciona métodos de alto nivel para enviar archivos, fotos
    y mensajes sin preocuparse por los detalles de la API de Telegram.

    Attributes:
        _bot: Instancia del bot de Telegram (se configura después del init).
    """

    def __init__(self) -> None:
        """Inicializa el servicio sin bot configurado."""
        self._bot: Any = None
        self._chat_id: int | None = None

    def configure(self, bot: Any, chat_id: int | None = None) -> None:
        """
        Configura el servicio con la instancia del bot.

        Args:
            bot: Instancia de telegram.Bot.
            chat_id: ID del chat por defecto para envíos programáticos.
        """
        self._bot = bot
        self._chat_id = chat_id
        logger.debug("TelegramService configurado.")

    async def send_document(
        self,
        file_path: str,
        caption: str | None = None,
        chat_id: int | None = None,
    ) -> bool:
        """
        Envía un documento por Telegram.

        Args:
            file_path: Ruta absoluta del archivo a enviar.
            caption: Texto opcional como pie de foto del documento.
            chat_id: ID del chat destino. Si es None, usa el configurado.

        Returns:
            True si se envió correctamente, False en caso contrario.
        """
        if not self._bot:
            logger.error("TelegramService no está configurado.")
            return False

        target_chat = chat_id or self._chat_id
        if target_chat is None:
            logger.error("No hay chat_id configurado para enviar documentos.")
            return False

        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            logger.error("Archivo no encontrado: %s", file_path)
            return False

        # Verificar tamaño
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > MAX_DOCUMENT_SIZE_MB:
            logger.warning(
                "Archivo demasiado grande (%.1f MB, límite %d MB): %s",
                size_mb, MAX_DOCUMENT_SIZE_MB, file_path,
            )
            return False

        try:
            file_name = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                await self._bot.send_document(
                    chat_id=target_chat,
                    document=f,
                    filename=file_name,
                    caption=caption or f"📄 {file_name}",
                )

            logger.info("Documento enviado: %s (%.1f MB)", file_name, size_mb)
            return True

        except Exception as e:
            logger.exception("Error al enviar documento: %s", e)
            return False

    async def send_photo(
        self,
        file_path: str,
        caption: str | None = None,
        chat_id: int | None = None,
    ) -> bool:
        """
        Envía una foto por Telegram.

        Args:
            file_path: Ruta de la imagen a enviar.
            caption: Texto opcional como pie de foto.
            chat_id: ID del chat destino.

        Returns:
            True si se envió correctamente.
        """
        if not self._bot:
            logger.error("TelegramService no está configurado.")
            return False

        target_chat = chat_id or self._chat_id
        if target_chat is None:
            return False

        if not os.path.exists(file_path):
            logger.error("Foto no encontrada: %s", file_path)
            return False

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > MAX_PHOTO_SIZE_MB:
            logger.warning("Foto demasiado grande (%.1f MB): %s", size_mb, file_path)
            return False

        try:
            with open(file_path, "rb") as f:
                await self._bot.send_photo(
                    chat_id=target_chat,
                    photo=f,
                    caption=caption,
                )

            logger.info("Foto enviada: %s", file_path)
            return True

        except Exception as e:
            logger.exception("Error al enviar foto: %s", e)
            return False

    async def send_message(
        self,
        text: str,
        chat_id: int | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        """
        Envía un mensaje de texto, dividiéndolo si excede el límite.

        Args:
            text: Texto del mensaje.
            chat_id: ID del chat destino.
            parse_mode: Modo de parseo ("Markdown", "HTML", None).

        Returns:
            True si se envió correctamente.
        """
        if not self._bot:
            return False

        target_chat = chat_id or self._chat_id
        if target_chat is None:
            return False

        try:
            # Dividir mensajes muy largos
            chunks = self._split_message(text)

            for chunk in chunks:
                await self._bot.send_message(
                    chat_id=target_chat,
                    text=chunk,
                    parse_mode=parse_mode,
                )

            return True

        except Exception as e:
            logger.exception("Error al enviar mensaje: %s", e)
            return False

    @staticmethod
    def _split_message(text: str) -> list[str]:
        """
        Divide un mensaje largo en partes que respeten el límite de Telegram.

        Corta por líneas para no romper palabras.

        Args:
            text: Texto a dividir.

        Returns:
            Lista de strings, cada uno dentro del límite.
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        current = ""

        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH - 50:
                chunks.append(current.strip())
                current = line
            else:
                current += "\n" + line

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text[:MAX_MESSAGE_LENGTH]]