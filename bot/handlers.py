"""
Handlers de mensajes y comandos de Telegram.

Cada handler es una función que recibe un Update de Telegram
y decide qué hacer. Los handlers delegan la lógica de negocio
al motor (engine) a través de un callback configurado dinámicamente.

Decisiones de diseño:
    - Los handlers son funciones async simples, no clases.
      python-telegram-bot usa este patrón como estándar.
    - Se verifica el owner_id en cada mensaje para seguridad.
    - Las confirmaciones se delegan a bot/confirmation.py.
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from bot.formatters import format_error_message, format_response
from bot.confirmation import handle_confirmation_callback, configure_confirmation

logger = logging.getLogger(__name__)

# Referencia al message processor (se configura desde telegram_bot.py)
_message_processor: Any = None
_owner_id: int | None = None


def configure_handlers(message_processor: Any, owner_id: int | None = None) -> None:
    """
    Configura los handlers con el processor y las restricciones.

    Se llama una vez al inicio desde JarvisBot.

    Args:
        message_processor: Callback async para procesar mensajes.
        owner_id: ID del propietario. None = sin restricción.
    """
    global _message_processor, _owner_id
    _message_processor = message_processor
    _owner_id = owner_id
    configure_confirmation(message_processor, _is_authorized)
    logger.debug("Handlers configurados. Owner ID: %s", owner_id or "sin restricción")


def _is_authorized(user_id: int) -> bool:
    """
    Verifica si un usuario tiene permiso para usar el bot.

    Si no hay owner_id configurado, cualquier usuario puede usar el bot.
    Si hay owner_id, solo ese usuario puede interactuar.
    """
    if _owner_id is None:
        return True
    return user_id == _owner_id


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start. Responde con bienvenida."""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    logger.info("Comando /start de %s (ID: %d)", user.username, user.id)

    if not _is_authorized(user.id):
        await update.message.reply_text("Acceso no autorizado. Este bot es privado.")
        return

    welcome = (
        f"¡Hola {user.first_name}! Soy **Jarvis**, tu asistente personal.\n\n"
        "Puedo ayudarte con:\n"
        "- Abrir y cerrar programas\n"
        "- Gestionar archivos y carpetas\n"
        "- Consultar el estado del sistema\n"
        "- Tomar capturas de pantalla\n"
        "- Y mucho más...\n\n"
        "Escríbeme lo que necesitas y haré lo posible por ayudarte.\n\n"
        "Usa /help para ver todos los comandos disponibles."
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /help. Responde con funcionalidades disponibles."""
    if not update.message or not update.effective_user:
        return

    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("Acceso no autorizado.")
        return

    # Construir ayuda dinámica desde el registry
    from commands import get_registry
    registry = get_registry()
    all_commands = sorted(registry.get_all().items())

    # Agrupar por categoría
    categories: dict[str, list[str]] = {
        "Sistema": [],
        "Archivos": [],
        "Programas": [],
        "Utilidades": [],
        "Seguridad": [],
        "Memoria": [],
    }

    cat_map = {
        "system_info": "Sistema",
        "system_resources": "Sistema",
        "shutdown": "Seguridad",
        "restart": "Seguridad",
        "suspend": "Seguridad",
        "open_program": "Programas",
        "close_program": "Programas",
        "open_url": "Programas",
        "search_files": "Archivos",
        "copy_file": "Archivos",
        "move_file": "Archivos",
        "rename_file": "Archivos",
        "delete_file": "Archivos",
        "read_file": "Archivos",
        "send_file": "Archivos",
        "create_folder": "Archivos",
        "organize_downloads": "Archivos",
        "take_screenshot": "Utilidades",
        "clipboard_read": "Utilidades",
        "clipboard_write": "Utilidades",
        "run_script": "Utilidades",
        "execute_python": "Utilidades",
        "summarize_document": "Utilidades",
        "play_music": "Utilidades",
        "stop_music": "Utilidades",
        "pause_music": "Utilidades",
        "save_memory": "Memoria",
        "recall_memory": "Memoria",
        "list_directory": "Archivos",
        "cd": "Archivos",
        "list_programs": "Programas",
    }

    for name, cmd in all_commands:
        cat = cat_map.get(name, "Utilidades")
        categories[cat].append(f"  /{name} — {cmd.description}")

    help_text = "**🤖 Comandos de Jarvis:**\n\n"
    for cat, cmds in categories.items():
        if cmds:
            help_text += f"**{cat}:**\n"
            help_text += "\n".join(cmds) + "\n\n"

    help_text += (
        "**Uso:**\n"
        "- Escribe `/comando` para ejecutar directamente\n"
        "- O escribe en lenguaje natural y la IA decidirá\n\n"
        "**Ejemplos:**\n"
        "- `/system_info` — Ver info del sistema\n"
        "- `/open_program notepad` — Abrir Bloc de notas\n"
        "- `/search_files .py` — Buscar archivos .py\n"
        "- `/save_memory clave valor` — Guardar en memoria"
    )

    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja todos los mensajes de texto del usuario.

    Flujo:
        1. Verificar autorización.
        2. Extraer texto.
        3. Enviar al motor (engine) para que la IA lo procese.
        4. Enviar la respuesta de vuelta al usuario.
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    text = update.message.text

    if not _is_authorized(user.id):
        await update.message.reply_text("Acceso no autorizado.")
        return

    if _message_processor is None:
        await update.message.reply_text(
            "El asistente aún no está listo. Por favor espera un momento."
        )
        return

    logger.info(
        "Mensaje de %s (ID: %d): %s",
        user.username or user.first_name,
        user.id,
        text[:100],
    )

    await update.message.chat.send_action("typing")

    try:
        response_text, file_path = await _message_processor(
            text=text,
            user_id=user.id,
            username=user.username or user.first_name,
        )

        if file_path:
            from bot.formatters import send_file_message
            await send_file_message(update.message, file_path)
            return

        formatted = format_response(response_text)
        await update.message.reply_text(formatted)

    except Exception as e:
        logger.exception("Error al procesar mensaje de %s", user.username)
        await update.message.reply_text(format_error_message(str(e)))