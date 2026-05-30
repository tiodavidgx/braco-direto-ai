"""
Rotas de Autenticação do Sistema
Endpoints para login e gerenciamento de sessão de usuários
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2.extras
import hashlib
import hmac
import jwt
import os
from datetime import datetime, timedelta
from app.database import get_db_connection
from app.utils.rate_limit import limiter

router = APIRouter()
security = HTTPBearer()

# Chave secreta para JWT (em produção, usar variável de ambiente)
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET/SECRET_KEY não definida no ambiente")
JWT_ALGORITHM = "HS256"
# Padrão: 1 ano (8760h). Sessão fica viva até o usuário fazer logout explícito,
# trocar a senha, ser desativado, ou ficar 1 ano sem abrir o sistema.
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8760"))


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    recaptcha_token: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nome: str
    telefone: Optional[str] = None
    role: str = "operador"  # admin ou operador
    pode_pre_cadastro: bool = False
    pode_revisao_cadastro: bool = False


def hash_password(password: str) -> str:
    """Hash de senha com SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return hash_password(password) == password_hash


def create_access_token(user_id: int, email: str) -> str:
    """Cria token JWT"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def _verify_recaptcha(recaptcha_token: str) -> bool:
    """Verifica token reCAPTCHA v3 com o Google"""
    import requests
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT recaptcha_enabled, recaptcha_secret_key, recaptcha_score_minimo
                FROM integracoes_config WHERE id = 1
            """)
            result = cur.fetchone()
            if not result or not result[0]:
                return True  # reCAPTCHA desabilitado, permite
            
            secret_key = result[1]
            score_minimo = float(result[2]) if result[2] else 0.5
            
            if not secret_key:
                return True  # Sem secret key configurada, permite
            
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret_key, "response": recaptcha_token},
                timeout=5,
            )
            data = response.json()
            
            if not data.get("success"):
                return False
            if data.get("score", 0) < score_minimo:
                return False
            return True
    except Exception as e:
        print(f"Erro ao verificar reCAPTCHA: {e}")
        return True  # Em caso de erro, não bloqueia


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency para obter usuário atual do token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, email, nome, telefone, ativo, role, pode_pre_cadastro, pode_revisao_cadastro, crm_solicitante, crm_analista, acesso_montagem FROM users WHERE id = %s",
            (payload["user_id"],)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        if not user["ativo"]:
            raise HTTPException(status_code=401, detail="Usuário desativado")
        
        return dict(user)


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency que exige role admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem acessar este recurso.")
    return current_user


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest):
    """
    Realiza login e retorna token JWT
    """
    # Verificar reCAPTCHA se habilitado
    if body.recaptcha_token:
        if not _verify_recaptcha(body.recaptcha_token):
            raise HTTPException(status_code=403, detail="Verificação reCAPTCHA falhou. Tente novamente.")
    else:
        # Verificar se reCAPTCHA está habilitado (se sim, token é obrigatório)
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT recaptcha_enabled FROM integracoes_config WHERE id = 1")
                result = cur.fetchone()
                if result and result[0]:
                    raise HTTPException(status_code=403, detail="Verificação reCAPTCHA necessária")
        except HTTPException:
            raise
        except Exception:
            pass  # Se tabela não existe, ignora

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar usuário por email
        cur.execute(
            "SELECT id, email, password_hash, nome, telefone, ativo, role, pode_pre_cadastro, pode_revisao_cadastro, crm_solicitante, crm_analista, acesso_montagem FROM users WHERE email = %s",
            (body.email,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")
        
        if not user["ativo"]:
            raise HTTPException(status_code=401, detail="Usuário desativado")
        
        if not verify_password(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")
        
        # Criar token
        access_token = create_access_token(user["id"], user["email"])
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "nome": user["nome"],
                "telefone": user.get("telefone"),
                "role": user.get("role", "operador"),
                "pode_pre_cadastro": user.get("pode_pre_cadastro", False),
                "pode_revisao_cadastro": user.get("pode_revisao_cadastro", False),
                "crm_solicitante": user.get("crm_solicitante", False),
                "crm_analista": user.get("crm_analista", False),
                "acesso_montagem": user.get("acesso_montagem", False)
            }
        }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna dados do usuário logado
    """
    return current_user


@router.post("/refresh")
def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Renova o token JWT do usuário autenticado.
    Usado pelo frontend para manter a sessão viva sem exigir relogin.
    """
    access_token = create_access_token(current_user["id"], current_user["email"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users")
def create_user(request: UserCreate, current_user: dict = Depends(require_admin)):
    """
    Cria novo usuário (requer autenticação de admin)
    """
    # Validar role
    if request.role not in ["admin", "operador", "motorista"]:
        raise HTTPException(status_code=400, detail="Role deve ser 'admin', 'operador' ou 'motorista'")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se email já existe
        cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        
        # Criar usuário
        password_hash = hash_password(request.password)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, nome, telefone, role, pode_pre_cadastro, pode_revisao_cadastro)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, nome, telefone, ativo, role, created_at, pode_pre_cadastro, pode_revisao_cadastro
            """,
            (request.email, password_hash, request.nome, request.telefone, request.role, request.pode_pre_cadastro, request.pode_revisao_cadastro)
        )
        user = cur.fetchone()
        conn.commit()
        
        return dict(user)


@router.post("/setup-admin")
def setup_admin(x_setup_token: Optional[str] = Header(None, alias="X-Setup-Token")):
    """
    Cria usuário admin inicial.

    Proteções:
    - Exige token partilhado via header ``X-Setup-Token`` que corresponda a ``SETUP_ADMIN_TOKEN`` no .env.
    - Se a variável não estiver definida, o endpoint fica desabilitado.
    - Continua bloqueando se já existir qualquer usuário.
    """
    expected_token = os.getenv("SETUP_ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=404, detail="Endpoint desabilitado")
    if not x_setup_token or not hmac.compare_digest(x_setup_token, expected_token):
        raise HTTPException(status_code=403, detail="Setup token inválido")

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Verificar se já existem usuários
        cur.execute("SELECT COUNT(*) as count FROM users")
        count = cur.fetchone()["count"]

        if count > 0:
            raise HTTPException(status_code=400, detail="Já existem usuários cadastrados")

        admin_email = os.getenv("SETUP_ADMIN_EMAIL") or "admin@bracodireto.com"
        admin_password = os.getenv("SETUP_ADMIN_PASSWORD")
        if not admin_password or len(admin_password) < 12:
            raise HTTPException(
                status_code=500,
                detail="Configure SETUP_ADMIN_PASSWORD (>=12 caracteres) no .env",
            )

        password_hash = hash_password(admin_password)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, nome, role)
            VALUES (%s, %s, %s, 'admin')
            RETURNING id, email, nome, ativo, created_at
            """,
            (admin_email, password_hash, "Administrador"),
        )
        user = cur.fetchone()
        conn.commit()

        return {
            "message": "Usuário admin criado com sucesso",
            "user": dict(user),
        }


@router.get("/users")
def list_users(current_user: dict = Depends(require_admin)):
    """
    Lista todos os usuários (requer autenticação de admin)
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, email, nome, telefone, ativo, role, created_at, pode_pre_cadastro, pode_revisao_cadastro, crm_solicitante, crm_analista, acesso_montagem 
            FROM users 
            ORDER BY created_at DESC
        """)
        users = cur.fetchall()
        return [dict(u) for u in users]


