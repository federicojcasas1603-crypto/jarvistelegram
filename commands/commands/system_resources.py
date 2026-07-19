"""
Comando de recursos del sistema en tiempo real.

Retorna métricas dinámicas: uso de CPU, RAM, disco y procesos.
Es de solo lectura y seguro de ejecutar múltiples veces.

Uso desde Telegram: "¿Cuánta RAM tengo libre?" o "¿Cómo va la CPU?"
"""

from __future__ import annotations

import logging
from typing import Any

import psutil

from commands.base import Command, get_registry
from models.command_result import CommandResult

logger = logging.getLogger(__name__)


def _bytes_to_human(num_bytes: float) -> str:
    """
    Convierte bytes a formato legible (KB, MB, GB, TB).

    Args:
        num_bytes: Cantidad de bytes a convertir.

    Returns:
        String con el valor formateado y la unidad apropiada.
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


class SystemResourcesCommand(Command):
    """
    Comando que retorna el uso actual de CPU, RAM y disco.

    Muestra porcentajes y cantidades absolutas de cada recurso,
    además de los 5 procesos que más recursos consumen.
    """

    @property
    def name(self) -> str:
        return "system_resources"

    @property
    def description(self) -> str:
        return "Muestra uso de CPU, RAM y disco en tiempo real"

    def execute(self, params: dict[str, Any]) -> CommandResult:
        """
        Recopila métricas de recursos del sistema.

        Returns:
            CommandResult con datos de CPU, RAM y disco formateados
            para enviar al usuario.
        """
        try:
            resources: dict[str, Any] = {
                "cpu": self._get_cpu_info(),
                "ram": self._get_ram_info(),
                "disks": self._get_disk_info(),
                "top_processes": self._get_top_processes(),
            }

            message = self._format_message(resources)

            logger.info("system_resources ejecutado correctamente")
            return CommandResult.ok(message=message, data=resources)

        except Exception as e:
            error_msg = f"Error al obtener recursos del sistema: {e}"
            logger.exception(error_msg)
            return CommandResult.fail(message=error_msg, error=str(e))

    @staticmethod
    def _get_cpu_info() -> dict[str, Any]:
        """Obtiene información detallada de la CPU."""
        try:
            usage_percent = psutil.cpu_percent(interval=1)
            physical_cores = psutil.cpu_count(logical=False) or 0
            logical_cores = psutil.cpu_count(logical=True) or 0

            freq = psutil.cpu_freq()
            freq_current = f"{freq.current:.0f} MHz" if freq else "No disponible"
            freq_max = f"{freq.max:.0f} MHz" if freq and freq.max else "No disponible"

            return {
                "uso_porcentaje": usage_percent,
                "nucleos_fisicos": physical_cores,
                "nucleos_logicos": logical_cores,
                "frecuencia_actual": freq_current,
                "frecuencia_maxima": freq_max,
            }
        except (psutil.Error, OSError):
            return {"uso_porcentaje": 0, "error": "No se pudo obtener info de CPU"}

    @staticmethod
    def _get_ram_info() -> dict[str, Any]:
        """Obtiene información detallada de la RAM."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total": _bytes_to_human(mem.total),
                "usada": _bytes_to_human(mem.used),
                "disponible": _bytes_to_human(mem.available),
                "uso_porcentaje": mem.percent,
                "swap_total": _bytes_to_human(swap.total),
                "swap_usada": _bytes_to_human(swap.used),
                "swap_porcentaje": swap.percent,
            }
        except (psutil.Error, OSError):
            return {"error": "No se pudo obtener info de RAM"}

    @staticmethod
    def _get_disk_info() -> list[dict[str, Any]]:
        """Obtiene información de todas las particiones principales."""
        disks = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        "dispositivo": partition.device,
                        "montaje": partition.mountpoint,
                        "sistema_archivos": partition.fstype,
                        "total": _bytes_to_human(usage.total),
                        "usado": _bytes_to_human(usage.used),
                        "libre": _bytes_to_human(usage.free),
                        "uso_porcentaje": usage.percent,
                    })
                except (PermissionError, OSError):
                    continue
        except (psutil.Error, OSError):
            pass
        return disks

    @staticmethod
    def _get_top_processes(count: int = 5) -> list[dict[str, Any]]:
        """Obtiene los N procesos que más CPU consumen."""
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    info = proc.info
                    if info["cpu_percent"] is not None:
                        processes.append({
                            "pid": info["pid"],
                            "nombre": info["name"],
                            "cpu": round(info["cpu_percent"], 1),
                            "ram": round(info["memory_percent"] or 0, 1),
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            processes.sort(key=lambda p: p["cpu"], reverse=True)
            return processes[:count]

        except (psutil.Error, OSError):
            return []

    @staticmethod
    def _format_message(resources: dict[str, Any]) -> str:
        """Formatea los recursos del sistema para Telegram."""
        lines = [" Recursos del Sistema", ""]

        # CPU
        cpu = resources.get("cpu", {})
        if "error" not in cpu:
            lines.extend([
                f" CPU: {cpu.get('uso_porcentaje', 0)}%",
                f"   Núcleos: {cpu.get('nucleos_fisicos', 0)} físicos / "
                f"{cpu.get('nucleos_logicos', 0)} lógicos",
                f"   Frecuencia: {cpu.get('frecuencia_actual', 'N/A')} "
                f"(máx: {cpu.get('frecuencia_maxima', 'N/A')})",
            ])
        else:
            lines.append(" CPU: No disponible")

        lines.append("")

        # RAM
        ram = resources.get("ram", {})
        if "error" not in ram:
            lines.extend([
                f" RAM: {ram.get('uso_porcentaje', 0)}%",
                f"   Usada: {ram.get('usada', 'N/A')} / {ram.get('total', 'N/A')}",
                f"   Disponible: {ram.get('disponible', 'N/A')}",
            ])
            if ram.get("swap_total", "0 B") != "0.0 B":
                lines.append(
                    f"   Swap: {ram.get('swap_usada', 'N/A')} / "
                    f"{ram.get('swap_total', 'N/A')} ({ram.get('swap_porcentaje', 0)}%)"
                )
        else:
            lines.append(" RAM: No disponible")

        lines.append("")

        # Discos
        disks = resources.get("disks", [])
        if disks:
            lines.append(" Disco:")
            for disk in disks:
                lines.append(
                    f"   {disk['montaje']} ({disk['dispositivo']}): "
                    f"{disk['uso_porcentaje']}% - "
                    f"{disk['libre']} libres de {disk['total']}"
                )

        # Top procesos
        top = resources.get("top_processes", [])
        if top:
            lines.extend(["", " Top 5 procesos (CPU%):"])
            for i, proc in enumerate(top, 1):
                lines.append(
                    f"   {i}. {proc['nombre'][:25]} - "
                    f"CPU: {proc['cpu']}% | RAM: {proc['ram']}%"
                )

        return "\n".join(lines)


# ============================================
# AUTO-REGISTRO
# ============================================
get_registry().register(SystemResourcesCommand())
