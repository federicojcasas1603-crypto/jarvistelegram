"""
Interfaz abstracta para proveedores de inteligencia artificial.

Cualquier proveedor (Gemini, OpenAI, Ollama, etc.) debe heredar
de AIProvider e implementar generate_action() y generate_response().

Decisiones de diseño:
    - Se usa ABC para forzar que todas las implementaciones tengan
      la misma interfaz. Esto garantiza que cambiar de proveedor
      solo requiera cambiar la clase instanciada.
    - Los métodos son async porque las llamadas a APIs de IA son
      I/O-bound y no deben bloquear el event loop de asyncio.
    - Se incluye cleanup() para liberar conexiones al cerrar la app.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from models.action import Action
from models.context import Context

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Interfaz abstracta para proveedores de IA.

    Cada proveedor concreto debe implementar:
        - generate_action(): Genera una acción estructurada a partir del contexto.
        - generate_response(): Genera una respuesta de texto libre.
        - initialize(): Configura la conexión con el proveedor.

    Example:
        >>> class MyProvider(AIProvider):
        ...     async def initialize(self) -> None:
        ...         # configurar cliente API
        ...     async def generate_action(self, context: Context) -> Action:
        ...         # llamar a la API y retornar Action
        ...     async def generate_response(self, context: Context) -> str:
        ...         # llamar a la API y retornar texto
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor (para logs y debugging)."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo específico que se está usando."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """
        Inicializa la conexión con el proveedor de IA.

        Se ejecuta una vez al inicio de la aplicación.
        Debe configurar credenciales, crear clientes, verificar conectividad.

        Raises:
            ConnectionError: Si no se puede conectar al proveedor.
            ValueError: Si las credenciales son inválidas.
        """
        ...

    @abstractmethod
    async def generate_action(self, context: Context) -> Action:
        """
        Genera una acción estructurada a partir del contexto de conversación.

        Este es el método principal del sistema. Recibe el contexto completo
        (historial de mensajes, preferencias del usuario, info del sistema)
        y debe retornar una Action con el JSON que la IA decidió ejecutar.

        Si la IA decide solo responder con texto (sin acción), debe retornar
        una Action especial con action="respond" y el texto en parameters["text"].

        Args:
            context: Contexto completo de la conversación.

        Returns:
            Action con la decisión de la IA.

        Raises:
            ConnectionError: Si hay problemas de conexión con la API.
            ValueError: Si la IA retorna un JSON inválido.
        """
        ...

    @abstractmethod
    async def generate_response(self, context: Context) -> str:
        """
        Genera una respuesta de texto libre (sin acción estructurada).

        Se usa para interacciones conversacionales donde la IA solo
        responde con texto y no necesita ejecutar ninguna acción.

        Args:
            context: Contexto completo de la conversación.

        Returns:
            String con la respuesta de texto de la IA.
        """
        ...

    async def cleanup(self) -> None:
        """
        Libera recursos del proveedor al cerrar la aplicación.

        Por defecto no hace nada. Los proveedores que mantengan
        conexiones abiertas deben sobreescribir este método.
        """
        pass