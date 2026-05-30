"""
Rotas para integração com API de Upload de Notas Fiscais
Gerenciamento de links de upload e consulta de status
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import requests
import os
import hmac
from dotenv import load_dotenv
from app.database import get_db_connection
from app.routes._auth_deps import get_current_user

load_dotenv()

router = APIRouter()


def verify_upload_webhook_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Valida a chave partilhada usada pelo serviço externo de upload."""
    expected = os.getenv("API_UPLOAD_KEY", "")
    if not expected or not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="API key inválida")

# Configurações da API de Upload
API_UPLOAD_URL = os.getenv("API_UPLOAD_URL", "https://api.link.dev.br/dvprocessamento/")
API_UPLOAD_KEY = os.getenv("API_UPLOAD_KEY")
if not API_UPLOAD_KEY:
    print("⚠️  API_UPLOAD_KEY não configurada no .env — endpoints de upload ficarão indisponíveis.")

class GerarLinkRequest(BaseModel):
    nome: str
    email: str
    periodo: str  # Formato: MM/YYYY
    valor_total: float
    quantidade_os: int
    lote_id: int
    tipo: str  # 'lote' ou 'montagem'

class ConsultarStatusRequest(BaseModel):
    hash: str

@router.post("/gerar-link")
def gerar_link_upload(request: GerarLinkRequest, current_user: dict = Depends(get_current_user)):
    """
    Gera link de upload na API externa
    
    Retorna:
        {
            "success": true,
            "id_controle": 1,
            "lote_id": 99999,
            "link": "https://api.link.com.br/dvprocessamento/envio-nf/...",
            "hash": "03de0449e11849318f7d67e08377f150",
            "validade_link": "2025-11-12",
            "status": 0,
            "message": "Registro criado com sucesso"
        }
    """
    
    try:
        # Aplicar offset para montadores (evitar conflito de IDs)
        lote_id_api = request.lote_id
        if request.tipo == 'montagem':
            lote_id_api = 876231 + request.lote_id
        
        # Preparar payload para API
        payload = {
            "nome": request.nome,
            "email": request.email,
            "periodo": request.periodo,
            "valor_total": request.valor_total,
            "quantidade_os": request.quantidade_os,
            "data_envio": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "lote_id": lote_id_api,
            "tipo": request.tipo
        }
        
        # Headers da requisição
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
            "X-API-Key": API_UPLOAD_KEY
        }
        
        print(f"\n📤 Enviando para API de Upload:")
        print(f"   URL: {API_UPLOAD_URL}")
        print(f"   Payload: {payload}")
        
        # Fazer requisição
        response = requests.post(
            API_UPLOAD_URL,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False  # SSL ainda não está ativo
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text}")
        
        # Verificar resposta
        if response.status_code in [200, 201]:
            resposta_json = response.json()
            
            if resposta_json.get('success'):
                return resposta_json
            else:
                erro_msg = resposta_json.get('message', 'Erro desconhecido')
                raise HTTPException(status_code=400, detail=f"API retornou erro: {erro_msg}")
        
        elif response.status_code == 409:
            raise HTTPException(status_code=409, detail="Lote já foi enviado anteriormente (duplicado)")
        
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Erro HTTP: {response.text}")
    
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao conectar com a API")
    
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Erro de conexão com a API")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consultar-status")
def consultar_status_upload(request: ConsultarStatusRequest, current_user: dict = Depends(get_current_user)):
    """
    Consulta status de um upload pelo hash
    
    Retorna:
        {
            "success": true,
            "status": 1,  # 0=pendente, 1=enviado, 2=erro
            "nota_fiscal": "arquivo.pdf",
            "data_upload": "2025-11-12T10:30:00",
            "message": "Status consultado"
        }
    """
    
    try:
        # Consultar API
        headers = {
            "Accept": "application/json",
            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
            "X-API-Key": API_UPLOAD_KEY
        }
        
        url = f"{API_UPLOAD_URL}consulta/{request.hash}"
        
        print(f"\n🔍 Consultando status:")
        print(f"   URL: {url}")
        
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            verify=False
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Erro HTTP: {response.text}")
    
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout ao conectar com a API")
    
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Erro de conexão com a API")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{hash}")
def get_status_upload(hash: str, current_user: dict = Depends(get_current_user)):
    """
    Consulta status de um upload pelo hash (via GET)
    """
    return consultar_status_upload(ConsultarStatusRequest(hash=hash), current_user)

