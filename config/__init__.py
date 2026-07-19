"""
Paquete de configuración centralizada de Jarvis Telegram.

Exposición pública:
    - Config: Dataclass con toda la configuración del sistema.
    - load_config(): Función que carga y valida la configuración desde .env.

Uso:
    from config import load_config
    config = load_config()
"""

from config.settings import Config, load_config

__all__ = ["Config", "load_config"]