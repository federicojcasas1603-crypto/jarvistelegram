"""
Handler dinámico de comandos slash (/) de Telegram.

Registra automáticamente todos los comandos del CommandRegistry
como comandos de Telegram. Permite ejecutar acciones directamente
sin pasar por la IA.

Formato de uso:
    /system_info
    /open_program notepad
    /search_files "*.py"
    /copy_file origen destino
    /save_memory clave valor
"""

from __future__ import annotations

import logging
import shlex
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from commands.base import Command, CommandRegistry, get_registry
from core.action_schemas import ACTION_SCHEMAS
from core.action_validator import ActionValidator
from core.dispatcher import Dispatcher
from core.security import SecurityPolicy
from models.action import Action
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

# Referencia al dispatcher (se configura desde bot.py)
_dispatcher: Dispatcher | None = None
_is_authorized_fn: Any = None


def init_slash_commands(is_authorized_fn: Any) -> Dispatcher:
    """
    Inicializa el sistema de slash commands.

    Crea el dispatcher con registry, validator y security policy.

    Args:
        is_authorized_fn: Función que verifica si un usuario está autorizado.

    Returns:
        Dispatcher configurado para uso externo.
    """
    global _dispatcher, _is_authorized_fn
    _is_authorized_fn = is_authorized_fn

    registry = get_registry()
    policy = SecurityPolicy()
    validator = ActionValidator(policy)
    _dispatcher = Dispatcher(registry, validator)

    logger.info("Slash commands inicializados. %d comandos disponibles.", registry.count)
    return _dispatcher


def _parse_args(args_text: str, action_name: str) -> dict[str, Any]:
    """
    Parsea los argumentos de texto en un diccionario de parámetros.

    Estrategia:
        1. Si hay un esquema, usar los nombres de parámetros requeridos
           para mapear argumentos posicionales.
        2. Si el usuario usa key=value, parsear directamente.
        3. Para comandos sin parámetros requeridos, retornar dict vacío.

    Args:
        args_text: Texto raw de argumentos del slash command.
        action_name: Nombre de la acción para buscar el esquema.

    Returns:
        Diccionario con parámetros parseados.
    """
    params: dict[str, Any] = {}

    if not args_text or not args_text.strip():
        return params

    # Intentar parsear como key=value primero
    if "=" in args_text:
        try:
            tokens = shlex.split(args_text)
        except ValueError:
            tokens = args_text.split()

        for token in tokens:
            if "=" in token:
                key, _, value = token.partition("=")
                params[key.strip()] = value.strip().strip("\"'")
        return params

    # Parseo posicional según el esquema
    schema = ACTION_SCHEMAS.get(action_name)
    if not schema:
        return params

    try:
        tokens = shlex.split(args_text)
    except ValueError:
        tokens = args_text.split()

    required = schema.get("required", [])
    optional = schema.get("optional", [])

    # Mapear tokens posicionales a parámetros requeridos
    for i, token in enumerate(tokens):
        if i < len(required):
            param_name, param_type = required[i]
            # Si es el último parámetro requerido y es string, unir tokens restantes
            is_last_required = (i == len(required) - 1)
            if is_last_required and param_type is str and len(tokens) > i + 1:
                params[param_name] = " ".join(tokens[i:])
            elif param_type is bool:
                params[param_name] = token.lower() in ("true", "1", "yes", "si", "sí")
            elif param_type is int:
                try:
                    params[param_name] = int(token)
                except ValueError:
                    params[param_name] = token
            else:
                params[param_name] = token
        elif i - len(required) < len(optional):
            opt_name, opt_type = optional[i - len(required)]
            if opt_type is bool:
                params[opt_name] = token.lower() in ("true", "1", "yes", "si", "sí")
            elif opt_type is int:
                try:
                    params[opt_name] = int(token)
                except ValueError:
                    params[opt_name] = token
            else:
                params[opt_name] = token
        else:
            break

    return params


async def _send_confirmation(
    update: Update,
    action: Action,
) -> None:
    """Envía un teclado inline de confirmación para acciones destructivas."""
    from bot.confirmation import store_pending_confirmation, build_confirmation_keyboard
    from bot.formatters import format_action_confirmation

    keyboard = build_confirmation_keyboard()
    confirmation_text = format_action_confirmation(action.action, action.parameters, "Comando directo del usuario")

    sent = await update.message.reply_text(
        confirmation_text,
        reply_markup=keyboard,
    )

    # Almacenar la acción pendiente usando el sistema existente
    store_pending_confirmation(
        message_id=sent.message_id,
        action_data={
            "action": action.action,
            "parameters": action.parameters,
            "reason": "Comando directo del usuario",
        },
    )


async def slash_command_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handler principal para todos los comandos /command de Telegram.

    Parsea el comando y argumentos, construye una Action,
    la valida y la ejecuta directamente (sin IA).
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    bot_command = update.message.text  # e.g. "/open_program notepad"

    if _is_authorized_fn and not _is_authorized_fn(user.id):
        await update.message.reply_text("Acceso no autorizado.")
        return

    if _dispatcher is None:
        await update.message.reply_text("El sistema de comandos no está listo.")
        return

    # Extraer nombre del comando y argumentos
    parts = bot_command.split(None, 1)
    command_name = parts[0].lstrip("/")  # "open_program"
    args_text = parts[1] if len(parts) > 1 else ""

    # Verificar que el comando exista
    if not _dispatcher._registry.has(command_name):
        available = sorted(_dispatcher._registry.get_all().keys())
        await update.message.reply_text(
            f"Comando desconocido: /{command_name}\n"
            f"Usa /help para ver los comandos disponibles."
        )
        return

    # Parsear argumentos
    params = _parse_args(args_text, command_name)

    # Construir Action
    action = Action(action=command_name, parameters=params)

    # Validar
    validation = _dispatcher.validate(action)
    if not validation.is_valid:
        error_text = "❌ Error de validación:\n" + "\n".join(f"• {e}" for e in validation.errors)
        await update.message.reply_text(error_text)
        return

    # Verificar si necesita confirmación
    command = _dispatcher._registry.get(command_name)
    if command and command.requires_confirmation():
        await _send_confirmation(update, action)
        return

    # Ejecutar
    await update.message.chat.send_action("typing")
    # Inyectar user_id para comandos que lo necesiten
    action.parameters["_user_id"] = user.id
    result = _dispatcher.execute(action)

    # Enviar resultado
    if result.send_file:
        from bot.formatters import send_file_message
        await send_file_message(update.message, result.send_file)
        return

    from bot.formatters import format_response
    formatted = format_response(result.message)
    await update.message.reply_text(formatted)


def get_all_command_names() -> list[str]:
    """Retorna todos los nombres de comandos slash disponibles."""
    registry = get_registry()
    return sorted(registry.get_all().keys())
