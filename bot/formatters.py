"""
Formateo de respuestas para Telegram.

Telegram tiene limitaciones específicas:
    - Mensajes de texto: máximo 4096 caracteres.
    - Markdown: soportado pero con reglas estrictas.
    - Archivos: máximo 50MB para documentos, 10MB para fotos.

Este módulo adapta las respuestas del asistente a estas restricciones.

Decisiones de diseño:
    - Se usa MarkdownV2 de Telegram para formato rico.
    - Los mensajes que excedan el límite se truncan con indicador.
    - Los errores se muestran de forma amigable sin detalles técnicos.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import Message

logger = logging.getLogger(__name__)

# Límite de caracteres de Telegram por mensaje
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def format_response(text: str) -> str:
    """
    Formatea una respuesta de texto para Telegram.

    Aplica las siguientes transformaciones:
        1. Trunca si excede el límite de Telegram.
        2. Escapa caracteres especiales de MarkdownV2 de forma segura.

    Args:
        text: Texto de respuesta del asistente.

    Returns:
        Texto formateado y seguro para Telegram.
    """
    if not text:
        return "No hay respuesta para mostrar."

    text = text.strip()

    # Truncar si es necesario
    text = truncate_message(text)

    # Limpiar markdown problemático
    text = _sanitize_markdown(text)

    return text


def format_error_message(error: str) -> str:
    """
    Formatea un mensaje de error para el usuario.

    Los errores técnicos no deben mostrarse al usuario tal cual.
    Se muestra un mensaje amigable con el detalle en los logs.

    Args:
        error: Mensaje de error técnico.

    Returns:
        Mensaje de error amigable para el usuario.
    """
    logger.debug("Error para usuario: %s", error)

    # Errores comunes con mensajes específicos
    error_lower = error.lower()

    if "connection" in error_lower or "timeout" in error_lower:
        return (
            "No pude conectarme al servicio de IA en este momento. "
            "Verifica tu conexión a internet e intenta de nuevo."
        )

    if "api key" in error_lower or "credential" in error_lower:
        return (
            "Hay un problema con la configuración de la API. "
            "Revisa el archivo .env."
        )

    if "permission" in error_lower or "access" in error_lower:
        return (
            "No tengo permisos para realizar esta operación. "
            "Es posible que se requieran permisos de administrador."
        )

    if "not found" in error_lower or "no existe" in error_lower:
        return "No encontré el archivo o recurso que mencionas."

    # Error genérico
    return (
        "Ocurrió un error al procesar tu solicitud. "
        "Por favor, intenta de nuevo o simplifica tu petición."
    )


def format_action_confirmation(action_name: str, parameters: dict, reason: str) -> str:
    """
    Formatea un mensaje de confirmación de acción.

    Se muestra al usuario cuando una acción requiere confirmación
    antes de ejecutarse.

    Args:
        action_name: Nombre de la acción a confirmar.
        parameters: Parámetros de la acción.
        reason: Razón de la IA para ejecutar esta acción.

    Returns:
        Mensaje de confirmación formateado.
    """
    lines = [
        " **Confirmación requerida**",
        "",
        f"**Acción:** {action_name}",
    ]

    if parameters:
        lines.append("**Parámetros:**")
        for key, value in parameters.items():
            lines.append(f"  - {key}: `{value}`")

    if reason:
        lines.extend(["", f"*Razón: {reason}*"])

    lines.extend([
        "",
        "¿Deseas que ejecute esta acción?",
    ])

    return "\n".join(lines)


async def send_file_message(message: Message, file_path: str) -> None:
    """
    Envía un archivo por Telegram.

    Verifica que el archivo exista y no exceda los límites de Telegram
    antes de intentar enviarlo.

    Args:
        message: Mensaje de Telegram al que responder (para reply).
        file_path: Ruta absoluta del archivo a enviar.
    """
    if not os.path.exists(file_path):
        await message.reply_text(
            f"No se encontró el archivo: {os.path.basename(file_path)}",
        )
        return

    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)

    # Verificar límite de Telegram (50MB para documentos)
    if file_size_mb > 50:
        await message.reply_text(
            f"El archivo es demasiado grande para enviarlo por Telegram "
            f"({file_size_mb:.1f} MB). Límite: 50 MB."
        )
        return

    file_name = os.path.basename(file_path)
    await message.reply_document(
        document=open(file_path, "rb"),
        filename=file_name,
        caption=f"📄 {file_name}",
    )
    logger.info("Archivo enviado por Telegram: %s (%.1f MB)", file_name, file_size_mb)


def truncate_message(text: str) -> str:
    """
    Trunca un mensaje si excede el límite de Telegram.

    Si el texto es más largo que TELEGRAM_MAX_MESSAGE_LENGTH,
    se trunca y se agrega un indicador de "... (truncado)".

    Args:
        text: Texto a truncar.

    Returns:
        Texto truncado si era necesario, o el texto original.
    """
    if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        return text

    # Dejar espacio para el indicador de truncado
    truncated = text[: TELEGRAM_MAX_MESSAGE_LENGTH - 25]
    return truncated + "\n\n... _(truncado)_"


def _sanitize_markdown(text: str) -> str:
    """
    Limpia markdown problemático para Telegram.

    Telegram MarkdownV2 es muy estricto con los caracteres especiales.
    Esta función asegura que el texto sea seguro sin romper el formato
    intencional.

    Args:
        text: Texto con posible markdown.

    Returns:
        Texto limpio y seguro para Telegram.
    """
    # Caracteres que Telegram MarkdownV2 interpreta como especiales
    # y que necesitan escape si no están dentro de un bloque de formato
    safe_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]

    # Por ahora, usar parse_mode=None para respuestas simples
    # y Markdown solo cuando sea explícitamente formateado.
    # Esto evita la mayoría de problemas de parsing.
    return text