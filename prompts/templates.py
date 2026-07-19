"""
Plantillas de prompts reutilizables.

Contiene fragmentos de texto que se pueden inyectar en diferentes
contextos: resumen de documentos, análisis de errores, etc.

Decisiones de diseño:
    - Se separan del system prompt principal para mantener limpio
      el archivo system_prompt.py.
    - Cada plantilla es una función que recibe parámetros y retorna
      un string formateado. Esto permite personalización dinámica.
"""

from __future__ import annotations


def summarize_document_prompt(file_name: str, file_content: str) -> str:
    """
    Genera un prompt para resumir un documento.

    Se usa cuando el usuario pide que se resuma un archivo de texto.
    El contenido del archivo se inyecta en el prompt para que la IA lo procese.

    Args:
        file_name: Nombre del archivo.
        file_content: Contenido del archivo (o primeras N líneas).

    Returns:
        Prompt listo para enviar a la IA.
    """
    return (
        f"Resume el siguiente documento de forma clara y concisa. "
        f"Incluye los puntos principales:\n\n"
        f"Archivo: {file_name}\n"
        f"---\n"
        f"{file_content}\n"
        f"---\n"
        f"Resumen:"
    )


def error_analysis_prompt(error_message: str, context: str = "") -> str:
    """
    Genera un prompt para analizar un error.

    Se usa para entender errores complejos y sugerir soluciones.

    Args:
        error_message: Mensaje de error a analizar.
        context: Contexto adicional sobre dónde ocurrió el error.

    Returns:
        Prompt listo para enviar a la IA.
    """
    context_section = f"\nContexto: {context}" if context else ""
    return (
        f"Analiza este error y sugiere una solución:\n\n"
        f"Error: {error_message}{context_section}\n\n"
        f"Respuesta concisa con la causa probable y la solución:"
    )


def task_planning_prompt(task_description: str) -> str:
    """
    Genera un prompt para planificar una tarea compleja.

    Se usa cuando el usuario pide algo que requiere múltiples pasos.

    Args:
        task_description: Descripción de la tarea a planificar.

    Returns:
        Prompt listo para enviar a la IA.
    """
    return (
        f"Planifica esta tarea en pasos concretos:\n\n"
        f"Tarea: {task_description}\n\n"
        f"Retorna un JSON con la siguiente estructura:\n"
        f'{{"action": "task_plan", "parameters": {{"steps": ["paso1", "paso2", ...], '
        f'"description": "resumen de la tarea"}}}}'
    )