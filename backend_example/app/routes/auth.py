"""
Rotas de Autenticação Microsoft OAuth2
Gerencia autenticação e tokens para Microsoft Graph API usando Device Flow
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from msal import PublicClientApplication
import requests
import os
from datetime import datetime, timedelta
from app.database import get_db_connection
import psycopg2.extras

router = APIRouter()

# Configurações OAuth2 Microsoft (Device Flow - não precisa de Client Secret)
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
# Se TENANT_ID estiver vazio, usar "common" como padrão
if not TENANT_ID or TENANT_ID.strip() == "":
    TENANT_ID = "common"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Send", "User.Read"]

# Inicializar PublicClientApplication (apenas se CLIENT_ID estiver configurado)
pca = None
if CLIENT_ID and CLIENT_ID.strip() != "":
    try:
        pca = PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY)
    except Exception as e:
        print(f"Aviso: Não foi possível inicializar Microsoft Auth: {e}")

# Modelos
class AuthConfig(BaseModel):
    client_id: Optional[str] = None
    has_token: bool
    user_email: Optional[str] = None
    token_expires: Optional[str] = None

class DeviceFlowResponse(BaseModel):
    user_code: str
    device_code: str
    verification_uri: str
    message: str
    expires_in: int
    interval: int

class TokenPollRequest(BaseModel):
    device_code: str

# Cache de device flows ativos (em produção, usar Redis)
device_flows = {}

@router.get("/config")
def get_auth_config():
    """
    Retorna configuração de autenticação atual
    
    Returns:
        - client_id: ID do cliente Microsoft
        - has_token: Se existe token válido
        - user_email: Email do usuário autenticado
        - token_expires: Data de expiração do token
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM microsoft_auth WHERE id = 1")
        auth = cur.fetchone()
        
        has_token = False
        user_email = None
        token_expires = None
        
        if auth and auth.get("access_token"):
            has_token = True
            user_email = auth.get("user_email")
            if auth.get("expires_at"):
                token_expires = auth["expires_at"].isoformat()
        
        return AuthConfig(
            client_id=CLIENT_ID if CLIENT_ID else None,
            has_token=has_token,
            user_email=user_email,
            token_expires=token_expires
        )