@router.post("/webhook/nf-recebida", dependencies=[Depends(verify_upload_webhook_key)])
async def webhook_nf_recebida(data: dict):
    """
    Webhook para receber notificação quando NF for enviada
    
    Payload esperado:
    {
        "lote_id": 123,
        "tipo": "lote" ou "montagem",
        "hash": "abc123",
        "nota_fiscal": "arquivo.pdf",
        "data_upload": "2025-11-12T10:30:00"
    }
    """
    try:
        lote_id = data.get("lote_id")
        tipo = data.get("tipo")
        nota_fiscal = data.get("nota_fiscal")
        hash_upload = data.get("hash")
        
        # ID já vem correto do banco (montadores >= 100000, prestadores < 100000)
        # Não precisa fazer conversão
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Atualizar status no banco
            if tipo == "lote":
                # Buscar tempo de vencimento do prestador
                from datetime import datetime, timedelta
                cursor.execute("""
                    SELECT p.tempo_vencimento_dias 
                    FROM lotes_servico ls
                    JOIN prestadores p ON ls.prestador_id = p.id
                    WHERE ls.id = %s
                """, (lote_id,))
                
                result_tempo = cursor.fetchone()
                dias_vencimento = result_tempo[0] if result_tempo and result_tempo[0] else 30
                data_vencimento = datetime.now() + timedelta(days=dias_vencimento)
                
                cursor.execute("""
                    UPDATE lotes_servico 
                    SET status_api = 1,
                        data_recebimento_nf = NOW(),
                        data_vencimento_pagamento = %s,
                        nota_fiscal_path = %s
                    WHERE id = %s
                    RETURNING prestador_nome, periodo, valor_total
                """, (data_vencimento, nota_fiscal, lote_id))
                
                result = cursor.fetchone()
                if result:
                    nome, periodo, valor = result
                    
                    # Enviar notificação em tempo real
                    from app.routes.notifications import notification_manager
                    await notification_manager.send_notification(
                        tipo="success",
                        titulo="📄 Nota Fiscal Recebida",
                        mensagem=f"{nome} enviou a NF do período {periodo}",
                        dados={
                            "lote_id": lote_id,
                            "tipo": "prestador",
                            "nome": nome,
                            "periodo": periodo,
                            "valor": valor,
                            "nota_fiscal": nota_fiscal
                        }
                    )
            
            elif tipo == "montagem":
                # Buscar tempo de vencimento do montador
                from datetime import datetime, timedelta
                cursor.execute("""
                    SELECT m.tempo_vencimento_dias 
                    FROM envios_montagem em
                    JOIN montadores m ON em.montador_id = m.id
                    WHERE em.id = %s
                """, (lote_id,))
                
                result_tempo = cursor.fetchone()
                dias_vencimento = result_tempo[0] if result_tempo and result_tempo[0] else 30
                data_vencimento = datetime.now() + timedelta(days=dias_vencimento)
                
                cursor.execute("""
                    UPDATE envios_montagem 
                    SET status_api = 1,
                        data_recebimento_nf = NOW(),
                        data_vencimento_pagamento = %s,
                        nota_fiscal_path = %s
                    WHERE id = %s
                    RETURNING montador_nome, periodo, valor_total
                """, (data_vencimento, nota_fiscal, lote_id))
                
                result = cursor.fetchone()
                if result:
                    nome, periodo, valor = result
                    
                    # Enviar notificação em tempo real
                    from app.routes.notifications import notification_manager
                    await notification_manager.send_notification(
                        tipo="success",
                        titulo="📄 Nota Fiscal Recebida",
                        mensagem=f"{nome} enviou a NF do período {periodo}",
                        dados={
                            "lote_id": lote_id,
                            "tipo": "montador",
                            "nome": nome,
                            "periodo": periodo,
                            "valor": valor,
                            "nota_fiscal": nota_fiscal
                        }
                    )
            
            conn.commit()
        
        return {
            "success": True,
            "message": "NF processada e notificação enviada",
            "lote_id": lote_id,
            "tipo": tipo
        }
    
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

