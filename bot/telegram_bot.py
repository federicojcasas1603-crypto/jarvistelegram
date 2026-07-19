"""
Configuración y lifecycle del bot de Telegram.

Responsabilidades:
    1. Crear y configurar la instancia de python-telegram-bot.
    2. Registrar los handlers de mensajes y comandos.
    3. Gestionar el ciclo de vida (inicio, apagado, manejo de errores).
    4. Expuesto el contexto de la aplicación para que otros módulos
       puedan enviar mensajes programáticamente.

Decisiones de diseño:
    - Se usa python-telegram-bot v21+ que es 100% async.
    - El bot recibe un callback 'message_processor' que será el motor (engine).
      Esto desacopla el bot de la lógica de negocio.
    - Se usa ApplicationBuilder para una configuración limpia.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.formatters import format_error_message
from bot.handlers import handle_confirmation_callback, handle_message, start_command, help_command

logger = logging.getLogger(__name__)

# Tipo del callback que procesa mensajes (será el motor)
MessageProcessor = Callable[[str, int, str], Awaitable[tuple[str, str | None]]]


class JarvisBot:
    """
    Bot de Telegram principal de Jarvis.

    Maneja la conexión con Telegram, el registro de handlers
    y el envío de mensajes y archivos.

    Attributes:
        _token: Token de autenticación del bot.
        _application: Instancia de la aplicación de python-telegram-bot.
        _owner_id: ID del propietario (para restricción de acceso).
    """

    def __init__(
        self,
        token: str,
        owner_id: int | None = None,
    ) -> None:
        """
        Inicializa el bot.

        Args:
            token: Token de autenticación de Telegram.
            owner_id: ID del propietario. Si se especifica, solo este
                      usuario podrá interactuar con el bot.
        """
        self._token = token
        self._owner_id = owner_id
        self._application: Application | None = None

    @property
    def application(self) -> Application | None:
        """Retorna la instancia de la aplicación de Telegram."""
        return self._application

    @property
    def bot_instance(self):
        """Retorna la instancia del bot de Telegram (para envíos programáticos)."""
        if self._application:
            return self._application.bot
        return None

    async def start(self) -> None:
        """
        Construye y arranca el bot de Telegram.

        Crea la aplicación, registra handlers y comienza el polling
        para recibir mensajes.
        """
        logger.info("Inicializando bot de Telegram...")

        # Construir la aplicación
        self._application = (
            Application.builder()
            .token(self._token)
            .build()
        )

        # Registrar handlers
        self._register_handlers()

        # Iniciar polling
        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling(drop_pending_updates=True)

        bot_info = await self._application.bot.get_me()
        logger.info(
            "Bot de Telegram activo. Nombre: @%s, ID: %d",
            bot_info.username,
            bot_info.id,
        )

    async def stop(self) -> None:
        """Detiene el bot de Telegram de forma segura."""
        if self._application:
            logger.info("Deteniendo bot de Telegram...")
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            logger.info("Bot de Telegram detenido.")

    def set_message_processor(self, processor: MessageProcessor) -> None:
        """
        Configura el callback que procesa mensajes.

        Este callback será invocado por los handlers cada vez que
        el usuario envíe un mensaje. Normalmente será el método
        process_message del engine.

        Args:
            processor: Función async que recibe (texto, user_id, username)
                       y retorna (respuesta_texto, ruta_archivo_opcional).
        """
        self._message_processor = processor
        logger.debug("Message processor configurado.")

    def _register_handlers(self) -> None:
        """Registra todos los handlers en la aplicación."""
        app = self._application

        # Comando /start
        app.add_handler(CommandHandler("start", start_command))

        # Comando /help
        app.add_handler(CommandHandler("help", help_command))

        # Callbacks de confirmación (inline keyboard)
        from telegram.ext import CallbackQueryHandler
        app.add_handler(CallbackQueryHandler(handle_confirmation_callback))

        # Registrar todos los comandos slash dinámicamente desde el registry
        self._register_slash_commands(app)

        # Todos los mensajes de texto → handler principal
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        ))

        # Manejador de errores global
        app.add_error_handler(self._error_handler)

        logger.debug("Handlers registrados correctamente.")

    def _register_slash_commands(self, app: Application) -> None:
        """
        Registra todos los comandos del registry como comandos slash de Telegram.

        Cada comando se registra como /command_name y se maneja
        con el slash_command_handler que ejecuta directamente.
        """
        from bot.slash_commands import slash_command_handler, init_slash_commands

        # Inicializar slash commands con la función de autorización
        from bot.handlers import _is_authorized
        init_slash_commands(_is_authorized)

        # Obtener todos los comandos del registry
        from commands import get_registry
        registry = get_registry()

        for command_name in registry.get_all():
            # Registrar como CommandHandler de Telegram
            app.add_handler(CommandHandler(command_name, slash_command_handler))

        logger.info(
            "Slash commands registrados: %d comandos",
            registry.count,
        )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Manejador de errores global de la aplicación.

        Captura errores no manejados en otros handlers para que
        el bot no se caiga. Registra el error en logs y, si es posible,
        notifica al usuario.

        Args:
            update: El update que causó el error (puede ser None).
            context: Contexto del error de la aplicación.
        """
        logger.exception(
            "Error no manejado en la aplicación de Telegram: %s",
            context.error,
        )

        # Intentar notificar al usuario si hay un update válido
        if update and hasattr(update, "message") and update.message:
            try:
                error_text = format_error_message(str(context.error))
                await update.message.reply_text(error_text)
            except Exception:
                logger.exception("No se pudo notificar el error al usuario.")