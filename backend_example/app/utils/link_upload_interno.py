"""
Utilitário para gerar links de upload internos.
Substitui a API externa (api.link.dev.br) para novos envios.
Mantém compatibilidade com sistema legado.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from pathlib import Path

# Carregar .env se existir
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# URL base do frontend - configurável via env
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://72.60.244.138")


def get_db_connection():
    """Obtém conexão com o banco de dados."""
    # Usar variáveis de ambiente ou fallback para produção
    db_password = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS") or "BracoDireto2025Prod!"
    db_user = os.getenv("DB_USER", "bracodireto")
    db_name = os.getenv("DB_NAME", "email")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    
    print(f"🔌 Conectando ao banco: {db_name}@{db_host}:{db_port} user={db_user}")
    
    return psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )


def gerar_link_upload_interno(
    tipo: str,  # 'prestador' ou 'montador'
    lote_id: Optional[int] = None,
    envio_montagem_id: Optional[int] = None,
    validade_dias: int = 30
) -> Dict[str, Any]:
    """
    Gera um link de upload interno para notas fiscais.
    
    Args:
        tipo: 'prestador' ou 'montador'
        lote_id: ID do lote_servico (para prestadores)
        envio_montagem_id: ID do envio_montagem (para montadores)
        validade_dias: Quantidade de dias até expirar o link
        
    Returns:
        Dict com hash, link, validade_link, etc.
    """
    
    # Validar parâmetros
    if tipo == 'prestador' and not lote_id:
        raise ValueError("lote_id é obrigatório para tipo 'prestador'")
    if tipo == 'montador' and not envio_montagem_id:
        raise ValueError("envio_montagem_id é obrigatório para tipo 'montador'")
    
    try:
        print(f"📝 gerar_link_upload_interno: tipo={tipo}, lote_id={lote_id}, envio_montagem_id={envio_montagem_id}")
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Calcular data de expiração
            data_expiracao = datetime.now() + timedelta(days=validade_dias)
            
            # Gerar hash usando função do banco
            print("   Executando gerar_hash_upload()...")
            cur.execute("SELECT gerar_hash_upload() as hash")
            hash_upload = cur.fetchone()['hash']
            print(f"   Hash gerado: {hash_upload}")
            
            # Inserir registro
            print("   Inserindo registro na tabela uploads_nf...")
            cur.execute("""
                INSERT INTO uploads_nf (hash, tipo, lote_id, envio_montagem_id, data_expiracao, sistema)
                VALUES (%s, %s, %s, %s, %s, 'interno')
                RETURNING id, hash, data_expiracao
            """, (
                hash_upload, 
                tipo, 
                lote_id if tipo == 'prestador' else None,
                envio_montagem_id if tipo == 'montador' else None,
                data_expiracao
            ))
            
            registro = cur.fetchone()
            conn.commit()
            
            # Montar resposta compatível com API externa
            link = f"{FRONTEND_URL}/upload/nf/{registro['hash']}"
            
            return {
                "success": True,
                "id_controle": registro['id'],
                "hash": registro['hash'],
                "link": link,
                "validade_link": registro['data_expiracao'].strftime("%Y-%m-%d %H:%M:%S"),
                "status": 0,  # Aguardando upload
                "sistema": "interno"
            }
            
    except psycopg2.Error as e:
        print(f"❌ Erro ao gerar link interno: {e}")
        return {
            "success": False,
            "message": str(e)
        }


def verificar_link_interno(hash: str) -> Optional[Dict[str, Any]]:
    """
    Verifica se um link de upload interno existe e está válido.
    
    Returns:
        Dict com informações do upload ou None se não encontrado/expirado
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
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
                    u.data_upload,
                    u.sistema,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.prestador_nome
                        WHEN u.tipo = 'montador' THEN e.montador_nome
                    END as nome_entidade,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.periodo
                        WHEN u.tipo = 'montador' THEN e.periodo
                    END as periodo,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.valor_total
                        WHEN u.tipo = 'montador' THEN e.valor_total
                    END as valor_total,
                    COALESCE(
                        (SELECT COUNT(*) FROM uploads_nf_arquivos WHERE upload_id = u.id),
                        0
                    ) as total_arquivos
                FROM uploads_nf u
                LEFT JOIN lotes_servico l ON u.lote_id = l.id
                LEFT JOIN envios_montagem e ON u.envio_montagem_id = e.id
                WHERE u.hash = %s AND u.sistema = 'interno'
            """, (hash,))
            
            registro = cur.fetchone()
            
            if not registro:
                return None
            
            # Verificar se expirou
            if registro['data_expiracao'] < datetime.now():
                # Marcar como expirado
                cur.execute("""
                    UPDATE uploads_nf SET status = 2 WHERE id = %s
                """, (registro['id'],))
                conn.commit()
                registro['status'] = 2
                registro['expirado'] = True
            else:
                registro['expirado'] = False
                
            return dict(registro)
            
    except psycopg2.Error as e:
        print(f"❌ Erro ao verificar link: {e}")
        return None


def consultar_uploads_internos_pendentes(
    tipo: Optional[str] = None,
    lote_id: Optional[int] = None,
    envio_montagem_id: Optional[int] = None
) -> list:
    """
    Consulta uploads internos que ainda estão aguardando NF.
    
    Args:
        tipo: Filtrar por 'prestador' ou 'montador'
        lote_id: Filtrar por lote específico
        envio_montagem_id: Filtrar por envio de montagem específico
        
    Returns:
        Lista de uploads pendentes
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT * FROM v_uploads_pendentes WHERE 1=1
            """
            params = []
            
            if tipo:
                query += " AND tipo = %s"
                params.append(tipo)
            if lote_id:
                query += " AND lote_id = %s"
                params.append(lote_id)
            if envio_montagem_id:
                query += " AND envio_montagem_id = %s"
                params.append(envio_montagem_id)
            
            query += " ORDER BY data_criacao DESC"
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
            
    except psycopg2.Error as e:
        print(f"❌ Erro ao consultar uploads pendentes: {e}")
        return []


def consultar_uploads_realizados_interno(
    tipo: Optional[str] = None,
    desde: Optional[datetime] = None
) -> list:
    """
    Consulta uploads internos que já receberam arquivos.
    Usado pelo job de consulta de notas.
    
    Args:
        tipo: Filtrar por 'prestador' ou 'montador'
        desde: Data mínima de upload
        
    Returns:
        Lista de uploads realizados
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT 
                    u.id,
                    u.hash,
                    u.tipo,
                    u.lote_id,
                    u.envio_montagem_id,
                    u.status,
                    u.data_criacao,
                    u.data_upload,
                    u.sistema,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.prestador_nome
                        WHEN u.tipo = 'montador' THEN e.montador_nome
                    END as nome_entidade,
                    CASE 
                        WHEN u.tipo = 'prestador' THEN l.periodo
                        WHEN u.tipo = 'montador' THEN e.periodo
                    END as periodo,
                    array_agg(json_build_object(
                        'id', a.id,
                        'nome', a.nome_original,
                        'caminho', a.caminho,
                        'tamanho', a.tamanho_bytes
                    )) as arquivos
                FROM uploads_nf u
                LEFT JOIN lotes_servico l ON u.lote_id = l.id
                LEFT JOIN envios_montagem e ON u.envio_montagem_id = e.id
                LEFT JOIN uploads_nf_arquivos a ON a.upload_id = u.id
                WHERE u.status = 1 
                  AND u.sistema = 'interno'
            """
            params = []
            
            if tipo:
                query += " AND u.tipo = %s"
                params.append(tipo)
            if desde:
                query += " AND u.data_upload >= %s"
                params.append(desde)
            
            query += """
                GROUP BY u.id, u.hash, u.tipo, u.lote_id, u.envio_montagem_id, 
                         u.status, u.data_criacao, u.data_upload, u.sistema,
                         l.prestador_nome, e.montador_nome, l.periodo, e.periodo
                ORDER BY u.data_upload DESC
            """
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
            
    except psycopg2.Error as e:
        print(f"❌ Erro ao consultar uploads realizados: {e}")
        return []


def atualizar_tabela_origem_com_link(
    tipo: str,
    lote_id: Optional[int],
    envio_montagem_id: Optional[int],
    link: str,
    hash_upload: str,
    id_controle: int,
    validade: str
) -> bool:
    """
    Atualiza lotes_servico ou envios_montagem com o link interno gerado.
    Mantém compatibilidade com campos existentes.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            if tipo == 'prestador' and lote_id:
                cur.execute("""
                    UPDATE lotes_servico 
                    SET link_upload = %s, 
                        upload_hash = %s, 
                        id_controle = %s,
                        validade_link = %s,
                        data_envio_api = NOW(),
                        fonte = 'interno'
                    WHERE id = %s
                """, (link, hash_upload, id_controle, validade, lote_id))
                
            elif tipo == 'montador' and envio_montagem_id:
                cur.execute("""
                    UPDATE envios_montagem 
                    SET link_upload = %s, 
                        upload_hash = %s, 
                        id_controle = %s,
                        validade_link = %s,
                        data_envio_api = NOW(),
                        fonte = 'interno'
                    WHERE id = %s
                """, (link, hash_upload, id_controle, validade, envio_montagem_id))
            
            conn.commit()
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Erro ao atualizar tabela origem: {e}")
        return False


