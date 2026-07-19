"""
Comandos para abrir y cerrar programas en Windows.

Uso desde Telegram: "Abre el Bloc de notas", "Cierra Chrome".
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

# Programas conocidos y sus ejecutables
KNOWN_PROGRAMS: dict[str, str] = {
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calc": "calc.exe",
    "calculadora": "calc.exe",
    "explorer": "explorer.exe",
    "explorador": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "administrador de tareas": "taskmgr.exe",
    "control panel": "control.exe",
    "panel de control": "control.exe",
    "settings": "ms-settings:",
    "configuracion": "ms-settings:",
    "vscode": "code.exe",
    "visual studio code": "code.exe",
}


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

        # Buscar en programas conocidos
        exe = KNOWN_PROGRAMS.get(program, program)

        # Si tiene extensión .exe, intentar con os.startfile
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
                # No se encontró directamente, intentar buscar en PATH
                pass
            except Exception as e:
                logger.exception("Error al abrir programa %s", exe)
                return CommandResult.fail(f"Error al abrir '{program}': {e}")

        # Intentar con subprocess.run para programas no .exe
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
                "Verifica el nombre o instala el programa."
            )
        except Exception as e:
            logger.exception("Error al abrir programa %s", program)
            return CommandResult.fail(f"Error al abrir '{program}': {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        program = params.get("program")
        if not program or not str(program).strip():
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

        # Buscar nombre real del ejecutable
        exe_name = KNOWN_PROGRAMS.get(program, program)
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
        program = params.get("program")
        if not program or not str(program).strip():
            errors.append("El parámetro 'program' es obligatorio.")
        return errors


# Auto-registro
get_registry().register(OpenProgramCommand())
get_registry().register(CloseProgramCommand())
