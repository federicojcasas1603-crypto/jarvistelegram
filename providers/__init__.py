"""
Paquete de proveedores de inteligencia artificial.

Cada proveedor implementa la interfaz base.AIProvider y se puede
intercambiar sin modificar el resto del sistema.

Proveedores disponibles:
    - Gemini: Google Gemini API (implementado)
    - OpenAI: Stub preparado (futuro)
    - Ollama: Stub preparado (futuro)

Uso:
    from providers import get_provider
    provider = get_provider("gemini")
    action = await provider.generate_action(context)
"""

from providers.base import AIProvider
from providers.gemini import GeminiProvider

__all__ = ["AIProvider", "GeminiProvider"]