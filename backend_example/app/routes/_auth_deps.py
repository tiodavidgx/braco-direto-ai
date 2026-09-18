"""
Dependências de autenticação compartilhadas.

Reexporta as dependências definidas em ``sistema_auth`` para que outros routers
possam aplicar proteção sem criar dependências circulares.
"""

from app.routes.sistema_auth import get_current_user, get_current_user_or_internal, require_admin

__all__ = ["get_current_user", "get_current_user_or_internal", "require_admin"]
