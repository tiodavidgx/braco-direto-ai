"""
Cliente HTTP para o microsserviço WhatsApp (Node/Baileys).

Centraliza a URL base e injeta o cabeçalho ``X-Internal-Token`` em todas as
chamadas para evitar acesso não autenticado ao serviço interno.
"""
import os
import requests

WA_BASE_URL = os.getenv("WHATSAPP_BASE_URL", "http://localhost:3000")
_WA_TOKEN = os.getenv("WHATSAPP_INTERNAL_TOKEN", "")

# Exposto para compatibilidade com módulos que já referenciam WA_HEADERS.
WA_HEADERS = {"X-Internal-Token": _WA_TOKEN}


def _merge_headers(extra):
    h = dict(WA_HEADERS)
    if extra:
        h.update(extra)
    return h


def wa_get(path: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.pop("headers", None))
    return requests.get(f"{WA_BASE_URL}{path}", **kwargs)


def wa_post(path: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.pop("headers", None))
    return requests.post(f"{WA_BASE_URL}{path}", **kwargs)
