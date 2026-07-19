"""
Modelo de datos para el resultado de la ejecución de un comando.

Cuando un comando se ejecuta, debe reportar qué pasó de forma estructurada.
El motor usa este resultado para:
    1. Generar una respuesta legible para el usuario.
    2. Decidir si enviar un archivo adjunto por Telegram.
    3. Registrar el resultado en los logs.
    4. Actualizar la memoria si es necesario.

Decisiones de diseño:
    - Se separa 'message' (respuesta para el usuario) de 'error' (detalle técnico).
      Esto permite mostrar al usuario un mensaje amigable mientras el error
      completo se registra en los logs.
    - 'data' es un dict genérico para resultados que necesitan datos extra
      (por ejemplo, la lista de archivos encontrados, uso de CPU, etc.).
    - 'send_file' es una ruta a un archivo que el bot debe enviar por Telegram.
      Se mantiene separado de 'data' porque requiere un flujo especial de envío.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandResult:
    """
    Resultado de la ejecución de un comando.

    Attributes:
        success: Indica si la ejecución fue exitosa.
        message: Mensaje legible para el usuario con el resultado de la acción.
                 Ejemplo: "Chrome se ha abierto correctamente."
        error: Detalle técnico del error si la ejecución falló.
               Solo se llena cuando success=False. Se registra en logs, no se
               muestra directamente al usuario.
        data: Datos adicionales del resultado. Estructura variable según el
              comando. Ejemplo: [{"name": "file.pdf", "size": 1024}].
        send_file: Ruta absoluta a un archivo que el bot debe enviar por Telegram.
                   Si es None, no se envía ningún archivo.
    """

    success: bool
    message: str
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    send_file: str | None = None

    @classmethod
    def ok(cls, message: str, data: dict[str, Any] | None = None, send_file: str | None = None) -> CommandResult:
        """
        Crea un resultado exitoso de forma concisa.

        Método de conveniencia para el caso más común: exito sin errores.

        Args:
            message: Mensaje para el usuario.
            data: Datos opcionales del resultado.
            send_file: Ruta de archivo a enviar opcionalmente.

        Returns:
            Instancia de CommandResult con success=True.

        Example:
            >>> result = CommandResult.ok("Chrome abierto correctamente")
            >>> result.success
            True
        """
        return cls(
            success=True,
            message=message,
            data=data or {},
            send_file=send_file,
        )

    @classmethod
    def fail(cls, message: str, error: str | None = None) -> CommandResult:
        """
        Crea un resultado fallido de forma concisa.

        Método de conveniencia para reportar errores de forma consistente.

        Args:
            message: Mensaje amigable para el usuario.
            error: Detalle técnico del error (para logs).

        Returns:
            Instancia de CommandResult con success=False.

        Example:
            >>> result = CommandResult.fail(
            ...     "No se pudo encontrar el archivo",
            ...     error="FileNotFoundError: /tmp/foo.txt"
            ... )
            >>> result.success
            False
        """
        return cls(
            success=False,
            message=message,
            error=error or message,
        )

    def __str__(self) -> str:
        """Representación legible para logs."""
        status = "OK" if self.success else "FAIL"
        parts = [f"[{status}] {self.message}"]
        if self.error:
            parts.append(f" Error: {self.error}")
        if self.send_file:
            parts.append(f" File: {self.send_file}")
        return "".join(parts)