from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import requests

router = APIRouter()

WHATSAPP_BASE_URL = "http://localhost:3000"


class SendMessageRequest(BaseModel):
    number: str
    message: str


class SendBulkRequest(BaseModel):
    numbers: List[str]
    message: str
    delay: int = 3000


@router.get("/status")
def get_status():
    """Verifica status da conexão WhatsApp"""
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2)
        return response.json()
    except:
        return {"status": "error", "error": "Serviço não está rodando"}


@router.get("/info")
def get_info():
    """Obtém informações do usuário conectado"""
    try:
        response = requests.get(f"{WHATSAPP_BASE_URL}/info", timeout=2)
        return response.json()
    except:
        return {"success": False, "error": "Não foi possível obter informações"}


@router.post("/send")
def send_message(request: SendMessageRequest):
    """Envia uma mensagem individual"""
    try:
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send",
            json={"number": request.number, "message": request.message},
            timeout=30
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-bulk")
def send_bulk(request: SendBulkRequest):
    """Envia mensagens em massa"""
    try:
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send-bulk",
            json={
                "numbers": request.numbers,
                "message": request.message,
                "delay": request.delay
            },
            timeout=300
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
