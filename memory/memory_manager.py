"""
Sistema de memoria a largo plazo basado en archivos JSON.

Permite guardar y recuperar pares clave-valor que persisten entre sesiones.
Los datos se guardan en data/memory.json.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")


def _load_memory() -> dict[str, Any]:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Archivo de memoria corrupto, creando uno nuevo.")
    return {}


def _save_memory(data: dict[str, Any]) -> None:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save(key: str, value: str) -> None:
    memory = _load_memory()
    memory[key.lower().strip()] = value
    _save_memory(memory)


def recall(key: str) -> str | None:
    memory = _load_memory()
    return memory.get(key.lower().strip())


def get_all() -> dict[str, str]:
    return _load_memory()
