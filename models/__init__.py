"""
Paquete de modelos de datos de Jarvis Telegram.

Todos los módulos del proyecto importan sus modelos desde aquí.
Esto garantiza una única fuente de verdad para las estructuras de datos.

Uso:
    from models import Action, Message, Context, CommandResult
"""

from models.action import Action
from models.command_result import CommandResult
from models.context import Context
from models.message import Message

__all__ = ["Action", "Message", "Context", "CommandResult"]