"""
Modelo de datos para acciones estructuradas.

Esta es la pieza central del sistema de seguridad.
La IA únicamente genera instancias de Action (en formato JSON).
El programa las interprete y ejecuta.

Flujo:
    1. El usuario envía un mensaje por Telegram.
    2. La IA analiza el mensaje y devuelve un JSON con la estructura de Action.
    3. El action_validator verifica que la acción sea válida y segura.
    4. El dispatcher ejecuta la acción correspondiente.

Ejemplo de JSON que la IA debe generar:
    {
        "action": "open_program",
        "parameters": {"program": "notepad"},
        "requires_confirmation": false,
        "reason": "El usuario pidió abrir el bloc de notas"
    }

Decisiones de diseño:
    - Se usa dataclass en lugar de Pydantic para no agregar dependencias extra.
    - 'parameters' es un dict genérico porque cada acción tiene parámetros
      diferentes. La validación específica la hace cada Command concreto.
    - 'requires_confirmation' permite que ciertas acciones peligrosas
      (como apagar la PC) requieran aprobación del usuario antes de ejecutarse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    """
    Representa una acción que la IA desea ejecutar.

    Attributes:
        action: Identificador del tipo de acción.
                Debe coincidir con el nombre registrado en el dispatcher.
                Ejemplos: "open_program", "search_files", "take_screenshot".
        parameters: Diccionario con los parámetros específicos de la acción.
                    Cada tipo de acción espera parámetros diferentes.
                    Ejemplo: {"program": "chrome"} o {"query": "*.pdf"}.
        requires_confirmation: Si es True, el sistema pedirá confirmación
                              al usuario antes de ejecutar la acción.
                              Debe ser True para acciones destructivas.
        reason: Explicación breve de por qué la IA eligió esta acción.
                Útil para logs y depuración. La IA debe generar esta campo.
    """

    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        """
        Crea una instancia de Action desde un diccionario (JSON parseado).

        Este método se usa para convertir la respuesta de la IA en un objeto
        tipado y validado. Si el JSON no tiene los campos mínimos necesarios,
        se lanzará un ValueError con un mensaje descriptivo.

        Args:
            data: Diccionario con la respuesta parseada de la IA.

        Returns:
            Instancia de Action con los valores del diccionario.

        Raises:
            ValueError: Si falta el campo 'action' o no es una cadena de texto.

        Example:
            >>> action = Action.from_dict({
            ...     "action": "open_program",
            ...     "parameters": {"program": "notepad"},
            ...     "requires_confirmation": False,
            ...     "reason": "El usuario pide abrir el bloc de notas"
            ... })
            >>> action.action
            'open_program'
        """
        if "action" not in data:
            raise ValueError(
                "La respuesta de la IA no contiene el campo 'action'. "
                f"JSON recibido: {data}"
            )

        if not isinstance(data["action"], str):
            raise ValueError(
                f"El campo 'action' debe ser una cadena de texto. "
                f"Tipo recibido: {type(data['action']).__name__}"
            )

        if data["action"].strip() == "":
            raise ValueError("El campo 'action' no puede estar vacío.")

        return cls(
            action=data["action"].strip(),
            parameters=data.get("parameters", {}),
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            reason=data.get("reason", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convierte la acción a un diccionario serializable.

        Útil para logging y debugging.

        Returns:
            Diccionario con todos los campos de la acción.
        """
        return {
            "action": self.action,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
        }

    def __str__(self) -> str:
        """Representación legible para humanos y logs."""
        params = (
            ", ".join(f"{k}={v!r}" for k, v in self.parameters.items())
            if self.parameters
            else "sin parámetros"
        )
        confirm = " [REQUIERE CONFIRMACIÓN]" if self.requires_confirmation else ""
        return f"Action({self.action}: {params}{confirm})"