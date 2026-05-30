from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime

router = APIRouter()


class NotaFiscalWebhook(BaseModel):
    lote_id: int
    tipo: str  # 'prestador' ou 'montador'
    nome: str
    data_upload: str

# Lista de conexões WebSocket ativas
active_connections: List[WebSocket] = []

class NotificationManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Nova conexão WebSocket. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Conexão WebSocket fechada. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Envia notificação para todos os clientes conectados"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Erro ao enviar notificação: {e}")
                disconnected.append(connection)
        
        # Remove conexões que falharam
        for conn in disconnected:
            self.disconnect(conn)

    async def send_notification(
        self, 
        tipo: str, 
        titulo: str, 
        mensagem: str, 
        dados: Dict[str, Any] = None
    ):
        """
        Envia uma notificação formatada
        
        Args:
            tipo: 'success', 'info', 'warning', 'error'
            titulo: Título da notificação
            mensagem: Mensagem detalhada
            dados: Dados adicionais (opcional)
        """
        notification = {
            "tipo": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "timestamp": datetime.now().isoformat(),
            "dados": dados or {}
        }
        await self.broadcast(notification)

# Instância global do gerenciador
notification_manager = NotificationManager()

@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await notification_manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão aberta
            data = await websocket.receive_text()
            # Cliente pode enviar "ping" para manter conexão viva
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket)
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
        notification_manager.disconnect(websocket)


@router.post("/webhook/nota-fiscal-recebida")
async def webhook_nota_fiscal_recebida(dados: NotaFiscalWebhook):
    """
    Webhook chamado quando uma nota fiscal é recebida
    Envia notificação WebSocket para todos os clientes conectados
    """
    try:
        await notification_manager.send_notification(
            tipo="success",
            titulo="Nova nota fiscal recebida",
            mensagem=f"{dados.nome} anexou a nota fiscal",
            dados={
                "lote_id": dados.lote_id,
                "tipo": dados.tipo,
                "nome": dados.nome,
                "data_upload": dados.data_upload
            }
        )
        return {"success": True, "message": "Notificação enviada"}
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")
        return {"success": False, "error": str(e)}
