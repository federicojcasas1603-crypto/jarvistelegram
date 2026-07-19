"""
Paquete de servicios compartidos.

Servicios que pueden ser usados por múltiples módulos del sistema.
Actualmente solo contiene el servicio de Telegram para envío de archivos.

Uso:
    from services import TelegramService
"""

from services.telegram_service import TelegramService

__all__ = ["TelegramService"]