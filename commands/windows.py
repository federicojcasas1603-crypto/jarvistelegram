"""
Comandos para abrir y cerrar programas en Windows.

Escanea automáticamente las apps instaladas en:
- Program Files / Program Files (x86)
- Accesos directos del Menú Inicio
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

# Programas del sistema (siempre disponibles)
SYSTEM_PROGRAMS: dict[str, str] = {
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calc": "calc.exe",
    "calculadora": "calc.exe",
    "explorer": "explorer.exe",
    "explorador": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "administrador de tareas": "taskmgr.exe",
    "control panel": "control.exe",
    "panel de control": "control.exe",
    "settings": "ms-settings:",
    "configuracion": "ms-settings:",
}

# Cache de programas escaneados
_scanned_programs: dict[str, str] | None = None
_scan_time: float = 0
SCAN_CACHE_SECONDS = 300  # re-escanear cada 5 min


def _scan_installed_programs() -> dict[str, str]:
    """
    Escanea el PC buscando todas las aplicaciones instaladas.

    Busca en:
    1. C:/Program Files y Program Files (x86) por carpetas con .exe
    2. Menú Inicio por accesos directos .lnk

    Returns:
        Diccionario {nombre: ruta_completa_o_ejecutable}
    """
    global _scanned_programs, _scan_time

    if _scanned_programs is not None and (time.time() - _scan_time) < SCAN_CACHE_SECONDS:
        return _scanned_programs

    logger.info("Escaneando aplicaciones instaladas...")
    programs: dict[str, str] = {}

    # 1. Escanear Program Files
    pf_paths = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", "") + "\\Programs",
    ]

    for base in pf_paths:
        if not base or not os.path.isdir(base):
            continue
        try:
            for folder in os.listdir(base):
                folder_path = os.path.join(base, folder)
                if not os.path.isdir(folder_path):
                    continue
                # Buscar el .exe principal en la carpeta
                for f in os.listdir(folder_path):
                    if f.lower().endswith(".exe") and not f.lower().startswith("unins"):
                        name = folder.lower().replace(" ", "_")
                        exe_path = os.path.join(folder_path, f)
                        programs[name] = exe_path
                        # También registrar por nombre del exe sin extensión
                        exe_name = f.lower().replace(".exe", "")
                        if exe_name not in programs:
                            programs[exe_name] = exe_path
                        break
        except PermissionError:
            continue

    # 2. Escanear accesos directos del Menú Inicio
    start_menu_paths = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
    ]

    for sm_path in start_menu_paths:
        if not os.path.isdir(sm_path):
            continue
        try:
            for root, dirs, files in os.walk(sm_path):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = f.lower().replace(".lnk", "").replace(" ", "_")
                        # Intentar resolver el .lnk para obtener el target
                        shortcut_path = os.path.join(root, f)
                        target = _resolve_shortcut(shortcut_path)
                        if target:
                            programs[name] = target
        except PermissionError:
            continue

    _scanned_programs = programs
    _scan_time = time.time()
    logger.info("Escaneo completado: %d aplicaciones encontradas", len(programs))
    return programs


def _resolve_shortcut(lnk_path: str) -> str | None:
    """Resuelve un acceso directo .lnk para obtener el ejecutable target."""
    try:
        # Usar PowerShell para leer el target del .lnk
        ps_cmd = (
            f'$sh = New-Object -ComObject WScript.Shell; '
            f'$sc = $sh.CreateShortcut("{lnk_path}"); '
            f'Write-Output $sc.TargetPath'
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
        )
        target = result.stdout.strip()
        if target and os.path.exists(target):
            return target
    except Exception:
        pass
    return None


def _get_all_programs() -> dict[str, str]:
    """Retorna todos los programas: sistema + escaneados."""
    all_programs = dict(SYSTEM_PROGRAMS)
    scanned = _scan_installed_programs()
    all_programs.update(scanned)
    return all_programs


class OpenProgramCommand(Command):
    """Comando que abre un programa en el sistema."""

    @property
    def name(self) -> str:
        return "open_program"

    @property
    def description(self) -> str:
        return "Abre un programa o aplicación en el sistema"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        program = params.get("program", "").strip().lower()
        args = params.get("args", [])

        if not program:
            return CommandResult.fail("No se especificó un programa para abrir.")

        all_programs = _get_all_programs()
        exe = all_programs.get(program, program)

        # Intentar abrir
        if exe.endswith(".exe") or exe.startswith("ms-"):
            try:
                if exe.startswith("ms-"):
                    os.startfile(exe)
                else:
                    subprocess.Popen(
                        [exe] + args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                logger.info("Programa abierto: %s", exe)
                return CommandResult.ok(f"Programa '{program}' abierto correctamente.")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.exception("Error al abrir programa %s", exe)
                return CommandResult.fail(f"Error al abrir '{program}': {e}")

        try:
            cmd = [exe] + args if args else [exe]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Programa abierto: %s", exe)
            return CommandResult.ok(f"Programa '{program}' abierto correctamente.")
        except FileNotFoundError:
            return CommandResult.fail(
                f"No se encontró el programa '{program}'. "
                "Usa /list_programs para ver los disponibles."
            )
        except Exception as e:
            logger.exception("Error al abrir programa %s", program)
            return CommandResult.fail(f"Error al abrir '{program}': {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("program"):
            errors.append("El parámetro 'program' es obligatorio.")
        return errors


class CloseProgramCommand(Command):
    """Comando que cierra un programa por nombre."""

    @property
    def name(self) -> str:
        return "close_program"

    @property
    def description(self) -> str:
        return "Cierra un programa o proceso en el sistema"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        program = params.get("program", "").strip().lower()

        if not program:
            return CommandResult.fail("No se especificó un programa para cerrar.")

        all_programs = _get_all_programs()
        exe_path = all_programs.get(program, program)

        # Obtener solo el nombre del exe
        exe_name = os.path.basename(exe_path)
        if not exe_name.endswith(".exe"):
            exe_name = f"{exe_name}.exe"

        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", exe_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("Programa cerrado: %s", exe_name)
                return CommandResult.ok(f"Programa '{program}' cerrado correctamente.")
            else:
                if "no se encuentra" in result.stderr.lower() or "not found" in result.stderr.lower():
                    return CommandResult.fail(f"No se encontró el programa '{program}' ejecutándose.")
                return CommandResult.fail(f"Error al cerrar '{program}': {result.stderr.strip()}")
        except Exception as e:
            logger.exception("Error al cerrar programa %s", program)
            return CommandResult.fail(f"Error al cerrar '{program}': {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("program"):
            errors.append("El parámetro 'program' es obligatorio.")
        return errors


class ListProgramsCommand(Command):
    """Lista todas las aplicaciones disponibles para abrir."""

    @property
    def name(self) -> str:
        return "list_programs"

    @property
    def description(self) -> str:
        return "Escanea y muestra todas las aplicaciones instaladas"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        all_programs = _get_all_programs()

        # Agrupar: nombre original → ruta
        by_name: dict[str, str] = {}
        for alias, exe in sorted(all_programs.items()):
            if alias not in by_name:
                by_name[alias] = exe

        # Mostrar solo nombres (sin rutas largas) y agrupar por类别
        system = []
        scanned = []

        for name, exe in sorted(by_name.items()):
            if name in SYSTEM_PROGRAMS:
                system.append(name)
            else:
                # Mostrar nombre amigable
                display = name.replace("_", " ").title()
                scanned.append(f"  {display}  (/{name})")

        lines = ["APLICACIONES DEL SISTEMA:\n"]
        for name in sorted(system):
            lines.append(f"  /{name}")

        if scanned:
            lines.append(f"\nAPLICACIONES INSTALADAS ({len(scanned)}):\n")
            lines.extend(scanned)

        lines.append(f"\nTotal: {len(by_name)} aplicaciones")
        lines.append("\nUsa /open_program nombre_para_abrir")
        lines.append("Ejemplo: /open_program visual_studio_code")

        result = "\n".join(lines)

        # Telegram limita a 4096 chars
        if len(result) > 4000:
            result = result[:3900] + "\n\n... (truncado, usa /open_program nombre)"

        return CommandResult.ok(result)


# Auto-registro
get_registry().register(OpenProgramCommand())
get_registry().register(CloseProgramCommand())
get_registry().register(ListProgramsCommand())


class NotifyCommand(Command):
    """Muestra una notificación en pantalla con el mensaje que el usuario quiera."""

    @property
    def name(self) -> str:
        return "notify"

    @property
    def description(self) -> str:
        return "Muestra un mensaje en pantalla del PC"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        message = params.get("message", "").strip()
        title = params.get("title", "Jarvis").strip()

        if not message:
            return CommandResult.fail("No se especificó un mensaje.")

        try:
            # Toast notification de Windows 10/11
            ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">{title}</text>
            <text id="2">{message}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Jarvis").Show($toast)
'''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return CommandResult.ok(f"Mensaje mostrado en pantalla: {message}")
            else:
                # Fallback: usar msg.exe o MessageBox
                return _fallback_notify(title, message)
        except Exception as e:
            logger.exception("Error al mostrar notificación")
            return _fallback_notify(title, message)

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("message"):
            errors.append("El parámetro 'message' es obligatorio.")
        return errors


def _fallback_notify(title: str, message: str) -> CommandResult:
    """Fallback: MessageBox usando ctypes."""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x100000)
        return CommandResult.ok(f"Mensaje mostrado en pantalla: {message}")
    except Exception as e:
        return CommandResult.fail(f"No se pudo mostrar el mensaje: {e}")


class NotifyAllCommand(Command):
    """Muestra un popup que requiere hacer clic en Aceptar (no se pierde)."""

    @property
    def name(self) -> str:
        return "popup"

    @property
    def description(self) -> str:
        return "Muestra un popup modal en pantalla (requiere clic en Aceptar)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        message = params.get("message", "").strip()
        title = params.get("title", "Jarvis").strip()

        if not message:
            return CommandResult.fail("No se especificó un mensaje.")

        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            return CommandResult.ok(f"Popup mostrado: {message}")
        except Exception as e:
            logger.exception("Error al mostrar popup")
            return CommandResult.fail(f"No se pudo mostrar el popup: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("message"):
            errors.append("El parámetro 'message' es obligatorio.")
        return errors


get_registry().register(NotifyCommand())
get_registry().register(NotifyAllCommand())
