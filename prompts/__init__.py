"""
Paquete de prompts para la IA.

Contiene el system prompt y plantillas reutilizables que definen
el comportamiento del asistente y el formato de sus respuestas.

Uso:
    from prompts import build_system_prompt
    prompt = build_system_prompt(action_list)
"""

from prompts.system_prompt import build_system_prompt

__all__ = ["build_system_prompt"]