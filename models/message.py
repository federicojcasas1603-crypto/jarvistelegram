"""
Modelo de datos para mensajes de la conversación.

Cada interacción entre el usuario y el asistente se modela como un Message.
Estos mensajes alimentan la memoria a corto plazo y se envían a la IA
como contexto de la conversación.

Decisiones de diseño:
    - Se usa un enum Role para distinguir explícitamente entre mensajes
      del usuario y respuestas del asistente. Esto es el estándar que
      usan todas las APIs de IA (OpenAI, Gemini, etc.).
    - El timestamp se genera automáticamente al crear el mensaje.
    - Se incluye user_id para soportar multi-usuario en el futuro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Role(Enum):
    """
    Define los roles posibles en una conversación.

    Attributes:
        USER: Mensaje enviado por el usuario a través de Telegram.
        ASSISTANT: Respuesta generada por el asistente (texto o acción).
        SYSTEM: Mensaje del sistema (errores, notificaciones internas).
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """
    Representa un mensaje en la conversación.

    Attributes:
        role: Quién generó el mensaje (USER, ASSISTANT o SYSTEM).
        content: Texto completo del mensaje.
        user_id: ID de Telegram del usuario. None para mensajes del sistema.
        username: Nombre de usuario de Telegram. None si no está disponible.
        timestamp: Fecha y hora del mensaje en UTC.
    """

    role: Role
    content: str
    user_id: int | None = None
    username: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_user(
        cls,
        content: str,
        user_id: int,
        username: str | None = None,
    ) -> Message:
        """
        Crea un mensaje enviado por el usuario.

        Método de conveniencia que establece el rol automáticamente
        y genera el timestamp actual.

        Args:
            content: Texto del mensaje del usuario.
            user_id: ID de Telegram del usuario.
            username: Nombre de usuario de Telegram (opcional).

        Returns:
            Instancia de Message con rol USER.
        """
        return cls(
            role=Role.USER,
            content=content,
            user_id=user_id,
            username=username,
        )

    @classmethod
    def from_assistant(cls, content: str) -> Message:
        """
        Crea un mensaje generado por el asistente.

        Args:
            content: Texto de la respuesta del asistente.

        Returns:
            Instancia de Message con rol ASSISTANT.
        """
        return cls(
            role=Role.ASSISTANT,
            content=content,
        )

    @classmethod
    def from_system(cls, content: str) -> Message:
        """
        Crea un mensaje del sistema.

        Se usa para errores, notificaciones y eventos internos
        que deben quedar en el historial de la conversación.

        Args:
            content: Texto del mensaje del sistema.

        Returns:
            Instancia de Message con rol SYSTEM.
        """
        return cls(
            role=Role.SYSTEM,
            content=content,
        )

    def to_api_format(self) -> dict[str, str]:
        """
        Convierte el mensaje al formato esperado por las APIs de IA.

        La mayoría de APIs de IA (Gemini, OpenAI) esperan un formato
        como {"role": "user", "content": "texto"}. Este método genera
        ese diccionario.

        Returns:
            Diccionario con 'role' y 'content' como strings.

        Example:
            >>> msg = Message.from_user("Hola", user_id=123)
            >>> msg.to_api_format()
            {"role": "user", "content": "Hola"}
        """
        return {
            "role": self.role.value,
            "content": self.content,
        }

    def to_dict(self) -> dict:
        """
        Serializa el mensaje completo a un diccionario.

        Incluye todos los campos, incluyendo timestamp como ISO format.
        Útil para persistencia y logging.

        Returns:
            Diccionario con todos los campos del mensaje.
        """
        return {
            "role": self.role.value,
            "content": self.content,
            "user_id": self.user_id,
            "username": self.username,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """Representación legible para logs."""
        sender = self.username or self.user_id or self.role.value
        preview = self.content[:80] + "..." if len(self.content) > 80 else self.content
        return f"[{self.role.value}] {sender}: {preview}"