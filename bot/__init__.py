"""
Paquete del bot de Telegram.

Gestiona la comunicación con Telegram: recibir mensajes,
enviar respuestas, manejar comandos especiales y archivos.

Uso:
    from bot import JarvisBot
    bot = JarvisBot(token="...")
    await bot.start()
"""

from bot.telegram_bot import JarvisBot

__all__ = ["JarvisBot"]