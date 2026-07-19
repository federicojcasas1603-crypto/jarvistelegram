"""
Paquete de comandos de Jarvis Telegram.

Cada archivo en este paquete implementa UNA responsabilidad específica.
El despachador (core/dispatcher.py) usa el registro para encontrar
el comando correcto y ejecutarlo.

Uso:
    from commands import CommandRegistry, get_registry
    registry = get_registry()
    command = registry.get("system_info")
    result = command.execute({})
"""

from commands.base import Command, CommandRegistry, get_registry  # noqa: F401

# Importar todos los módulos de comandos para activar el auto-registro
import commands.system_info  # noqa: F401
import commands.system_resources  # noqa: F401
import commands.windows  # noqa: F401
import commands.browser  # noqa: F401
import commands.clipboard  # noqa: F401
import commands.files  # noqa: F401
import commands.folders  # noqa: F401
import commands.shutdown  # noqa: F401
import commands.screenshots  # noqa: F401
import commands.scripts  # noqa: F401
import commands.documents  # noqa: F401
import commands.downloads  # noqa: F401
import commands.music  # noqa: F401
import commands.memory  # noqa: F401
import commands.navigate  # noqa: F401

__all__ = ["Command", "CommandRegistry", "get_registry"]