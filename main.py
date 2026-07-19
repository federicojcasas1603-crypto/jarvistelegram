"""
Punto de entrada de Jarvis Telegram.

Este archivo es el que se ejecuta para iniciar el asistente.
Responsabilidades:
    1. Configurar el sistema de logging.
    2. Cargar la configuración desde .env.
    3. Inicializar el motor (IA + comandos + seguridad).
    4. Crear y arrancar el bot de Telegram.
    5. Mantener la aplicación activa hasta que se detenga.

Uso:
    python main.py

    O con entorno virtual:
    .venv/Scripts/activate
    python main.py
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path para imports
PROJECT_DIR = Path(__file__).parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def setup_logging(log_level: str) -> None:
    """
    Configura el sistema de logging de la aplicación.

    Formato: [FECHA] [HORA] [NIVEL] [MÓDULO] mensaje
    Los logs se guardan en archivos rotativos en la carpeta logs/
    y también se muestran en consola.

    Args:
        log_level: Nivel de severidad (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    log_format = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configuración raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler de archivo (solo si existe la carpeta de logs)
    logs_dir = PROJECT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(
        logs_dir / "jarvis.log",
        encoding="utf-8",
        mode="a",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Reducir ruido de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configurado. Nivel: %s", log_level)


async def main() -> None:
    """
    Función principal asíncrona.

    Orquesta el ciclo de vida completo de la aplicación:
        1. Configurar logging
        2. Cargar configuración
        3. Crear e inicializar el motor
        4. Crear y arrancar el bot
        5. Esperar hasta que se detenga (Ctrl+C o señal de sistema)
    """
    # Paso 1: Configurar logging con nivel por defecto antes de cargar config
    setup_logging("INFO")

    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("  JARVIS TELEGRAM - Iniciando")
    logger.info("=" * 50)

    # Paso 2: Cargar configuración
    try:
        from config import load_config
        config = load_config()
        # Reconfigurar logging con el nivel del .env
        setup_logging(config.log_level)
        logger.info("Configuración cargada correctamente.")
    except SystemExit:
        logger.error("No se pudo cargar la configuración. Saliendo.")
        return
    except Exception as e:
        logger.exception("Error inesperado al cargar configuración: %s", e)
        return

    # Paso 3: Crear e inicializar el motor
    try:
        from core.engine import Engine
        engine = Engine(config)
        await engine.initialize()
        logger.info("Motor inicializado correctamente.")
    except Exception as e:
        logger.exception("Error al inicializar el motor: %s", e)
        return

    # Paso 4: Crear y configurar el bot
    try:
        from bot import JarvisBot
        from bot.handlers import configure_handlers

        bot = JarvisBot(
            token=config.telegram_token,
            owner_id=config.owner_id,
        )

        # Conectar el motor con los handlers del bot
        configure_handlers(
            message_processor=engine.process_message,
            owner_id=config.owner_id,
        )

        logger.info("Bot configurado correctamente.")
    except Exception as e:
        logger.exception("Error al configurar el bot: %s", e)
        return

    # Paso 5: Arrancar el bot y mantener activo
    try:
        await bot.start()
        logger.info("Jarvis está listo y escuchando mensajes.")
        logger.info("Presiona Ctrl+C para detener.")

        # Esperar indefinidamente hasta que se reciba una señal de interrupción
        stop_event = asyncio.Event()

        # Manejar señales del sistema (Ctrl+C, cierre de ventana)
        loop = asyncio.get_running_loop()

        def _signal_handler() -> None:
            logger.info("Señal de interrupción recibida.")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                # Windows no soporta add_signal_handler para todas las señales
                pass

        # También intentar con signal.signal como fallback para Windows
        try:
            signal.signal(signal.SIGINT, lambda s, f: _signal_handler())
            signal.signal(signal.SIGTERM, lambda s, f: _signal_handler())
        except (OSError, ValueError):
            pass

        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("Interrupción por teclado.")
    except Exception as e:
        logger.exception("Error durante la ejecución: %s", e)
    finally:
        # Apagar limpiamente
        logger.info("Apagando Jarvis...")
        await bot.stop()
        await engine.shutdown()
        logger.info("Jarvis detenido correctamente. ¡Hasta luego!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarvis detenido.")
    except Exception as e:
        print(f"\nError fatal: {e}")
        sys.exit(1)