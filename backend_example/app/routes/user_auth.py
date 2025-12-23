"""
Rotas de Autenticação de Usuários
Sistema de login/logout com JWT
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from app.database import get_db_connection

router = APIRouter()
security = HTTPBearer()

# Configurações JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "BracoAISecretKey2025ProdServer")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 horas

# Contexto de criptografia para senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelos
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "user"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decodifica e valida token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency para obter usuário atual do token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, full_name, role, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        if not user[5]:  # is_active
            raise HTTPException(status_code=401, detail="Usuário desativado")
        
        return {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "full_name": user[3],
            "role": user[4]
        }


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency que requer que o usuário seja admin"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Apenas administradores podem realizar esta ação."
        )
    return current_user


@router.post("/login")
def login(request: LoginRequest):
    """
    Realiza login e retorna token JWT
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, username, email, full_name, role, password_hash, is_active 
               FROM users WHERE username = %s""",
            (request.username,)
        )
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Usuário ou senha incorretos"
            )
        
        user_id, username, email, full_name, role, password_hash, is_active = user
        
        if not is_active:
            raise HTTPException(
                status_code=401,
                detail="Usuário desativado. Entre em contato com o administrador."
            )
        
        if not verify_password(request.password, password_hash):
            raise HTTPException(
                status_code=401,
                detail="Usuário ou senha incorretos"
            )
        
        # Atualizar último login
        cur.execute(
            "UPDATE users SET last_login = %s WHERE id = %s",
            (datetime.utcnow(), user_id)
        )
        
        # Criar token
        access_token = create_access_token(
            data={"sub": str(user_id), "username": username, "role": role}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "role": role
            }
        }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna informações do usuário logado
    """
    return current_user


@router.post("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica se o token é válido e retorna dados do usuário
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, full_name, role, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        user = cur.fetchone()
        
        if not user or not user[5]:
            raise HTTPException(status_code=401, detail="Usuário inválido ou desativado")
        
        return {
            "valid": True,
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "full_name": user[3],
                "role": user[4]
            }
        }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Altera a senha do usuário logado
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Verificar senha atual
        cur.execute(
            "SELECT password_hash FROM users WHERE id = %s",
            (current_user["id"],)
        )
        result = cur.fetchone()
        
        if not result or not verify_password(request.current_password, result[0]):
            raise HTTPException(
                status_code=400,
                detail="Senha atual incorreta"
            )
        
        # Atualizar senha
        new_hash = get_password_hash(request.new_password)
        cur.execute(
            "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s",
            (new_hash, datetime.utcnow(), current_user["id"])
        )
        
        return {"message": "Senha alterada com sucesso"}


@router.get("/users")
async def list_users(current_user: dict = Depends(require_admin)):
    """
    Lista todos os usuários (apenas admin)
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, username, email, full_name, role, is_active, created_at, last_login 
               FROM users ORDER BY created_at DESC"""
        )
        users = cur.fetchall()
        
        return [
            {
                "id": u[0],
                "username": u[1],
                "email": u[2],
                "full_name": u[3],
                "role": u[4],
                "is_active": u[5],
                "created_at": u[6].isoformat() if u[6] else None,
                "last_login": u[7].isoformat() if u[7] else None
            }
            for u in users
        ]


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Cria novo usuário (apenas admin)
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Verificar se username já existe
        cur.execute("SELECT id FROM users WHERE username = %s", (request.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username já existe")
        
        # Criar usuário
        password_hash = get_password_hash(request.password)
        cur.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (request.username, request.email, password_hash, request.full_name, request.role)
        )
        user_id = cur.fetchone()[0]
        
        return {
            "message": "Usuário criado com sucesso",
            "user_id": user_id
        }


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """
    Ativa/desativa usuário (apenas admin)
    """
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET is_active = NOT is_active, updated_at = %s WHERE id = %s RETURNING is_active",
            (datetime.utcnow(), user_id)
        )
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return {
            "message": f"Usuário {'ativado' if result[0] else 'desativado'} com sucesso",
            "is_active": result[0]
        }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """
    Remove usuário (apenas admin)
    """
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Você não pode remover sua própria conta")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return {"message": "Usuário removido com sucesso"}
