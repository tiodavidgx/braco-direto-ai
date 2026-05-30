"""
Dependências de autenticação compartilhadas.

Reexporta as dependências definidas em ``sistema_auth`` para que outros routers
possam aplicar proteção sem criar dependências circulares.
"""

from app.routes.sistema_auth import get_current_user, require_admin

__all__ = ["get_current_user", "require_admin"]