@router.put("/users/{user_id}/status")
def update_user_status(user_id: int, data: dict, current_user: dict = Depends(require_admin)):
    """
    Ativa/desativa um usuário (requer admin)
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        ativo = data.get("ativo", True)
        cur.execute(
            "UPDATE users SET ativo = %s WHERE id = %s RETURNING id, email, nome, ativo",
            (ativo, user_id)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return dict(user)


@router.put("/users/{user_id}/password")
def update_user_password(user_id: int, data: dict, current_user: dict = Depends(get_current_user)):
    """
    Altera a senha de um usuário.

    Regras:
    - Admins podem trocar a senha de qualquer usuário.
    - Usuários comuns só podem trocar a própria senha e devem informar ``current_password``.
    """
    is_admin = current_user.get("role") == "admin"
    is_self = current_user.get("id") == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Acesso negado")

    password = data.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Senha é obrigatória")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 8 caracteres")

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Se não for admin, exigir senha atual
        if not is_admin:
            current_password = data.get("current_password")
            if not current_password:
                raise HTTPException(status_code=400, detail="current_password é obrigatório")
            cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row or not verify_password(current_password, row["password_hash"]):
                raise HTTPException(status_code=403, detail="Senha atual incorreta")

        password_hash = hash_password(password)
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s RETURNING id",
            (password_hash, user_id)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return {"success": True, "message": "Senha alterada com sucesso"}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, data: dict, current_user: dict = Depends(require_admin)):
    """
    Altera o role de um usuário (requer admin)
    """
    role = data.get("role")
    if role not in ["admin", "operador", "motorista"]:
        raise HTTPException(status_code=400, detail="Role deve ser 'admin', 'operador' ou 'motorista'")
    
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Você não pode alterar seu próprio role")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute(
            "UPDATE users SET role = %s WHERE id = %s RETURNING id, email, nome, ativo, role",
            (role, user_id)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return dict(user)


@router.put("/users/{user_id}/permissoes")
def update_user_permissoes(user_id: int, data: dict, current_user: dict = Depends(require_admin)):
    """
    Altera as permissões de pré-cadastro de um usuário (requer admin)
    """
    pode_pre_cadastro = data.get("pode_pre_cadastro", False)
    pode_revisao_cadastro = data.get("pode_revisao_cadastro", False)
    crm_solicitante = data.get("crm_solicitante", False)
    crm_analista = data.get("crm_analista", False)
    acesso_montagem = data.get("acesso_montagem", False)
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute(
            """UPDATE users 
               SET pode_pre_cadastro = %s, pode_revisao_cadastro = %s,
                   crm_solicitante = %s, crm_analista = %s, acesso_montagem = %s
               WHERE id = %s 
               RETURNING id, email, nome, telefone, ativo, role, pode_pre_cadastro, pode_revisao_cadastro, crm_solicitante, crm_analista, acesso_montagem""",
            (pode_pre_cadastro, pode_revisao_cadastro, crm_solicitante, crm_analista, acesso_montagem, user_id)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return dict(user)


@router.put("/users/{user_id}/telefone")
def update_user_telefone(user_id: int, data: dict, current_user: dict = Depends(require_admin)):
    """
    Altera o telefone de um usuário (requer admin)
    """
    telefone = data.get("telefone")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute(
            """UPDATE users 
               SET telefone = %s 
               WHERE id = %s 
               RETURNING id, email, nome, telefone, ativo, role, pode_pre_cadastro, pode_revisao_cadastro""",
            (telefone, user_id)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return dict(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    """
    Exclui um usuário (requer admin)
    """
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Você não pode excluir seu próprio usuário")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        conn.commit()
        return {"success": True, "message": "Usuário excluído com sucesso"}