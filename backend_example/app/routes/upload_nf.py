"""
Rotas para sistema interno de upload de Notas Fiscais
Página pública (sem autenticação) para prestadores/montadores enviarem NF
"""

import os
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.database import get_db_connection

router = APIRouter()
logger = logging.getLogger('UploadNF')

# Configurações
UPLOAD_DIR = "uploads/notas_fiscais"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.xml', '.jpg', '.jpeg', '.png'}
DIAS_VALIDADE_LINK = 30


class UploadInfo(BaseModel):
    """Informações do upload para exibir na página"""
    hash: str
    tipo: str
    nome: str
    email: Optional[str]
    lote_id: Optional[int]
    envio_id: Optional[int]
    periodo: str
    valor_total: float
    quantidade_os: int
    status: int
    status_descricao: str
    data_expiracao: str
    dias_restantes: int
    arquivos_enviados: List[dict]


class UploadResponse(BaseModel):
    success: bool
    message: str
    arquivos: Optional[List[dict]] = None


def gerar_hash_unico() -> str:
    """Gera hash único para o link de upload"""
    timestamp = datetime.now().timestamp()
    random_part = uuid.uuid4().hex
    raw = f"{timestamp}-{random_part}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def validar_arquivo(arquivo: UploadFile) -> tuple[bool, str]:
    """Valida extensão e tamanho do arquivo"""
    if not arquivo.filename:
        return False, "Nome do arquivo não informado"
    
    ext = os.path.splitext(arquivo.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão {ext} não permitida. Use: PDF, XML, JPG, PNG"
    
    return True, "OK"


def get_status_descricao(status: int, expirado: bool) -> str:
    """Retorna descrição do status"""
    if expirado:
        return "Link expirado"
    return {
        0: "Aguardando envio",
        1: "Nota fiscal recebida",
        2: "Link expirado"
    }.get(status, "Desconhecido")


# ===== ENDPOINTS PÚBLICOS (SEM AUTH) =====

@router.get("/info/{hash}")
async def get_upload_info(hash: str):
    """
    Retorna informações do upload para exibir na página pública
    Endpoint público - não requer autenticação
    """
    try:
        with get_db_connection() as conn:
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Buscar upload pelo hash
            cur.execute("""
                SELECT 
                    u.id,
                    u.hash,
                    u.tipo,
                    u.lote_id,
                    u.envio_montagem_id,
                    u.status,
                    u.data_criacao,
                    u.data_expiracao,
                    u.data_upload
                FROM uploads_nf u
                WHERE u.hash = %s
            """, (hash,))
            
            upload = cur.fetchone()
            
            if not upload:
                raise HTTPException(status_code=404, detail="Link não encontrado")
            
            # Verificar se expirou
            agora = datetime.now()
            expirado = upload['data_expiracao'] < agora
            dias_restantes = max(0, (upload['data_expiracao'] - agora).days)
            
            if expirado and upload['status'] == 0:
                # Atualizar status para expirado
                cur.execute("UPDATE uploads_nf SET status = 2 WHERE id = %s", (upload['id'],))
                conn.commit()
                upload['status'] = 2
            
            # Buscar dados do prestador ou montador
            if upload['tipo'] == 'prestador' and upload['lote_id']:
                cur.execute("""
                    SELECT 
                        l.prestador_nome as nome,
                        p.email,
                        l.id as lote_id,
                        l.periodo,
                        l.valor_total,
                        l.quantidade_os
                    FROM lotes_servico l
                    LEFT JOIN prestadores p ON l.prestador_id = p.id
                    WHERE l.id = %s
                """, (upload['lote_id'],))
                dados = cur.fetchone()
                lote_id = upload['lote_id']
                envio_id = None
            else:
                cur.execute("""
                    SELECT 
                        e.montador_nome as nome,
                        m.email,
                        e.id as envio_id,
                        e.periodo,
                        e.valor_total,
                        (SELECT COUNT(*) FROM ordens_servico_montagem WHERE envio_montagem_id = e.id) as quantidade_os
                    FROM envios_montagem e
                    LEFT JOIN montadores m ON e.montador_id = m.id
                    WHERE e.id = %s
                """, (upload['envio_montagem_id'],))
                dados = cur.fetchone()
                lote_id = None
                envio_id = upload['envio_montagem_id']
            
            if not dados:
                raise HTTPException(status_code=404, detail="Dados não encontrados")
            
            # Buscar arquivos já enviados
            cur.execute("""
                SELECT 
                    nome_original,
                    extensao,
                    tamanho_bytes,
                    data_upload
                FROM uploads_nf_arquivos
                WHERE upload_id = %s
                ORDER BY data_upload DESC
            """, (upload['id'],))
            arquivos = cur.fetchall()
            
            return {
                "hash": hash,
                "tipo": upload['tipo'],
                "nome": dados['nome'],
                "email": dados.get('email'),
                "lote_id": lote_id,
                "envio_id": envio_id,
                "periodo": dados['periodo'],
                "valor_total": float(dados['valor_total'] or 0),
                "quantidade_os": dados.get('quantidade_os', 0),
                "status": upload['status'],
                "status_descricao": get_status_descricao(upload['status'], expirado),
                "data_expiracao": upload['data_expiracao'].isoformat(),
                "dias_restantes": dias_restantes,
                "link_valido": not expirado and upload['status'] == 0,
                "arquivos_enviados": [
                    {
                        "nome": arq['nome_original'],
                        "extensao": arq['extensao'],
                        "tamanho": arq['tamanho_bytes'],
                        "tamanho_formatado": formatar_tamanho(arq['tamanho_bytes']),
                        "data": arq['data_upload'].isoformat() if arq['data_upload'] else None
                    }
                    for arq in arquivos
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar info do upload: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


@router.post("/enviar/{hash}")
async def enviar_arquivos(
    hash: str,
    request: Request,
    arquivos: List[UploadFile] = File(...)
):
    """
    Recebe os arquivos de nota fiscal
    Endpoint público - não requer autenticação
    """
    try:
        with get_db_connection() as conn:
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Buscar e validar upload
            cur.execute("""
                SELECT id, tipo, lote_id, envio_montagem_id, status, data_expiracao
                FROM uploads_nf
                WHERE hash = %s
            """, (hash,))
            
            upload = cur.fetchone()
            
            if not upload:
                raise HTTPException(status_code=404, detail="Link não encontrado")
            
            if upload['status'] != 0:
                raise HTTPException(status_code=400, detail="Este link já foi utilizado")
            
            if upload['data_expiracao'] < datetime.now():
                raise HTTPException(status_code=400, detail="Link expirado")
            
            if not arquivos or len(arquivos) == 0:
                raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
            
            # Criar diretório de destino
            if upload['tipo'] == 'prestador':
                pasta = os.path.join(UPLOAD_DIR, f"lote_{upload['lote_id']}")
            else:
                pasta = os.path.join(UPLOAD_DIR, f"montagem_{upload['envio_montagem_id']}")
            
            os.makedirs(pasta, exist_ok=True)
            
            # Processar cada arquivo
            arquivos_salvos = []
            ip_cliente = request.client.host if request.client else None
            
            for arquivo in arquivos:
                # Validar
                valido, msg = validar_arquivo(arquivo)
                if not valido:
                    raise HTTPException(status_code=400, detail=msg)
                
                # Ler conteúdo e verificar tamanho
                conteudo = await arquivo.read()
                if len(conteudo) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Arquivo {arquivo.filename} excede 10MB"
                    )
                
                # Gerar nome único
                ext = os.path.splitext(arquivo.filename)[1].lower()
                nome_salvo = f"{uuid.uuid4().hex}{ext}"
                caminho = os.path.join(pasta, nome_salvo)
                
                # Calcular hash do arquivo
                hash_arquivo = hashlib.sha256(conteudo).hexdigest()
                
                # Salvar arquivo
                with open(caminho, 'wb') as f:
                    f.write(conteudo)
                
                # Registrar no banco
                cur.execute("""
                    INSERT INTO uploads_nf_arquivos 
                    (upload_id, nome_original, nome_salvo, caminho, extensao, tamanho_bytes, mime_type, hash_arquivo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    upload['id'],
                    arquivo.filename,
                    nome_salvo,
                    caminho,
                    ext,
                    len(conteudo),
                    arquivo.content_type,
                    hash_arquivo
                ))
                
                arquivos_salvos.append({
                    "nome": arquivo.filename,
                    "tamanho": len(conteudo),
                    "tamanho_formatado": formatar_tamanho(len(conteudo))
                })
                
                logger.info(f"Arquivo salvo: {arquivo.filename} -> {caminho}")
            
            # Atualizar status do upload
            cur.execute("""
                UPDATE uploads_nf 
                SET status = 1, data_upload = NOW(), ip_upload = %s
                WHERE id = %s
            """, (ip_cliente, upload['id']))
            
            # Atualizar lote/envio com o caminho do primeiro arquivo
            primeiro_arquivo = os.path.join(pasta, arquivos_salvos[0]['nome']) if arquivos_salvos else None
            
            if upload['tipo'] == 'prestador':
                cur.execute("""
                    UPDATE lotes_servico 
                    SET nota_fiscal_path = %s, status_api = 1, data_recebimento_nf = NOW()
                    WHERE id = %s
                """, (pasta, upload['lote_id']))
            else:
                cur.execute("""
                    UPDATE envios_montagem 
                    SET nota_fiscal_path = %s, status_api = 1, data_recebimento_nf = NOW()
                    WHERE id = %s
                """, (pasta, upload['envio_montagem_id']))
            
            conn.commit()
            
            # Disparar notificações (async em background)
            try:
                from app.utils.upload_notifications import disparar_notificacoes_upload
                disparar_notificacoes_upload(upload['id'])
            except Exception as e:
                logger.warning(f"Erro ao disparar notificações: {e}")
            
            return {
                "success": True,
                "message": f"{len(arquivos_salvos)} arquivo(s) enviado(s) com sucesso!",
                "arquivos": arquivos_salvos
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar upload: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Erro ao processar arquivos")


# ===== ENDPOINTS INTERNOS (COM AUTH) =====

@router.post("/criar")
async def criar_link_upload(
    tipo: str = Form(...),
    referencia_id: int = Form(...)
):
    """
    Cria um novo link de upload para um lote ou envio
    Uso interno - chamado ao enviar relatório
    """
    if tipo not in ['prestador', 'montador']:
        raise HTTPException(status_code=400, detail="Tipo deve ser 'prestador' ou 'montador'")
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Verificar se já existe link ativo
            if tipo == 'prestador':
                cur.execute("""
                    SELECT hash FROM uploads_nf 
                    WHERE lote_id = %s AND status = 0 AND data_expiracao > NOW()
                """, (referencia_id,))
            else:
                cur.execute("""
                    SELECT hash FROM uploads_nf 
                    WHERE envio_montagem_id = %s AND status = 0 AND data_expiracao > NOW()
                """, (referencia_id,))
            
            existente = cur.fetchone()
            if existente:
                return {
                    "success": True,
                    "hash": existente[0],
                    "link": f"/upload/nf/{existente[0]}",
                    "message": "Link já existe"
                }
            
            # Gerar novo hash
            hash_upload = gerar_hash_unico()
            data_expiracao = datetime.now() + timedelta(days=DIAS_VALIDADE_LINK)
            
            # Inserir
            if tipo == 'prestador':
                cur.execute("""
                    INSERT INTO uploads_nf (hash, tipo, lote_id, data_expiracao, sistema)
                    VALUES (%s, %s, %s, %s, 'interno')
                    RETURNING id
                """, (hash_upload, tipo, referencia_id, data_expiracao))
            else:
                cur.execute("""
                    INSERT INTO uploads_nf (hash, tipo, envio_montagem_id, data_expiracao, sistema)
                    VALUES (%s, %s, %s, %s, 'interno')
                    RETURNING id
                """, (hash_upload, tipo, referencia_id, data_expiracao))
            
            conn.commit()
            
            return {
                "success": True,
                "hash": hash_upload,
                "link": f"/upload/nf/{hash_upload}",
                "data_expiracao": data_expiracao.isoformat(),
                "message": "Link criado com sucesso"
            }
            
    except Exception as e:
        logger.error(f"Erro ao criar link: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar link de upload")


@router.get("/pendentes")
async def listar_uploads_pendentes(tipo: Optional[str] = None):
    """Lista uploads com status pendente (sistema interno)"""
    try:
        with get_db_connection() as conn:
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT * FROM v_uploads_pendentes
                WHERE 1=1
            """
            params = []
            
            if tipo:
                query += " AND tipo = %s"
                params.append(tipo)
            
            query += " ORDER BY data_criacao DESC"
            
            cur.execute(query, params)
            
            return cur.fetchall()
            
    except Exception as e:
        logger.error(f"Erro ao listar pendentes: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar uploads")


@router.get("/recebidos")
async def listar_uploads_recebidos(
    tipo: Optional[str] = None,
    limit: int = 50
):
    """Lista uploads que já receberam arquivos"""
    try:
        with get_db_connection() as conn:
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    u.id,
                    u.hash,
                    u.tipo,
                    u.lote_id,
                    u.envio_montagem_id,
                    u.status,
                    u.data_upload,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.prestador_nome
                        WHEN u.tipo = 'montador' THEN e.montador_nome
                    END as nome,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.periodo
                        WHEN u.tipo = 'montador' THEN e.periodo
                    END as periodo,
                    (SELECT COUNT(*) FROM uploads_nf_arquivos WHERE upload_id = u.id) as total_arquivos,
                    (SELECT SUM(tamanho_bytes) FROM uploads_nf_arquivos WHERE upload_id = u.id) as tamanho_total
                FROM uploads_nf u
                LEFT JOIN lotes_servico l ON u.lote_id = l.id
                LEFT JOIN envios_montagem e ON u.envio_montagem_id = e.id
                WHERE u.status = 1
            """
            params = []
            
            if tipo:
                query += " AND u.tipo = %s"
                params.append(tipo)
            
            query += " ORDER BY u.data_upload DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            
            return cur.fetchall()
            
    except Exception as e:
        logger.error(f"Erro ao listar recebidos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar uploads")


def formatar_tamanho(bytes: int) -> str:
    """Formata tamanho em bytes para formato legível"""
    for unidade in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unidade}"
        bytes /= 1024
    return f"{bytes:.1f} TB"
