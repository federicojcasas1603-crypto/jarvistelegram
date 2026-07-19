"""
Esquemas de parámetros para cada acción permitida.

Este módulo contiene la definición estática de qué parámetros
requiere y acepta cada tipo de acción. El validador usa estos
esquemas para verificar que la IA genera acciones correctamente.

Decisiones de diseño:
    - Se separan los esquemas del validador para mantener archivos < 300 líneas.
    - Cada esquema es un diccionario con 'required' y 'optional'.
    - Cada entrada es una tupla (nombre, tipo_esperado).
    - Si el tipo es None, se acepta cualquier tipo de dato.
    - Este archivo es puro datos: no tiene lógica ni dependencias.
"""

from __future__ import annotations

# Formato de cada esquema:
# {
#     "required": [(nombre_param, tipo_esperado), ...],
#     "optional": [(nombre_param, tipo_esperado), ...],
# }

ACTION_SCHEMAS: dict[str, dict[str, list[tuple[str, type | None]]]] = {
    # ============================================
    # PROGRAMAS
    # ============================================
    "open_program": {
        "required": [("program", str)],
        "optional": [("args", list)],
    },
    "close_program": {
        "required": [("program", str)],
        "optional": [],
    },

    # ============================================
    # ARCHIVOS
    # ============================================
    "search_files": {
        "required": [("query", str)],
        "optional": [("directory", str), ("recursive", bool)],
    },
    "copy_file": {
        "required": [("source", str), ("destination", str)],
        "optional": [],
    },
    "move_file": {
        "required": [("source", str), ("destination", str)],
        "optional": [],
    },
    "rename_file": {
        "required": [("old_name", str), ("new_name", str)],
        "optional": [],
    },
    "delete_file": {
        "required": [("path", str)],
        "optional": [],
    },
    "read_file": {
        "required": [("file_path", str)],
        "optional": [("max_lines", int)],
    },
    "send_file": {
        "required": [("file_path", str)],
        "optional": [],
    },

    # ============================================
    # CARPETAS
    # ============================================
    "create_folder": {
        "required": [("path", str)],
        "optional": [],
    },

    # ============================================
    # SISTEMA
    # ============================================
    "system_info": {
        "required": [],
        "optional": [],
    },
    "system_resources": {
        "required": [],
        "optional": [],
    },
    "shutdown": {
        "required": [],
        "optional": [("action_type", str)],
    },
    "restart": {
        "required": [],
        "optional": [],
    },
    "suspend": {
        "required": [],
        "optional": [],
    },

    # ============================================
    # NAVEGADOR
    # ============================================
    "open_url": {
        "required": [("url", str)],
        "optional": [],
    },

    # ============================================
    # CAPTURAS
    # ============================================
    "take_screenshot": {
        "required": [],
        "optional": [],
    },

    # ============================================
    # PORTAPAPELES
    # ============================================
    "clipboard_read": {
        "required": [],
        "optional": [],
    },
    "clipboard_write": {
        "required": [("text", str)],
        "optional": [],
    },

    # ============================================
    # SCRIPTS
    # ============================================
    "run_script": {
        "required": [("script_path", str)],
        "optional": [],
    },
    "execute_python": {
        "required": [("code", str)],
        "optional": [],
    },

    # ============================================
    # DOCUMENTOS
    # ============================================
    "summarize_document": {
        "required": [("file_path", str)],
        "optional": [],
    },

    # ============================================
    # ORGANIZACIÓN
    # ============================================
    "organize_downloads": {
        "required": [],
        "optional": [("directory", str)],
    },

    # ============================================
    # MÚSICA
    # ============================================
    "play_music": {
        "required": [],
        "optional": [("query", str)],
    },
    "stop_music": {
        "required": [],
        "optional": [],
    },
    "pause_music": {
        "required": [],
        "optional": [],
    },

    # ============================================
    # MEMORIA
    # ============================================
    "save_memory": {
        "required": [("key", str), ("value", str)],
        "optional": [],
    },
    "recall_memory": {
        "required": [("key", str)],
        "optional": [],
    },

    # ============================================
    # NAVEGACIÓN
    # ============================================
    "list_directory": {
        "required": [],
        "optional": [("path", str)],
    },
    "cd": {
        "required": [],
        "optional": [("path", str)],
    },
}