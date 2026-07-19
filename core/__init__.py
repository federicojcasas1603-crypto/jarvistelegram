"""
Paquete core del sistema Jarvis Telegram.

Contiene la lógica central: motor, despachador, seguridad y validación.

Uso:
    from core import Engine, SecurityPolicy, ActionValidator, Dispatcher
"""

from core.action_validator import ActionValidator
from core.security import SecurityPolicy

__all__ = ["SecurityPolicy", "ActionValidator", "Dispatcher"]