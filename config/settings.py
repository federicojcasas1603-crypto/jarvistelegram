"""
Módulo de configuración centralizada.

Responsabilidades:
    1. Cargar variables de entorno desde el archivo .env.
    2. Validar que todas las variables obligatorias estén presentes.
    3. Exponer una instancia inmutable de Config con valores tipados.

Decisiones de diseño:
    - Se usa dataclass con frozen=True para que la configuración sea inmutable
      una vez cargada. Esto previene modificaciones accidentales en runtime.
    - Se valida temprano (al inicio del programa) para fallar rápido si falta
      alguna variable crítica.
    - Los valores opcionales tienen defaults sensatos que funcionan sin
      configuración adicional.
"""

import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """
    Configuración inmutable del sistema.

    Todos los campos son obligatorios excepto los marcados con default.
    Una vez creada esta instancia, no se puede modificar (frozen=True).

    Attributes:
        telegram_token: Token de autenticación del bot de Telegram.
        gemini_api_key: Clave de API de Google Gemini.
        owner_id: ID de Telegram del propietario. None = sin restricción.
        log_level: Nivel de severidad para el sistema de logs.
        max_memory_messages: Cuántos mensajes conservar en memoria a corto plazo.
        screenshots_dir: Ruta donde almacenar capturas de pantalla temporales.
        memory_dir: Ruta donde almacenar la memoria persistente.
        logs_dir: Ruta donde almacenar los archivos de log.
    """

    telegram_token: str
    gemini_api_key: str
    owner_id: int | None = None
    log_level: str = "INFO"
    max_memory_messages: int = 50
    screenshots_dir: str = "data/screenshots"
    memory_dir: str = "data/memory"
    logs_dir: str = "logs"


def _validate_env_vars() -> None:
    """
    Verifica que las variables de entorno obligatorias existan.

    Si falta alguna variable crítica, imprime un mensaje de error claro
    y termina la ejecución del programa con código de error 1.

    Raises:
        No lanza excepciones; termina el proceso directamente.
    """
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Token de Telegram. Obtenerlo de @BotFather.",
        "GEMINI_API_KEY": "Clave de API de Gemini. Obtenerla de https://aistudio.google.com/apikey",
    }

    missing = []

    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value or value.strip() == "":
            missing.append(f"  - {var_name}: {description}")

    if missing:
        error_message = (
            "\n========================================\n"
            "  ERROR: Variables de entorno faltantes\n"
            "========================================\n\n"
            "Las siguientes variables obligatorias no están definidas "
            "en el archivo .env:\n\n"
            + "\n".join(missing)
            + "\n\nSolución:\n"
            "  1. Copia .env.example como .env\n"
            "  2. Rellena los valores requeridos\n"
            "  3. Vuelve a ejecutar el programa\n"
            "========================================\n"
        )
        print(error_message, file=sys.stderr)
        sys.exit(1)


def _parse_owner_id(raw_value: str | None) -> int | None:
    """
    Convierte el OWNER_TELEGRAM_ID de string a entero.

    Args:
        raw_value: Valor crudo de la variable de entorno.

    Returns:
        ID como entero, o None si no está definido.

    Raises:
        ValueError: Si el valor no es un número entero válido.
    """
    if raw_value is None or raw_value.strip() == "":
        return None

    try:
        return int(raw_value.strip())
    except ValueError:
        print(
            f"\nERROR: OWNER_TELEGRAM_ID debe ser un número entero. "
            f"Valor recibido: '{raw_value}'\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _ensure_directories(config: Config) -> None:
    """
    Crea los directorios necesarios si no existen.

    Los directorios de logs, screenshots y memoria deben existir antes
    de que el programa intente escribir en ellos.

    Args:
        config: Instancia de configuración con las rutas a verificar.
    """
    directories = [
        config.logs_dir,
        config.screenshots_dir,
        config.memory_dir,
    ]

    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)


def load_config() -> Config:
    """
    Función principal de carga de configuración.

    Flujo de ejecución:
        1. Carga el archivo .env usando python-dotenv.
        2. Valida que todas las variables obligatorias existan.
        3. Parsea y convierte los valores a sus tipos correctos.
        4. Crea los directorios necesarios.
        5. Retorna una instancia inmutable de Config.

    Returns:
        Instancia de Config con toda la configuración validada y lista para usar.

    Example:
        config = load_config()
        print(config.telegram_token)  # '123456:ABC...'
    """
    # Paso 1: Cargar .env (no sobreescribe variables del sistema)
    load_dotenv(override=False)

    # Paso 2: Validar variables obligatorias
    _validate_env_vars()

    # Paso 3: Parsear valores
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    owner_id = _parse_owner_id(os.getenv("OWNER_TELEGRAM_ID"))
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # Validar log_level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in valid_levels:
        print(
            f"\nWARNING: LOG_LEVEL '{log_level}' no es válido. "
            f"Valores permitidos: {', '.join(valid_levels)}. "
            f"Usando INFO por defecto.\n",
            file=sys.stderr,
        )
        log_level = "INFO"

    # Parsear max_memory_messages con validación
    raw_max_messages = os.getenv("MAX_MEMORY_MESSAGES", "50").strip()
    try:
        max_memory_messages = int(raw_max_messages)
        if max_memory_messages < 5:
            max_memory_messages = 5
        elif max_memory_messages > 200:
            max_memory_messages = 200
    except ValueError:
        max_memory_messages = 50

    # Paso 4: Construir configuración
    config = Config(
        telegram_token=telegram_token,
        gemini_api_key=gemini_api_key,
        owner_id=owner_id,
        log_level=log_level,
        max_memory_messages=max_memory_messages,
        screenshots_dir=os.getenv("SCREENSHOTS_DIR", "data/screenshots").strip(),
        memory_dir=os.getenv("MEMORY_DIR", "data/memory").strip(),
        logs_dir=os.getenv("LOGS_DIR", "logs").strip(),
    )

    # Paso 5: Crear directorios necesarios
    _ensure_directories(config)

    return config