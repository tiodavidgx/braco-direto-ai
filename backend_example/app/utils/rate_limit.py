"""
Rate limiting global usando slowapi.

Exporta uma instância ``limiter`` que é anexada ao app em ``main.py`` e
pode ser usada como decorator nos endpoints sensíveis.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Chave baseada no IP do cliente (atrás do Nginx usa X-Forwarded-For)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
