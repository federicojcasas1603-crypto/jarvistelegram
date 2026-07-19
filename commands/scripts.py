"""
Comandos para ejecutar scripts y código Python.

Uso desde Telegram: "Ejecuta el script de respaldo", "Corre este código".
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import os
from typing import Any

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)

MAX_OUTPUT_LINES = 100
MAX_OUTPUT_BYTES = 50000


class RunScriptCommand(Command):
    """Ejecuta un script Python existente."""

    @property
    def name(self) -> str:
        return "run_script"

    @property
    def description(self) -> str:
        return "Ejecuta un script Python existente en el sistema"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        script_path = os.path.expanduser(params.get("script_path", ""))

        if not os.path.exists(script_path):
            return CommandResult.fail(f"Script no encontrado: {script_path}")

        if not script_path.endswith(".py"):
            return CommandResult.fail("Solo se pueden ejecutar scripts Python (.py).")

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\n--- STDERR ---\n{result.stderr.strip()}"

            if not output:
                output = "(sin salida)"

            # Truncar si es muy largo
            lines = output.split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                output = "\n".join(lines[:MAX_OUTPUT_LINES]) + f"\n... (truncado, {len(lines)} líneas totales)"

            status = "éxito" if result.returncode == 0 else f"error (código {result.returncode})"
            logger.info("Script ejecutado: %s (%s)", script_path, status)

            return CommandResult.ok(f"Script ejecutado ({status}):\n```\n{output}\n```")

        except subprocess.TimeoutExpired:
            return CommandResult.fail("El script tardó demasiado (>60s) y fue detenido.")
        except Exception as e:
            logger.exception("Error al ejecutar script")
            return CommandResult.fail(f"Error al ejecutar el script: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("script_path"):
            errors.append("El parámetro 'script_path' es obligatorio.")
        return errors

    def requires_confirmation(self) -> bool:
        return True


class ExecutePythonCommand(Command):
    """Ejecuta código Python inline."""

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return "Ejecuta un fragmento de código Python (requiere confirmación)"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        code = params.get("code", "")

        if not code.strip():
            return CommandResult.fail("No se proporcionó código para ejecutar.")

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            os.unlink(temp_path)

            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\n--- STDERR ---\n{result.stderr.strip()}"

            if not output:
                output = "(sin salida)"

            lines = output.split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                output = "\n".join(lines[:MAX_OUTPUT_LINES]) + f"\n... (truncado, {len(lines)} líneas totales)"

            status = "éxito" if result.returncode == 0 else f"error (código {result.returncode})"
            logger.info("Código Python ejecutado (%s)", status)

            return CommandResult.ok(f"Código ejecutado ({status}):\n```\n{output}\n```")

        except subprocess.TimeoutExpired:
            return CommandResult.fail("El código tardó demasiado (>30s) y fue detenido.")
        except Exception as e:
            logger.exception("Error al ejecutar código Python")
            return CommandResult.fail(f"Error al ejecutar el código: {e}")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("code"):
            errors.append("El parámetro 'code' es obligatorio.")
        return errors

    def requires_confirmation(self) -> bool:
        return True


# Auto-registro
get_registry().register(RunScriptCommand())
get_registry().register(ExecutePythonCommand())
