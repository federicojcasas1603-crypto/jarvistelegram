"""
Motor principal de Jarvis Telegram.

Orquestador central: Telegram Bot → Motor → IA → Despachador → Comando → Respuesta.
El engine es la única clase que conoce a todos los componentes (dependency injection).
El método process_message() es el endpoint que el bot invoca.
Se mantiene un Context por usuario para soportar multi-usuario en el futuro.
"""

from __future__ import annotations

import logging
import platform
from typing import Any

from config.settings import Config
from core.action_validator import ActionValidator
from core.dispatcher import Dispatcher
from core.security import SecurityPolicy
from commands import get_registry
from models.action import Action
from models.command_result import CommandResult
from models.context import Context
from models.message import Message, Role
from providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)


class Engine:
    """
    Motor central de Jarvis Telegram.

    Coordina la comunicación entre el bot de Telegram, la IA,
    el sistema de validación y los comandos ejecutables.

    Example:
        >>> config = load_config()
        >>> engine = Engine(config)
        >>> await engine.initialize()
        >>> response, file = await engine.process_message("Hola", 123, "feder")
    """

    def __init__(self, config: Config) -> None:
        """
        Inicializa el motor con la configuración del sistema.

        Crea instancias de componentes pero NO los inicializa.
        Llama a initialize() después para configurar conexiones.
        """
        self._config = config

        self._security_policy = SecurityPolicy()
        self._validator = ActionValidator(self._security_policy)

        self._registry = get_registry()
        self._dispatcher = Dispatcher(self._registry, self._validator)
        self._ai_provider = GeminiProvider(api_key=config.gemini_api_key, model="flash")
        self._contexts: dict[int, Context] = {}

        self._initialized = False

    async def initialize(self) -> None:
        """Inicializa el motor. Debe llamarse una vez antes de process_message()."""
        if self._initialized:
            return

        logger.info("Inicializando motor de Jarvis...")

        action_info = self._dispatcher.get_command_info()
        await self._ai_provider.initialize(action_descriptions=action_info)

        logger.info(
            "Motor inicializado. Comandos: %d, IA: %s",
            self._registry.count,
            self._ai_provider.model_name,
        )
        self._initialized = True

    async def process_message(
        self,
        text: str | None,
        user_id: int,
        username: str,
        confirmed_action: dict | None = None,
    ) -> tuple[str, str | None]:
        """
        Procesa un mensaje y retorna (respuesta_texto, ruta_archivo_opcional).

        Endpoint principal invocado por los handlers de Telegram.
        Flujo: contexto → IA → validación → ejecución → respuesta.
        """
        if not self._initialized:
            return ("El asistente aún se está iniciando. Por favor espera.", None)

        # Si es una confirmación, ejecutar directamente
        if confirmed_action is not None:
            return await self._execute_confirmed(confirmed_action, user_id, username)

        # Construir o recuperar el contexto del usuario
        context = self._get_or_create_context(user_id, username)

        # Agregar mensaje del usuario al contexto
        user_msg = Message.from_user(text, user_id, username)
        context.add_message(user_msg)

        logger.debug("Procesando mensaje de %s: %s", username, text[:80] if text else "")

        try:
            # Enviar a la IA para que genere una acción
            action = await self._ai_provider.generate_action(context)

            logger.info("IA generó acción: %s", action)

            # Manejar respuesta de texto (la IA decidió no ejecutar acción)
            if action.action == "respond":
                response_text = action.parameters.get("text", "No tengo respuesta.")
                assistant_msg = Message.from_assistant(response_text)
                context.add_message(assistant_msg)
                return (response_text, None)

            # Validar la acción
            validation = self._dispatcher.validate(action)

            if not validation.is_valid:
                error_text = "No puedo ejecutar esa acción:\n" + "\n".join(validation.errors)
                logger.warning("Acción inválida: %s", validation.errors)
                return (error_text, None)

            # Verificar si necesita confirmación
            if validation.requires_confirmation:
                # Retornar un marcador especial que el handler interpreta
                # para mostrar el inline keyboard
                confirm_text = self._build_confirmation_text(action)
                return (f"__CONFIRM__:{confirm_text}:{action.to_dict().__repr__()}", None)

            # Ejecutar la acción directamente
            result = self._dispatcher.execute(action)

            # Agregar respuesta al contexto
            assistant_msg = Message.from_assistant(result.message)
            context.add_message(assistant_msg)

            return (result.message, result.send_file)

        except ConnectionError as e:
            logger.error("Error de conexión con IA para %s: %s", username, e)
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "exceeded" in error_str:
                error_msg = (
                    "❌ La API de Gemini agotó su cuota gratuita.\n"
                    "Opciones:\n"
                    "1. Espera ~1 minuto y vuelve a intentar\n"
                    "2. Obtén una nueva API key en aistudio.google.com\n"
                    "3. Configura una API key con cuota paga en .env"
                )
            else:
                error_msg = (
                    "No pude conectar con la IA. Verifica tu conexión "
                    "a internet y la API key en .env."
                )
            return (error_msg, None)

        except Exception as e:
            logger.exception("Error al procesar mensaje de %s", username)
            error_msg = (
                "Ocurrió un error inesperado al procesar tu mensaje. "
                "Por favor, intenta de nuevo."
            )
            return (error_msg, None)

    async def _execute_confirmed(
        self,
        action_data: dict,
        user_id: int,
        username: str,
    ) -> tuple[str, str | None]:
        """
        Ejecuta una acción que el usuario acaba de confirmar.

        Args:
            action_data: Datos de la acción confirmada.
            user_id: ID del usuario.
            username: Nombre del usuario.

        Returns:
            Tupla (respuesta, archivo_opcional).
        """
        try:
            action = Action.from_dict(action_data)
            result = self._dispatcher.execute(action)

            # Actualizar contexto
            context = self._get_or_create_context(user_id, username)
            assistant_msg = Message.from_assistant(result.message)
            context.add_message(assistant_msg)

            return (result.message, result.send_file)

        except Exception as e:
            logger.exception("Error al ejecutar acción confirmada")
            return ("Error al ejecutar la acción confirmada.", None)

    def _get_or_create_context(self, user_id: int, username: str) -> Context:
        """
        Obtiene o crea el contexto de conversación para un usuario.

        Si el usuario ya tiene un contexto, se reutiliza (mantiene historial).
        Si es nuevo, se crea uno con información del sistema.

        Args:
            user_id: ID de Telegram del usuario.
            username: Nombre de usuario.

        Returns:
            Instancia de Context para este usuario.
        """
        if user_id not in self._contexts:
            context = Context(
                user_id=user_id,
                username=username,
                system_info={
                    "os": platform.system(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                },
            )
            self._contexts[user_id] = context
            logger.debug("Contexto creado para usuario %s (ID: %d)", username, user_id)

        return self._contexts[user_id]

    def _build_confirmation_text(self, action: Action) -> str:
        """
        Construye el texto de solicitud de confirmación.

        Args:
            action: Acción que requiere confirmación.

        Returns:
            Texto formateado con los detalles de la acción.
        """
        lines = [
            f"**Acción:** {action.action}",
        ]

        if action.parameters:
            lines.append("**Parámetros:**")
            for key, value in action.parameters.items():
                lines.append(f"  - {key}: `{value}`")

        if action.reason:
            lines.append(f"\n*Razón: {action.reason}*")

        lines.append("\n¿Ejecuto esta acción?")
        return "\n".join(lines)

    async def shutdown(self) -> None:
        """
        Apaga el motor y libera recursos.

        Se llama al cerrar la aplicación.
        """
        logger.info("Apagando motor de Jarvis...")
        await self._ai_provider.cleanup()
        self._contexts.clear()
        self._initialized = False
        logger.info("Motor apagado correctamente.")

    @property
    def dispatcher(self) -> Dispatcher:
        """Acceso al despachador (para testing y debugging)."""
        return self._dispatcher

    @property
    def ai_provider(self) -> GeminiProvider:
        """Acceso al proveedor de IA (para testing)."""
        return self._ai_provider