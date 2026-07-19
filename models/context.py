"""
Modelo de datos para el contexto de conversación.

El contexto es el paquete completo de información que se envía a la IA
para que pueda tomar decisiones informadas. Incluye:
    - Historial de mensajes recientes (memoria a corto plazo).
    - Datos del usuario (memoria a largo plazo).
    - Información del sistema actual.

Decisiones de diseño:
    - Se mantiene separado de la IA para que cualquier proveedor
      (Gemini, OpenAI, Ollama) pueda recibir el mismo contexto.
    - El contexto se construye en el motor (engine) y se consume
      en el proveedor de IA. Esto mantiene la separación de responsabilidades.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.message import Message


@dataclass
class Context:
    """
    Contexto completo de la conversación actual.

    Se construye antes de cada llamada a la IA y contiene toda la
    información que el modelo necesita para generar una respuesta adecuada.

    Attributes:
        messages: Lista ordenada de mensajes de la conversación actual.
                  El primer mensaje es el más antiguo, el último es el más reciente.
        user_id: ID de Telegram del usuario que está interactuando.
        username: Nombre de usuario de Telegram.
        user_preferences: Diccionario con las preferencias almacenadas del usuario.
                         Se carga desde la memoria a largo plazo.
        system_info: Información relevante del sistema actual.
                    Ejemplo: {"os": "windows", "cwd": "C:\\Users\\..."}.
        active_command: Nombre del comando que se está ejecutando, si aplica.
                       Se usa para mantener contexto durante flujos multi-paso.
    """

    messages: list[Message] = field(default_factory=list)
    user_id: int = 0
    username: str = ""
    user_preferences: dict = field(default_factory=dict)
    system_info: dict = field(default_factory=dict)
    active_command: str | None = None

    def add_message(self, message: Message) -> None:
        """
        Agrega un mensaje al contexto.

        Args:
            message: Instancia de Message a agregar al historial.
        """
        self.messages.append(message)

    def get_recent_messages(self, count: int = 20) -> list[Message]:
        """
        Retorna los últimos N mensajes del contexto.

        Se usa para limitar la cantidad de contexto enviado a la IA
        y controlar el consumo de tokens.

        Args:
            count: Número máximo de mensajes a retornar.

        Returns:
            Lista con los últimos 'count' mensajes. Si hay menos mensajes
            que el límite, retorna todos los disponibles.
        """
        if count <= 0:
            return []
        return self.messages[-count:]

    def get_messages_for_api(self, count: int = 20) -> list[dict[str, str]]:
        """
        Retorna los mensajes en el formato esperado por las APIs de IA.

        Combina get_recent_messages() con la serialización de cada
        mensaje al formato de diccionario que las APIs de IA esperan.

        Args:
            count: Número máximo de mensajes a incluir.

        Returns:
            Lista de diccionarios con 'role' y 'content'.
        """
        recent = self.get_recent_messages(count)
        return [msg.to_api_format() for msg in recent]

    def clear(self) -> None:
        """
        Limpia el historial de mensajes del contexto.

        Se usa al iniciar una nueva conversación o cuando el usuario
        pide explícitamente "empezar de nuevo".
        """
        self.messages.clear()
        self.active_command = None

    @property
    def message_count(self) -> int:
        """Número total de mensajes en el contexto actual."""
        return len(self.messages)

    def __str__(self) -> str:
        """Representación legible para debugging."""
        user = self.username or self.user_id or "desconocido"
        return (
            f"Context(user={user}, "
            f"messages={self.message_count}, "
            f"preferences={len(self.user_preferences)} keys)"
        )