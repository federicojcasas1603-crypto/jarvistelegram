"""
Paquete de comandos de Jarvis Telegram.

Cada archivo en este paquete implementa UNA responsabilidad específica.
El despachador (core/dispatcher.py) usa el registro para encontrar
el comando correcto y ejecutarlo.

Patrón de auto-registro:
    Cada módulo de comandos se auto-registra al final del archivo
    llamando a get_registry().register(). Este __init__.py importa
    todos los módulos para activar ese registro al iniciar la app.

Uso:
    from commands import CommandRegistry, get_registry
    registry = get_registry()
    command = registry.get("system_info")
    result = command.execute({})
"""

from commands.base import Command, CommandRegistry, get_registry

# ============================================
# IMPORTS DE MÓDULOS DE COMANDOS
# ============================================
# Cada import activa el auto-registro de los comandos de ese módulo.
# El orden no importa; todos se registran en el mismo registry.
# Al agregar un nuevo módulo de comandos, agregar su import aquí.
import commands.system_info  # noqa: F401
import commands.system_resources  # noqa: F401

__all__ = ["Command", "CommandRegistry", "get_registry"]
