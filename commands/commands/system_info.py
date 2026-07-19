"""
Comando de información general del sistema.

Retorna datos estáticos del sistema operativo, hardware y red.
Es de solo lectura y no tiene efectos secundarios.

Uso desde Telegram: "¿Qué computadora es esta?"
"""

from __future__ import annotations

import logging
import platform
import socket
from typing import Any

import psutil

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


class SystemInfoCommand(Command):
    """
    Comando que retorna información general del sistema.

    Incluye: sistema operativo, máquina, usuario, Python, red, pantalla.
    No recibe parámetros. Es de solo lectura.
    """

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Obtiene información general del sistema: OS, máquina, usuario, Python, red"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        """
        Recopila y retorna información del sistema.

        Returns:
            CommandResult con un diccionario 'data' que contiene
            toda la información del sistema, y un 'message' formateado
            para enviar al usuario por Telegram.
        """
        try:
            info: dict[str, Any] = {
                "sistema_operativo": f"{platform.system()} {platform.release()}",
                "version_os": platform.version(),
                "arquitectura": platform.machine(),
                "procesador": platform.processor() or "No disponible",
                "nombre_maquina": socket.gethostname(),
                "usuario": platform.node(),
                "python_version": platform.python_version(),
                "directorio_actual": self._safe_getcwd(),
                "boot_time": self._get_boot_time(),
                "uptime": self._get_uptime(),
            }

            net_info = self._get_network_info()
            if net_info:
                info["interfaces_red"] = net_info

            message = self._format_message(info)

            logger.info("system_info ejecutado correctamente")
            return CommandResult.ok(message=message, data=info)

        except Exception as e:
            error_msg = f"Error al obtener información del sistema: {e}"
            logger.exception(error_msg)
            return CommandResult.fail(message=error_msg, error=str(e))

    @staticmethod
    def _safe_getcwd() -> str:
        """Obtiene el directorio actual de forma segura."""
        try:
            import os
            return os.getcwd()
        except OSError:
            return "No disponible"

    @staticmethod
    def _get_boot_time() -> str:
        """Obtiene la fecha y hora de último encendido."""
        try:
            import datetime
            boot_ts = psutil.boot_time()
            boot_dt = datetime.datetime.fromtimestamp(boot_ts)
            return boot_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (psutil.Error, OSError, ValueError):
            return "No disponible"

    @staticmethod
    def _get_uptime() -> str:
        """Calcula el tiempo que lleva encendido el sistema."""
        try:
            import datetime
            boot_ts = psutil.boot_time()
            uptime_seconds = datetime.datetime.now().timestamp() - boot_ts
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            parts.append(f"{minutes}m")
            return " ".join(parts)
        except (psutil.Error, OSError):
            return "No disponible"

    @staticmethod
    def _get_network_info() -> dict[str, str]:
        """Obtiene información de las interfaces de red activas."""
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            active = {}
            for iface_name, addr_list in addrs.items():
                iface_stats = stats.get(iface_name)
                if iface_stats and iface_stats.isup:
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            active[iface_name] = addr.address
                            break
            return active
        except (psutil.Error, OSError):
            return {}

    @staticmethod
    def _format_message(info: dict[str, Any]) -> str:
        """Formatea la información del sistema para Telegram."""
        lines = [
            " Información del Sistema",
            "",
            f" OS: {info['sistema_operativo']}",
            f" Versión: {info['version_os']}",
            f" Arquitectura: {info['arquitectura']}",
            f" Procesador: {info['procesador']}",
            f" Máquina: {info['nombre_maquina']}",
            f" Usuario: {info['usuario']}",
            f" Python: {info['python_version']}",
            f" Directorio: {info['directorio_actual']}",
            f" Encendido: {info['boot_time']}",
            f" Uptime: {info['uptime']}",
        ]

        net = info.get("interfaces_red", {})
        if net:
            lines.extend(["", " Red:"])
            for iface, ip in net.items():
                lines.append(f"   {iface}: {ip}")

        return "\n".join(lines)


# ============================================
# AUTO-REGISTRO
# ============================================
get_registry().register(SystemInfoCommand())
