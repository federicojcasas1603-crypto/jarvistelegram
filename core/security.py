"""
Políticas de seguridad centralizadas.

Este módulo define TODAS las reglas de seguridad del sistema en un solo lugar.
Cualquier cambio en las políticas se hace aquí y aplica globalmente.

Filosofía de seguridad:
    1. Whitelist, no blacklist: solo se permite lo que está explícitamente listado.
    2. Confirmación obligatoria para acciones destructivas o peligrosas.
    3. Rutas del sistema protegidas: la IA no puede modificar archivos críticos.
    4. Principio de mínimo privilegio: cada acción solo puede acceder a lo necesario.

Decisiones de diseño:
    - Se usa una dataclass con constants para que el validador y el despachador
      compartan la misma fuente de verdad.
    - Las acciones que requieren confirmación están en un set separado para
      que sea trivial agregar nuevas acciones peligrosas.
    - Las rutas protegidas usan normalización de path para evitar bypass
      con '../' o symlinks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ============================================
# ACCIONES PERMITIDAS (WHITELIST)
# ============================================
# Solo las acciones listadas aquí pueden ser ejecutadas por la IA.
# Para agregar una nueva acción, agregar su nombre como string.
ALLOWED_ACTIONS: set[str] = {
    # --- Programas ---
    "open_program",
    "close_program",
    # --- Archivos ---
    "search_files",
    "copy_file",
    "move_file",
    "rename_file",
    "delete_file",
    "read_file",
    "send_file",
    # --- Carpetas ---
    "create_folder",
    # --- Sistema ---
    "system_info",
    "system_resources",
    "shutdown",
    "restart",
    "suspend",
    # --- Navegador ---
    "open_url",
    # --- Capturas ---
    "take_screenshot",
    # --- Portapapeles ---
    "clipboard_read",
    "clipboard_write",
    # --- Scripts ---
    "run_script",
    "execute_python",
    # --- Documentos ---
    "summarize_document",
    # --- Organización ---
    "organize_downloads",
    # --- Música ---
    "play_music",
    "stop_music",
    "pause_music",
    # --- Memoria ---
    "save_memory",
    "recall_memory",
    # --- Navegación ---
    "list_directory",
    "dir",
    "cd",
    # --- Lista de apps ---
    "list_programs",
}

# ============================================
# ACCIONES QUE SIEMPRE REQUIEREN CONFIRMACIÓN
# ============================================
# La IA puede poner requires_confirmation=True en cualquier acción,
# pero estasacciones LO REQUIEREN SIEMPRE independientemente de lo
# que la IA decida. Esto previene que un prompt injection las ejecute.
ALWAYS_CONFIRM: set[str] = {
    "delete_file",
    "shutdown",
    "restart",
    "suspend",
    "run_script",
    "execute_python",
}

# ============================================
# ACCIONES DESTRUCTIVAS (mayor nivel de审查)
# ============================================
# Estas acciones tienen un审查 adicional: se registra extra detail
# en los logs y se muestra una advertencia más prominente al usuario.
DESTRUCTIVE_ACTIONS: set[str] = {
    "delete_file",
    "shutdown",
    "restart",
    "move_file",
    "rename_file",
}

# ============================================
# RUTAS PROHIBIDAS
# ============================================
# Ninguna acción puede leer/escribir/eliminar archivos en estas rutas.
# Se normalizan con Path.resolve() para evitar bypass con '../'.
FORBIDDEN_PATHS: list[str] = [
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Windows\\Boot",
    "C:\\Program Files\\Windows Defender",
    "C:\\ProgramData\\Microsoft",
    "C:\\Recovery",
    "$Recycle.Bin",
]

# ============================================
# EXTENSIONES PROHIBIDAS
# ============================================
# La IA no puede ejecutar ni modificar archivos con estas extensiones.
FORBIDDEN_EXTENSIONS: set[str] = {
    ".exe",
    ".dll",
    ".sys",
    ".msi",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".scr",
    ".com",
}

# ============================================
# PROGRAMAS PROHIBIDOS
# ============================================
# La IA no puede abrir ni cerrar estos programas por nombre.
FORBIDDEN_PROGRAMS: set[str] = {
    "cmd",
    "powershell",
    "regedit",
    "msconfig",
    "diskpart",
    "format",
}

# ============================================
# LÍMITES DEL SISTEMA
# ============================================
MAX_FILE_READ_LINES: int = 500
MAX_SEARCH_RESULTS: int = 50
MAX_FILE_SIZE_MB: int = 100
MAX_SCRIPT_LINES: int = 100


@dataclass(frozen=True)
class SecurityPolicy:
    """
    Configuración inmutable de políticas de seguridad.

    Agrupa todas las reglas en un solo objeto que se pasa al validador.
    Frozen=True previene modificaciones accidentales en runtime.

    Attributes:
        allowed_actions: Conjunto de acciones que el sistema puede ejecutar.
        always_confirm: Acciones que SIEMPRE requieren confirmación del usuario.
        destructive_actions: Acciones destructivas con审查 adicional.
        forbidden_paths: Rutas del sistema que están protegidas.
        forbidden_extensions: Extensiones de archivos que no se pueden procesar.
        forbidden_programs: Programas que la IA no puede abrir/cerrar.
        max_file_read_lines: Límite de líneas al leer archivos de texto.
        max_search_results: Límite de resultados en búsquedas de archivos.
        max_file_size_mb: Tamaño máximo de archivo para operaciones.
        max_script_lines: Límite de líneas para scripts que la IA puede generar.
    """

    allowed_actions: frozenset[str] = field(default_factory=lambda: frozenset(ALLOWED_ACTIONS))
    always_confirm: frozenset[str] = field(default_factory=lambda: frozenset(ALWAYS_CONFIRM))
    destructive_actions: frozenset[str] = field(default_factory=lambda: frozenset(DESTRUCTIVE_ACTIONS))
    forbidden_paths: tuple[str, ...] = tuple(FORBIDDEN_PATHS)
    forbidden_extensions: frozenset[str] = field(default_factory=lambda: frozenset(FORBIDDEN_EXTENSIONS))
    forbidden_programs: frozenset[str] = field(default_factory=lambda: frozenset(FORBIDDEN_PROGRAMS))
    max_file_read_lines: int = MAX_FILE_READ_LINES
    max_search_results: int = MAX_SEARCH_RESULTS
    max_file_size_mb: int = MAX_FILE_SIZE_MB
    max_script_lines: int = MAX_SCRIPT_LINES

    def is_action_allowed(self, action_name: str) -> bool:
        """
        Verifica si una acción está en la whitelist.

        Args:
            action_name: Nombre de la acción a verificar.

        Returns:
            True si la acción está permitida, False en caso contrario.
        """
        return action_name in self.allowed_actions

    def requires_confirmation(self, action_name: str) -> bool:
        """
        Verifica si una acción requiere confirmación obligatoria.

        Args:
            action_name: Nombre de la acción a verificar.

        Returns:
            True si la acción requiere confirmación.
        """
        return action_name in self.always_confirm

    def is_destructive(self, action_name: str) -> bool:
        """
        Verifica si una acción es destructiva.

        Args:
            action_name: Nombre de la acción a verificar.

        Returns:
            True si la acción es destructiva.
        """
        return action_name in self.destructive_actions

    def is_path_safe(self, file_path: str) -> bool:
        """
        Verifica que una ruta no esté en la lista de rutas prohibidas.

        Normaliza la ruta usando Path.resolve() para detectar intentos
        de bypass con '../', symlinks, o rutas relativas engañosas.

        Args:
            file_path: Ruta del archivo a verificar.

        Returns:
            True si la ruta es segura, False si está prohibida.

        Example:
            >>> policy = SecurityPolicy()
            >>> policy.is_path_safe("C:\\Users\\feder\\Documents\\file.txt")
            True
            >>> policy.is_path_safe("C:\\Windows\\System32\\config")
            False
        """
        try:
            resolved = Path(file_path).resolve()
            resolved_str = str(resolved).lower()

            for forbidden in self.forbidden_paths:
                forbidden_resolved = str(Path(forbidden).resolve()).lower()
                if resolved_str.startswith(forbidden_resolved):
                    return False

            return True
        except (ValueError, OSError):
            return False

    def is_extension_safe(self, file_path: str) -> bool:
        """
        Verifica que la extensión de un archivo no esté prohibida.

        Args:
            file_path: Ruta del archivo a verificar.

        Returns:
            True si la extensión es segura.
        """
        suffix = Path(file_path).suffix.lower()
        return suffix not in self.forbidden_extensions

    def is_program_allowed(self, program_name: str) -> bool:
        """
        Verifica que un programa no esté en la lista de prohibidos.

        Args:
            program_name: Nombre del programa a verificar.

        Returns:
            True si el programa está permitido.
        """
        return program_name.lower().strip() not in self.forbidden_programs