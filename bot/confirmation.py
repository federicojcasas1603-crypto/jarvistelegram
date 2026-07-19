"""
Manejo de confirmaciones de acciones destructivas.

Cuando una acción requiere confirmación del usuario, se muestra
un teclado inline con "Confirmar" y "Cancelar". Este módulo
gestiona el flujo completo: crear el teclado, almacenar la acción
pendiente y procesar la respuesta del usuario.

Decisiones de diseño:
    - Se separa de handlers.py porque es un flujo independiente
      con su propio estado (acciones pendientes).
    - Las acciones pendientes se almacenan por message_id para
      que expiren cuando se cierra la conversación.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.formatters import format_action_confirmation, format_error_message, format_response

logger = logging.getLogger(__name__)

# Acciones pendientes de confirmación: message_id → action_dict
_pending_confirmations: dict[int, dict] = {}

# Referencia al processor (se configura desde handlers.configure_handlers)
_message_processor: Any = None
_owner_check: Any = None


def configure_confirmation(
    message_processor: Any,
    owner_check: Any,
) -> None:
    """
    Configura el módulo de confirmaciones.

    Args:
        message_processor: Callback del motor para procesar mensajes.
        owner_check: Callback que verifica si un usuario está autorizado.
    """
    global _message_processor, _owner_check
    _message_processor = message_processor
    _owner_check = owner_check


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Construye el teclado inline de confirmación.

    Returns:
        InlineKeyboardMarkup con botones Confirmar y Cancelar.
    """
    keyboard = [
        [
            InlineKeyboardButton(" Confirmar", callback_data="confirm_yes"),
            InlineKeyboardButton(" Cancelar", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_confirmation_request(
    message: Any,
    action_name: str,
    parameters: dict,
    reason: str,
) -> None:
    """
    Envía una solicitud de confirmación al usuario.

    Muestra los detalles de la acción y un teclado inline
    con las opciones Confirmar y Cancelar.

    Args:
        message: Mensaje de Telegram al que responder.
        action_name: Nombre de la acción a confirmar.
        parameters: Parámetros de la acción.
        reason: Razón de la IA para ejecutar esta acción.
    """
    confirmation_text = format_action_confirmation(action_name, parameters, reason)
    keyboard = build_confirmation_keyboard()

    sent = await message.reply_text(
        confirmation_text,
        reply_markup=keyboard,
    )

    # Almacenar la acción pendiente
    store_pending_confirmation(
        message_id=sent.message_id,
        action_data={
            "action": action_name,
            "parameters": parameters,
            "reason": reason,
        },
    )

    logger.debug(
        "Confirmación enviada. Message ID: %d, Acción: %s",
        sent.message_id,
        action_name,
    )


async def handle_confirmation_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Procesa el callback de confirmación del usuario.

    Flujo:
        1. El usuario presiona "Confirmar" o "Cancelar".
        2. Se busca la acción pendiente por message_id.
        3. Si confirma, se ejecuta la acción a través del motor.
        4. Si cancela, se elimina la acción pendiente.

    Args:
        update: Update de Telegram con el callback.
        context: Contexto de la aplicación.
    """
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    user_id = query.from_user.id

    # Verificar autorización
    if _owner_check and not _owner_check(user_id):
        await query.edit_message_text("Acceso no autorizado.")
        return

    data = query.data
    message_id = query.message.message_id if query.message else None

    if data == "confirm_yes":
        await _handle_confirm_yes(query, message_id)

    elif data == "confirm_no":
        await _handle_confirm_no(query, message_id)


async def _handle_confirm_yes(query: Any, message_id: int | None) -> None:
    """Procesa la confirmación positiva del usuario."""
    if message_id is None:
        await query.edit_message_text("Error interno.")
        return

    pending = _pending_confirmations.get(message_id)

    if not pending or not _message_processor:
        await query.edit_message_text(" La acción ya expiró. Envía el mensaje de nuevo.")
        return

    await query.edit_message_text("⚙️ Ejecutando...")

    try:
        user_id = query.from_user.id
        response_text, file_path = await _message_processor(
            text=None,
            user_id=user_id,
            username=query.from_user.username or "",
            confirmed_action=pending,
        )

        if file_path:
            from bot.formatters import send_file_message
            if query.message:
                await send_file_message(query.message, file_path)
        else:
            formatted = format_response(response_text)
            if query.message:
                await query.message.reply_text(formatted)

    except Exception as e:
        logger.exception("Error al ejecutar acción confirmada")
        if query.message:
            await query.message.reply_text(format_error_message(str(e)))

    _pending_confirmations.pop(message_id, None)


async def _handle_confirm_no(query: Any, message_id: int | None) -> None:
    """Procesa la cancelación del usuario."""
    await query.edit_message_text(" Acción cancelada.")

    if message_id:
        _pending_confirmations.pop(message_id, None)


def store_pending_confirmation(message_id: int, action_data: dict) -> None:
    """
    Almacena una acción pendiente de confirmación.

    Args:
        message_id: ID del mensaje de confirmación en Telegram.
        action_data: Datos de la acción a ejecutar si confirma.
    """
    _pending_confirmations[message_id] = action_data


def get_pending_confirmation(message_id: int) -> dict | None:
    """
    Obtiene una acción pendiente por su message_id.

    Args:
        message_id: ID del mensaje de confirmación.

    Returns:
        Datos de la acción, o None si no existe o expiró.
    """
    return _pending_confirmations.get(message_id)