# Função wrapper para substituir chamada à API externa
def gerar_link_upload(
    nome: str,
    email: str,
    periodo: str,
    valor_total: float,
    quantidade_os: int,
    lote_id: int,
    tipo: str,  # 'prestador' ou 'montador'  
    usar_interno: bool = True,
    validade_dias: int = 30
) -> Dict[str, Any]:
    """
    Função wrapper que gera link interno ou chama API externa.
    
    Esta função substitui diretamente as chamadas à API externa,
    mantendo a mesma interface de resposta.
    
    Args:
        nome: Nome do destinatário
        email: Email do destinatário
        periodo: Período do relatório
        valor_total: Valor total do lote
        quantidade_os: Quantidade de O.S.
        lote_id: ID do lote (ou envio_montagem para montadores)
        tipo: 'prestador' ou 'montador'
        usar_interno: Se True, usa sistema interno. Se False, chama API externa
        validade_dias: Dias até o link expirar
        
    Returns:
        Dict compatível com resposta da API externa
    """
    
    if usar_interno:
        # Usar sistema interno
        if tipo == 'montador':
            resultado = gerar_link_upload_interno(
                tipo='montador',
                envio_montagem_id=lote_id,
                validade_dias=validade_dias
            )
        else:
            resultado = gerar_link_upload_interno(
                tipo='prestador',
                lote_id=lote_id,
                validade_dias=validade_dias
            )
        
        if resultado.get('success'):
            # Atualizar tabela de origem
            atualizar_tabela_origem_com_link(
                tipo=tipo,
                lote_id=lote_id if tipo == 'prestador' else None,
                envio_montagem_id=lote_id if tipo == 'montador' else None,
                link=resultado['link'],
                hash_upload=resultado['hash'],
                id_controle=resultado['id_controle'],
                validade=resultado['validade_link']
            )
        
        return resultado
    
    else:
        # Chamar API externa (legado)
        import requests
        
        API_UPLOAD_URL = "http://api.link.dev.br/dvprocessamento/"
        API_UPLOAD_KEY = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
        
        payload = {
            "nome": nome,
            "email": email,
            "periodo": periodo,
            "valor_total": valor_total,
            "quantidade_os": quantidade_os,
            "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "lote_id": lote_id,
            "tipo": tipo
        }
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "NovoMundo-DisparadorEmail/1.0",
            "X-API-Key": API_UPLOAD_KEY
        }
        
        try:
            print(f"   📤 Chamando API externa: {API_UPLOAD_URL}")
            print(f"   📤 Payload: {payload}")
            
            response = requests.post(
                API_UPLOAD_URL,
                json=payload,
                headers=headers,
                timeout=10,
                verify=False
            )
            
            print(f"   📥 Status: {response.status_code}")
            print(f"   📥 Resposta: {response.text[:500] if response.text else 'vazio'}")
            
            if response.status_code in [200, 201]:
                resposta = response.json()
                if resposta.get('success'):
                    # Marcar origem como externo
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        if tipo == 'prestador':
                            cur.execute("""
                                UPDATE lotes_servico 
                                SET fonte = 'api_externa' 
                                WHERE id = %s
                            """, (lote_id,))
                        else:
                            cur.execute("""
                                UPDATE envios_montagem 
                                SET fonte = 'api_externa' 
                                WHERE id = %s
                            """, (lote_id,))
                        conn.commit()
                        
                return resposta
            else:
                print(f"   ❌ API externa retornou erro: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"API retornou status {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