@router.post("/start-device-flow")
def start_device_flow():
    """
    Inicia o fluxo de autenticação por dispositivo (Device Flow)
    
    Returns:
        - user_code: Código que o usuário deve digitar
        - verification_uri: URL onde o usuário deve entrar
        - message: Mensagem completa para exibir ao usuário
        - device_code: Código do dispositivo (usado para polling)
        - expires_in: Tempo de validade em segundos
        - interval: Intervalo recomendado entre polls em segundos
    """
    if not CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="CLIENT_ID não configurado. Configure MICROSOFT_CLIENT_ID no .env"
        )
    
    if not pca:
        raise HTTPException(
            status_code=500,
            detail="Microsoft Auth não inicializado. Verifique as configurações."
        )
    
    try:
        # Iniciar device flow
        flow = pca.initiate_device_flow(scopes=SCOPES)
        
        if "error" in flow:
            raise HTTPException(
                status_code=400,
                detail=f"Erro ao iniciar device flow: {flow.get('error_description', flow['error'])}"
            )
        
        # Armazenar device_code temporariamente
        device_code = flow["device_code"]
        device_flows[device_code] = flow
        
        return DeviceFlowResponse(
            user_code=flow["user_code"],
            device_code=device_code,
            verification_uri=flow["verification_uri"],
            message=flow["message"],
            expires_in=flow["expires_in"],
            interval=flow.get("interval", 5)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar autenticação: {str(e)}")

@router.post("/poll-device-flow")
def poll_device_flow(request: TokenPollRequest):
    """
    Verifica se o usuário completou a autenticação (polling)
    
    Args:
        device_code: Código do dispositivo retornado pelo start-device-flow
    
    Returns:
        - success: Se a autenticação foi completada
        - message: Mensagem de status
        - Se success=true, inclui: access_token, user_email, expires_at
    """
    device_code = request.device_code
    
    if device_code not in device_flows:
        raise HTTPException(
            status_code=404,
            detail="Device flow não encontrado ou expirado"
        )
    
    flow = device_flows[device_code]
    
    if not pca:
        raise HTTPException(
            status_code=500,
            detail="Microsoft Auth não inicializado"
        )
    
    try:
        # Tentar adquirir token (sem bloquear, só verifica status)
        # Importante: não passar o flow diretamente para não consumi-lo
        import copy
        flow_copy = copy.deepcopy(flow)
        result = pca.acquire_token_by_device_flow(flow_copy)
        
        # authorization_pending: usuário ainda não completou
        if "error" in result and result["error"] == "authorization_pending":
            return {
                "success": False,
                "message": "Aguardando autenticação do usuário..."
            }
        
        # Erro definitivo
        if "error" in result:
            del device_flows[device_code]
            return {
                "success": False,
                "message": result.get("error_description", result["error"]),
                "error": True
            }
        
        # Sucesso! Salvar tokens
        if "access_token" in result:
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token")
            expires_in = result.get("expires_in", 3600)
            
            # Buscar email do usuário
            user_email = None
            try:
                me_response = requests.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    user_email = user_data.get("userPrincipalName") or user_data.get("mail")
            except:
                pass
            
            # Calcular expiração
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Salvar no banco
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO microsoft_auth (id, access_token, refresh_token, expires_at, user_email)
                    VALUES (1, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        expires_at = EXCLUDED.expires_at,
                        user_email = EXCLUDED.user_email,
                        updated_at = NOW()
                    """,
                    (access_token, refresh_token, expires_at, user_email)
                )
            
            # Remover do cache
            del device_flows[device_code]
            
            return {
                "success": True,
                "message": "Autenticação realizada com sucesso!",
                "access_token": access_token,
                "user_email": user_email,
                "expires_at": expires_at.isoformat()
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar autenticação: {str(e)}")

@router.post("/refresh")
def refresh_token():
    """
    Renova o access token usando o refresh token
    
    Returns:
        - message: Confirmação de renovação
        - expires_at: Nova data de expiração
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM microsoft_auth WHERE id = 1")
        auth = cur.fetchone()
        
        if not auth or not auth.get("refresh_token"):
            raise HTTPException(
                status_code=404,
                detail="Nenhum refresh token encontrado. Faça login novamente."
            )
        
        refresh_token = auth["refresh_token"]
        
        try:
            # Tentar renovar usando MSAL
            accounts = pca.get_accounts()
            
            if accounts:
                # Tentar silent token acquisition
                result = pca.acquire_token_silent(SCOPES, account=accounts[0])
                
                if result and "access_token" in result:
                    access_token = result["access_token"]
                    new_refresh_token = result.get("refresh_token", refresh_token)
                    expires_in = result.get("expires_in", 3600)
                    expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Atualizar no banco
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE microsoft_auth
                        SET access_token = %s,
                            refresh_token = %s,
                            expires_at = %s,
                            updated_at = NOW()
                        WHERE id = 1
                        """,
                        (access_token, new_refresh_token, expires_at)
                    )
                    
                    return {
                        "message": "Token renovado com sucesso",
                        "expires_at": expires_at.isoformat()
                    }
            
            raise HTTPException(status_code=401, detail="Não foi possível renovar o token")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao renovar token: {str(e)}"
            )

@router.post("/logout")
def logout():
    """
    Remove autenticação (limpa tokens do banco)
    
    Returns:
        - message: Confirmação de logout
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE microsoft_auth
            SET access_token = NULL,
                refresh_token = NULL,
                expires_at = NULL,
                user_email = NULL,
                updated_at = NOW()
            WHERE id = 1
            """
        )
    
    return {"message": "Logout realizado com sucesso"}

# ==================== FUNÇÃO AUXILIAR PARA OUTROS MÓDULOS ====================

def get_valid_access_token() -> str:
    """
    Retorna um access token válido, renovando automaticamente se necessário.
    Usada por outros módulos (ex: relatorios.py) para enviar emails.
    
    Returns:
        str: Access token válido
    
    Raises:
        HTTPException: Se não houver token ou não for possível renová-lo
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM microsoft_auth WHERE id = 1")
        auth = cur.fetchone()
        
        if not auth or not auth.get("access_token"):
            raise HTTPException(
                status_code=401,
                detail="Nenhuma autenticação encontrada. Configure a autenticação Microsoft em Configurar Email."
            )
        
        access_token = auth["access_token"]
        expires_at = auth.get("expires_at")
        
        # Se o token ainda é válido (com margem de 5 minutos), retornar direto
        if expires_at and expires_at > datetime.now() + timedelta(minutes=5):
            return access_token
        
        # Token expirado ou próximo de expirar, tentar renovar
        if auth.get("refresh_token"):
            try:
                accounts = pca.get_accounts()
                
                if accounts:
                    result = pca.acquire_token_silent(SCOPES, account=accounts[0])
                    
                    if result and "access_token" in result:
                        new_access_token = result["access_token"]
                        new_refresh_token = result.get("refresh_token", auth["refresh_token"])
                        expires_in = result.get("expires_in", 3600)
                        new_expires_at = datetime.now() + timedelta(seconds=expires_in)
                        
                        # Atualizar no banco
                        cur = conn.cursor()
                        cur.execute(
                            """
                            UPDATE microsoft_auth
                            SET access_token = %s,
                                refresh_token = %s,
                                expires_at = %s,
                                updated_at = NOW()
                            WHERE id = 1
                            """,
                            (new_access_token, new_refresh_token, new_expires_at)
                        )
                        
                        return new_access_token
            except:
                pass
        
        # Se chegou aqui, o token está expirado e não foi possível renovar
        raise HTTPException(
            status_code=401,
            detail="Token expirado. Faça login novamente em Configurar Email."
        )
