"""
Implementación del proveedor de IA usando Google Gemini.

Google Gemini ofrece una API gratuita con generación de texto
y soporte para system instructions. Es la IA principal del proyecto.

Cómo funciona:
    1. Se configura la API key de Gemini.
    2. Se crea un modelo con el system prompt (que incluye las acciones disponibles).
    3. Para cada mensaje, se envía el historial de la conversación.
    4. La IA responde con un JSON que se parsea en una Action.

Decisiones de diseño:
    - Se usa el modo chat de Gemini para mantener contexto entre mensajes.
    - El system prompt se genera dinámicamente con la lista de acciones reales.
    - Se implementa retry con backoff exponencial para errores transitorios.
    - Se extrae JSON de la respuesta aunque venga envuelto en markdown (```json).
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import google.generativeai as genai

from models.action import Action
from models.context import Context
from prompts.system_prompt import build_system_prompt
from providers.base import AIProvider

logger = logging.getLogger(__name__)

# Modelos de Gemini soportados (ordenados por capacidad, de menor a mayor)
SUPPORTED_MODELS = {
    "flash": "gemini-2.0-flash",
    "flash-lite": "gemini-2.0-flash-lite",
    "pro": "gemini-2.5-pro",
}

# Número máximo de reintentos para errores transitorios
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # segundos


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """
    Extrae un objeto JSON de un texto que puede contener otros elementos.

    La IA a veces envuelve el JSON en bloques de código markdown:
        ```json
        {"action": "open_program", ...}
        ```

    Esta función maneja ambos casos: JSON puro y JSON en markdown.

    Args:
        text: Texto de respuesta de la IA.

    Returns:
        Diccionario parseado, o None si no se encontró JSON válido.
    """
    text = text.strip()

    # Caso 1: El texto es JSON puro
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Caso 2: JSON envuelto en bloque markdown ```json ... ```
    markdown_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(markdown_pattern, text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Caso 3: Buscar el primer { ... } en el texto
    brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    match = re.search(brace_pattern, text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


class GeminiProvider(AIProvider):
    """
    Proveedor de IA basado en Google Gemini.

    Utiliza la librería google-generativeai para interactuar con
    la API de Gemini. Soporta modo chat con historial y system instructions.

    Attributes:
        _api_key: Clave de API de Google AI Studio.
        _model_id: Identificador del modelo Gemini a usar.
        _model: Instancia del modelo generativo configurado.
    """

    def __init__(self, api_key: str, model: str = "flash") -> None:
        """
        Inicializa el proveedor Gemini.

        Args:
            api_key: Clave de API de Google AI Studio.
            model: Nombre corto del modelo. Valores válidos:
                   "flash" (default, rápido y gratuito),
                   "flash-lite" (más rápido, menos capaz),
                   "pro" (más capaz, puede tener costo).
        """
        self._api_key = api_key
        self._model_id = SUPPORTED_MODELS.get(model, f"gemini-{model}")
        self._model = None
        self._action_descriptions: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_id

    async def initialize(self, action_descriptions: list[dict[str, str]] | None = None) -> None:
        """
        Configura la conexión con la API de Gemini.

        Args:
            action_descriptions: Lista de comandos disponibles con sus
                                descripciones. Se usa para generar el
                                system prompt dinámicamente.

        Raises:
            ValueError: Si la API key es inválida.
        """
        if not self._api_key or self._api_key.strip() == "":
            raise ValueError("La API key de Gemini no puede estar vacía.")

        # Configurar la API
        genai.configure(api_key=self._api_key)

        # Guardar descripciones de acciones para el system prompt
        self._action_descriptions = action_descriptions or []

        # Construir el system prompt
        system_text = build_system_prompt(self._action_descriptions)

        # Crear el modelo con system instruction
        generation_config = genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
            top_p=0.95,
        )

        self._model = genai.GenerativeModel(
            model_name=self._model_id,
            system_instruction=system_text,
            generation_config=generation_config,
        )

        logger.info(
            "Proveedor Gemini inicializado. Modelo: %s, Acciones: %d",
            self._model_id,
            len(self._action_descriptions),
        )

    async def generate_action(self, context: Context) -> Action:
        """
        Genera una acción estructurada a partir del contexto.

        Envía el historial de conversación a Gemini y parsea la respuesta
        en una Action. Si la IA responde con texto libre en lugar de JSON,
        se retorna una Action de tipo "respond" con el texto.

        Args:
            context: Contexto completo de la conversación.

        Returns:
            Action con la decisión de la IA.

        Raises:
            ConnectionError: Si hay problemas de conexión con la API.
            ValueError: Si la respuesta de la IA no puede interpretarse.
        """
        if self._model is None:
            raise ConnectionError(
                "El modelo Gemini no está inicializado. "
                "Llama a initialize() primero."
            )

        # Construir el historial para el chat
        history = self._build_chat_history(context)

        # Obtener el último mensaje (el que procesamos)
        if not context.messages:
            raise ValueError("El contexto no contiene mensajes para procesar.")

        last_message = context.messages[-1]
        user_input = last_message.content

        logger.debug("Enviando a Gemini (%d mensajes en historial)", len(history))

        # Llamar a la API con reintentos
        response_text = await self._generate_with_retry(history, user_input)

        logger.debug("Respuesta de Gemini: %s", response_text[:200])

        # Parsear la respuesta en una Action
        action = self._parse_response(response_text)

        return action

    async def generate_response(self, context: Context) -> str:
        """
        Genera una respuesta de texto libre.

        Misma lógica que generate_action(), pero retorna el texto
        raw de la IA sin parsear a Action.

        Args:
            context: Contexto completo de la conversación.

        Returns:
            String con la respuesta de texto.
        """
        if self._model is None:
            raise ConnectionError("El modelo Gemini no está inicializado.")

        history = self._build_chat_history(context)

        if not context.messages:
            return "No hay mensajes para procesar."

        last_message = context.messages[-1]
        user_input = last_message.content

        return await self._generate_with_retry(history, user_input)

    def _build_chat_history(self, context: Context) -> list[dict[str, str]]:
        """
        Convierte el historial de Message al formato que Gemini espera.

        Excluye el último mensaje (que se envía como user_input separado)
        porque el chat de Gemini maneja eso de forma diferente.

        Args:
            context: Contexto de la conversación.

        Returns:
            Lista de diccionarios con 'role' y 'parts'.
        """
        messages = context.get_recent_messages(count=context.max_messages if hasattr(context, 'max_messages') else 50)

        # Excluir el último mensaje (se envía aparte)
        if len(messages) > 1:
            history_messages = messages[:-1]
        else:
            history_messages = []

        history = []
        for msg in history_messages:
            # Mapear roles: system → user para Gemini
            role = msg.role.value
            if role == "system":
                role = "user"

            history.append({
                "role": role,
                "parts": [msg.content],
            })

        return history

    async def _generate_with_retry(
        self,
        history: list[dict[str, str]],
        user_input: str,
    ) -> str:
        """
        Genera contenido con reintentos para errores transitorios.

        Implementa backoff exponencial: 1s, 2s, 4s entre reintentos.

        Args:
            history: Historial de conversación previo.
            user_input: Mensaje del usuario a procesar.

        Returns:
            Texto de respuesta de la IA.

        Raises:
            ConnectionError: Si todos los reintentos fallan.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                # Crear chat con historial
                chat = self._model.start_chat(history=history)

                # Enviar mensaje
                response = await chat.send_message_async(user_input)

                if response.text:
                    return response.text.strip()

                # Si no hay texto, la IA pudo haber bloqueado la respuesta
                logger.warning("Gemini retornó respuesta vacía (intento %d)", attempt + 1)
                return "No pude generar una respuesta. Intenta de nuevo."

            except Exception as e:
                last_error = e
                logger.warning(
                    "Error en llamada a Gemini (intento %d/%d): %s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    type(e).__name__,
                    e,
                )

                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info("Reintentando en %.1f segundos...", delay)
                    import asyncio
                    await asyncio.sleep(delay)

        # Todos los reintentos fallaron
        raise ConnectionError(
            f"No se pudo conectar con Gemini después de {MAX_RETRIES} intentos. "
            f"Último error: {type(last_error).__name__}: {last_error}"
        )

    def _parse_response(self, response_text: str) -> Action:
        """
        Parsea la respuesta de la IA en una Action.

        Intenta extraer JSON de la respuesta. Si la IA respondió con
        texto libre (sin JSON), se crea una Action de tipo "respond"
        con el texto para que el motor lo envíe como mensaje al usuario.

        Args:
            response_text: Texto crudo de la respuesta de la IA.

        Returns:
            Action parseada o Action de tipo "respond" con el texto.
        """
        parsed = _extract_json_from_text(response_text)

        if parsed is not None:
            try:
                return Action.from_dict(parsed)
            except ValueError as e:
                logger.warning(
                    "JSON extraído no es una Action válida: %s. "
                    "Convirtiendo a respuesta de texto.",
                    e,
                )

        # La IA respondió con texto libre → crear Action de tipo "respond"
        return Action(
            action="respond",
            parameters={"text": response_text},
            reason="La IA decidió responder con texto en lugar de ejecutar una acción.",
        )