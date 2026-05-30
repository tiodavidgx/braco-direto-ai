# =====================================================
# ROTAS DE GESTÃO DE PAGAMENTOS - ROTEIRO FINANCEIRO
# =====================================================

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import pandas as pd
import io
import psycopg2.extras
from ..database import get_db_connection

router = APIRouter(tags=["Gestão de Pagamentos"])


# ==================== MODELOS ====================

class OrcamentoConfig(BaseModel):
    orcamento_diario: float
    dia_inicio_semana: int = 1
    dias_uteis_semana: int = 5


class FornecedorPrioridade(BaseModel):
    nome_fornecedor: str
    cnpj_cpf: Optional[str] = None
    tier: int = 3
    descricao: Optional[str] = None
    max_dias_atraso: int = 0
    notas: Optional[str] = None


class FornecedorPrioridadeUpdate(BaseModel):
    tier: Optional[int] = None
    descricao: Optional[str] = None
    max_dias_atraso: Optional[int] = None
    notas: Optional[str] = None


class PagamentoExcecao(BaseModel):
    nome_fornecedor: str
    cnpj_cpf: Optional[str] = None
    valor_solicitado: float
    data_necessidade: date
    data_limite: Optional[date] = None
    motivo: str
    prioridade_especial: int = 1


class TituloImportado(BaseModel):
    numero_titulo: Optional[str] = None
    nome_fornecedor: str
    cnpj_cpf: Optional[str] = None
    valor: float
    data_vencimento: date
    data_emissao: Optional[date] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    pix: Optional[str] = None


# ========== INICIALIZAR TABELA DE TÍTULOS EXCLUÍDOS ==========
def _ensure_titulos_excluidos_table():
    """Cria a tabela titulos_excluidos se não existir"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS titulos_excluidos (
                        id SERIAL PRIMARY KEY,
                        numero_titulo VARCHAR(100),
                        nome_fornecedor VARCHAR(255) NOT NULL,
                        cod_fornecedor VARCHAR(50),
                        cnpj_cpf VARCHAR(20),
                        valor DECIMAL(15, 2),
                        data_vencimento DATE,
                        chave_fornecedor_titulo VARCHAR(300) NOT NULL,
                        motivo VARCHAR(50) DEFAULT 'excluido_manual',
                        excluido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_titulos_excluidos_chave
                    ON titulos_excluidos (chave_fornecedor_titulo)
                """)
    except Exception as e:
        print(f"⚠️ Erro ao criar tabela titulos_excluidos: {e}")

# Executar na inicialização do módulo
_ensure_titulos_excluidos_table()


def _gerar_chave_titulo(cod_fornecedor: str, numero_titulo: str, bloquear_todas_parcelas: bool = True) -> str:
    """Gera chave única: COD_FORNECEDOR + '|' + TITULO
    
    Args:
        cod_fornecedor: Código do fornecedor (mais preciso que nome)
        numero_titulo: Número do título
        bloquear_todas_parcelas: Se True, remove sufixos de parcela para bloquear todas
    """
    import re
    cod = str(cod_fornecedor or '').strip().upper()
    tit = str(numero_titulo or '').strip()
    
    if bloquear_todas_parcelas:
        # Remover sufixos de parcela para pegar a chave base
        tit_base = re.sub(r'[-\s]*P\d+$', '', tit)  # Remove -P1, -P2
        tit_base = re.sub(r'\s*\(\d+/\d+\)$', '', tit_base)  # Remove (1/2)
        return f"{cod}|{tit_base.upper()}"
    else:
        # Manter parcela exata
        return f"{cod}|{tit.upper()}"


# ==================== CONFIGURAÇÃO DE ORÇAMENTO ====================

@router.get("/orcamento")
async def get_orcamento():
    """Retorna a configuração de orçamento atual"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM configuracao_orcamento ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "orcamento_diario": float(row[1]),
                    "dia_inicio_semana": row[2],
                    "dias_uteis_semana": row[3]
                }
            return {"orcamento_diario": 40000.0, "dia_inicio_semana": 1, "dias_uteis_semana": 5}


@router.put("/orcamento")
async def update_orcamento(config: OrcamentoConfig):
    """Atualiza a configuração de orçamento"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE configuracao_orcamento 
                SET orcamento_diario = %s, dia_inicio_semana = %s, dias_uteis_semana = %s, atualizado_em = NOW()
                WHERE id = (SELECT id FROM configuracao_orcamento ORDER BY id DESC LIMIT 1)
                RETURNING id
            """, (config.orcamento_diario, config.dia_inicio_semana, config.dias_uteis_semana))
            
            result = cur.fetchone()
            if not result:
                cur.execute("""
                    INSERT INTO configuracao_orcamento (orcamento_diario, dia_inicio_semana, dias_uteis_semana)
                    VALUES (%s, %s, %s)
                """, (config.orcamento_diario, config.dia_inicio_semana, config.dias_uteis_semana))
            
            return {"message": "Orçamento atualizado com sucesso"}


# ==================== PRIORIDADES DE FORNECEDORES (TIERS) ====================

@router.get("/fornecedores/buscar")
async def buscar_fornecedores(q: Optional[str] = None):
    """Busca fornecedores dos títulos importados nos últimos 120 dias para autocomplete"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q and len(q) >= 2:
                # Buscar por nome ou código
                cur.execute("""
                    SELECT DISTINCT 
                        nome_fornecedor, 
                        cod_fornecedor,
                        cnpj_cpf,
                        COUNT(*) as total_titulos,
                        SUM(valor) as valor_total
                    FROM titulos_importados
                    WHERE criado_em >= NOW() - INTERVAL '120 days'
                    AND (
                        LOWER(nome_fornecedor) LIKE LOWER(%s) 
                        OR cod_fornecedor::text LIKE %s
                    )
                    GROUP BY nome_fornecedor, cod_fornecedor, cnpj_cpf
                    ORDER BY total_titulos DESC
                    LIMIT 20
                """, (f'%{q}%', f'%{q}%'))
            else:
                # Listar todos os fornecedores recentes
                cur.execute("""
                    SELECT DISTINCT 
                        nome_fornecedor, 
                        cod_fornecedor,
                        cnpj_cpf,
                        COUNT(*) as total_titulos,
                        SUM(valor) as valor_total
                    FROM titulos_importados
                    WHERE criado_em >= NOW() - INTERVAL '120 days'
                    GROUP BY nome_fornecedor, cod_fornecedor, cnpj_cpf
                    ORDER BY total_titulos DESC
                    LIMIT 50
                """)
            
            rows = cur.fetchall()
            return [{
                "nome_fornecedor": row[0],
                "cod_fornecedor": row[1],
                "cnpj_cpf": row[2],
                "total_titulos": row[3],
                "valor_total": float(row[4]) if row[4] else 0,
                "label": f"{row[1]} - {row[0]}" if row[1] else row[0]
            } for row in rows]


@router.get("/fornecedores/prioridades")
async def list_fornecedor_prioridades():
    """Lista todos os fornecedores com suas prioridades"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nome_fornecedor, cnpj_cpf, tier, descricao, max_dias_atraso, notas, criado_em
                FROM fornecedor_prioridades
                ORDER BY tier ASC, nome_fornecedor ASC
            """)
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "nome_fornecedor": row[1],
                "cnpj_cpf": row[2],
                "tier": row[3],
                "descricao": row[4],
                "max_dias_atraso": row[5],
                "notas": row[6],
                "criado_em": row[7].isoformat() if row[7] else None
            } for row in rows]


@router.post("/fornecedores/prioridades")
async def create_fornecedor_prioridade(fornecedor: FornecedorPrioridade):
    """Cadastra um novo fornecedor com prioridade"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fornecedor_prioridades (nome_fornecedor, cnpj_cpf, tier, descricao, max_dias_atraso, notas)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nome_fornecedor) DO UPDATE SET
                    tier = EXCLUDED.tier,
                    descricao = EXCLUDED.descricao,
                    max_dias_atraso = EXCLUDED.max_dias_atraso,
                    notas = EXCLUDED.notas,
                    atualizado_em = NOW()
                RETURNING id
            """, (fornecedor.nome_fornecedor, fornecedor.cnpj_cpf, fornecedor.tier, 
                  fornecedor.descricao, fornecedor.max_dias_atraso, fornecedor.notas))
            result = cur.fetchone()
            return {"id": result[0], "message": "Fornecedor cadastrado com sucesso"}


@router.put("/fornecedores/prioridades/{fornecedor_id}")
async def update_fornecedor_prioridade(fornecedor_id: int, dados: FornecedorPrioridadeUpdate):
    """Atualiza a prioridade de um fornecedor"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            updates = []
            values = []
            
            if dados.tier is not None:
                updates.append("tier = %s")
                values.append(dados.tier)
            if dados.descricao is not None:
                updates.append("descricao = %s")
                values.append(dados.descricao)
            if dados.max_dias_atraso is not None:
                updates.append("max_dias_atraso = %s")
                values.append(dados.max_dias_atraso)
            if dados.notas is not None:
                updates.append("notas = %s")
                values.append(dados.notas)
            
            if not updates:
                raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
            
            updates.append("atualizado_em = NOW()")
            values.append(fornecedor_id)
            
            cur.execute(f"""
                UPDATE fornecedor_prioridades 
                SET {', '.join(updates)}
                WHERE id = %s
            """, values)
            
            return {"message": "Fornecedor atualizado com sucesso"}


@router.delete("/fornecedores/prioridades/{fornecedor_id}")
async def delete_fornecedor_prioridade(fornecedor_id: int):
    """Remove um fornecedor da lista de prioridades"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fornecedor_prioridades WHERE id = %s", (fornecedor_id,))
            return {"message": "Fornecedor removido com sucesso"}


# ==================== EXCEÇÕES DE PAGAMENTO ====================

@router.get("/excecoes")
async def list_excecoes():
    """Lista todas as exceções de pagamento ativas"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nome_fornecedor, cnpj_cpf, valor_solicitado, data_necessidade, 
                       data_limite, motivo, status, prioridade_especial, criado_em
                FROM pagamento_excecoes
                WHERE status IN ('pendente', 'aprovado')
                ORDER BY prioridade_especial ASC, data_necessidade ASC
            """)
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "nome_fornecedor": row[1],
                "cnpj_cpf": row[2],
                "valor_solicitado": float(row[3]),
                "data_necessidade": row[4].isoformat() if row[4] else None,
                "data_limite": row[5].isoformat() if row[5] else None,
                "motivo": row[6],
                "status": row[7],
                "prioridade_especial": row[8],
                "criado_em": row[9].isoformat() if row[9] else None
            } for row in rows]


@router.post("/excecoes")
async def create_excecao(excecao: PagamentoExcecao):
    """Cria uma nova exceção de pagamento"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pagamento_excecoes 
                (nome_fornecedor, cnpj_cpf, valor_solicitado, data_necessidade, data_limite, motivo, prioridade_especial)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (excecao.nome_fornecedor, excecao.cnpj_cpf, excecao.valor_solicitado,
                  excecao.data_necessidade, excecao.data_limite, excecao.motivo, excecao.prioridade_especial))
            result = cur.fetchone()
            return {"id": result[0], "message": "Exceção criada com sucesso"}


@router.put("/excecoes/{excecao_id}/status")
async def update_excecao_status(excecao_id: int, status: str):
    """Atualiza o status de uma exceção"""
    if status not in ['pendente', 'aprovado', 'pago', 'cancelado']:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pagamento_excecoes 
                SET status = %s, atualizado_em = NOW()
                WHERE id = %s
            """, (status, excecao_id))
            return {"message": "Status atualizado com sucesso"}


@router.delete("/excecoes/{excecao_id}")
async def delete_excecao(excecao_id: int):
    """Remove uma exceção"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pagamento_excecoes WHERE id = %s", (excecao_id,))
            return {"message": "Exceção removida com sucesso"}


# ==================== TÍTULOS IMPORTADOS ====================

@router.get("/titulos")
async def list_titulos(status: Optional[str] = None):
    """Lista todos os títulos importados"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT t.id, t.numero_titulo, t.nome_fornecedor, t.cnpj_cpf, t.valor, 
                       t.data_vencimento, t.data_emissao, t.descricao, t.categoria,
                       t.status, t.data_agendamento, t.lote_importacao, t.criado_em,
                       COALESCE(fp.tier, 3) as tier,
                       t.titulo_original_id, t.parcela_numero, t.parcela_total,
                       t.cod_fornecedor, t.banco, t.agencia, t.conta, t.pix,
                       t.id_titulo_pagar, t.num_orcom, t.filial, t.empresa, t.data_pagamento,
                       t.tipo, t.tipo_movimento, t.situacao, t.documento_dev, t.liberacao,
                       t.empenho, t.carne, t.valor_titulo, t.valor_antecipado, t.valor_desconto,
                       t.valor_desconto_tributacao, t.instrucao_pagamento, t.grupo_conta,
                       t.seu_numero, t.vinculado_lote, t.lote_erp
                FROM titulos_importados t
                LEFT JOIN fornecedor_prioridades fp ON LOWER(t.nome_fornecedor) = LOWER(fp.nome_fornecedor)
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND t.status = %s"
                params.append(status)
            
            query += " ORDER BY t.data_vencimento ASC, tier ASC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [{
                "id": row[0],
                "numero_titulo": row[1],
                "nome_fornecedor": row[2],
                "cnpj_cpf": row[3],
                "valor": float(row[4]),
                "data_vencimento": row[5].isoformat() if row[5] else None,
                "data_emissao": row[6].isoformat() if row[6] else None,
                "descricao": row[7],
                "categoria": row[8],
                "status": row[9],
                "data_agendamento": row[10].isoformat() if row[10] else None,
                "lote_importacao": row[11],
                "criado_em": row[12].isoformat() if row[12] else None,
                "tier": row[13],
                "titulo_original_id": row[14],
                "parcela_numero": row[15],
                "parcela_total": row[16],
                "cod_fornecedor": row[17],
                "banco": row[18],
                "agencia": row[19],
                "conta": row[20],
                "pix": row[21],
                "id_titulo_pagar": row[22],
                "num_orcom": row[23],
                "filial": row[24],
                "empresa": row[25],
                "data_pagamento": row[26].isoformat() if row[26] else None,
                "tipo": row[27],
                "tipo_movimento": row[28],
                "situacao": row[29],
                "documento_dev": row[30],
                "liberacao": row[31],
                "empenho": row[32],
                "carne": row[33],
                "valor_titulo": float(row[34]) if row[34] else None,
                "valor_antecipado": float(row[35]) if row[35] else None,
                "valor_desconto": float(row[36]) if row[36] else None,
                "valor_desconto_tributacao": float(row[37]) if row[37] else None,
                "instrucao_pagamento": row[38],
                "grupo_conta": row[39],
                "seu_numero": row[40],
                "vinculado_lote": row[41],
                "lote_erp": row[42]
            } for row in rows]


@router.post("/titulos/preview")
async def preview_arquivo(file: UploadFile = File(...)):
    """Faz preview das colunas de um arquivo para debug"""
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine='python')
                    break
                except:
                    continue
            else:
                df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        return {
            "colunas_originais": list(df.columns),
            "colunas_lowercase": [c.lower().strip() for c in df.columns],
            "total_linhas": len(df),
            "primeiras_linhas": df.head(3).to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/titulos/importar")
async def importar_titulos(file: UploadFile = File(...)):
    """Importa títulos de um arquivo Excel/CSV"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Formato de arquivo inválido. Use Excel ou CSV.")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            # Tentar diferentes encodings para CSV
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine='python')
                    break
                except:
                    continue
            else:
                df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Debug: mostrar colunas originais
        colunas_originais = list(df.columns)
        print(f"DEBUG - Colunas originais: {colunas_originais}")
        
        # Normalizar nomes das colunas (remover espaços extras e converter para minúsculas)
        df.columns = df.columns.str.lower().str.strip()
        
        # Mapear colunas comuns (incluindo padrão do sistema ERP)
        column_mapping = {
            # Fornecedor
            'fornecedor': 'nome_fornecedor',
            'razao_social': 'nome_fornecedor',
            'razão social': 'nome_fornecedor',
            'nome': 'nome_fornecedor',
            'nome fornecedor': 'nome_fornecedor',
            # Código fornecedor
            'cod. fornecedor': 'cod_fornecedor',
            'cod.fornecedor': 'cod_fornecedor',
            'cod fornecedor': 'cod_fornecedor',
            'codigo fornecedor': 'cod_fornecedor',
            # CNPJ/CPF
            'cnpj': 'cnpj_cpf',
            'cpf': 'cnpj_cpf',
            'cnpj/cpf': 'cnpj_cpf',
            'cpf cnpj': 'cnpj_cpf',
            'cpf/cnpj': 'cnpj_cpf',
            # Número título
            'numero': 'numero_titulo',
            'título': 'numero_titulo',
            'titulo': 'numero_titulo',
            'nf': 'numero_titulo',
            'nota': 'numero_titulo',
            'num. titulo': 'numero_titulo',
            'num.titulo': 'numero_titulo',
            'num titulo': 'numero_titulo',
            # ID Título Pagar
            'id  titulo pagar': 'id_titulo_pagar',
            'id titulo pagar': 'id_titulo_pagar',
            # Num Orcom
            'num. orcom': 'num_orcom',
            'num.orcom': 'num_orcom',
            'num orcom': 'num_orcom',
            # Filial e Empresa
            'filial': 'filial',
            'empresa': 'empresa',
            # Parcela original do ERP
            'parcela': 'parcela_erp',
            # Datas
            'data lancamento': 'data_emissao',
            'data lançamento': 'data_emissao',
            'emissao': 'data_emissao',
            'dt_emissao': 'data_emissao',
            'data emissão': 'data_emissao',
            'data vencimento': 'data_vencimento',
            'vencimento': 'data_vencimento',
            'dt_vencimento': 'data_vencimento',
            'data pagamento': 'data_pagamento',
            # Tipo e Tipo Mov
            'tipo': 'tipo',
            'tipo mov.': 'tipo_movimento',
            'tipo mov': 'tipo_movimento',
            # Situação
            'situação': 'situacao',
            'situacao': 'situacao',
            # Documento Dev
            'documento dev.': 'documento_dev',
            'documento dev': 'documento_dev',
            # Liberação, Empenho, Carnê
            'liberação': 'liberacao',
            'liberacao': 'liberacao',
            'empenho': 'empenho',
            'carnê': 'carne',
            'carne': 'carne',
            # Valores
            'valor do titulo': 'valor_titulo',
            'valor do título': 'valor_titulo',
            'valor do t\u00edtulo': 'valor_titulo',
            'valor antecipado': 'valor_antecipado',
            'valor desconto': 'valor_desconto',
            'valor desconto tributacao': 'valor_desconto_tributacao',
            'valor desconto tributação': 'valor_desconto_tributacao',
            'valor final': 'valor',
            # Instrução pagamento
            'instrucao_pagamento': 'instrucao_pagamento',
            'instrução pagamento': 'instrucao_pagamento',
            'instrucao pagamento': 'instrucao_pagamento',
            # Grupo de Conta e Conta
            'grupo de conta': 'grupo_conta',
            'grupo conta': 'grupo_conta',
            'conta': 'conta',
            # Descrição
            'descricao': 'descricao',
            'descrição': 'descricao',
            'descrição conta': 'descricao',
            'descricao conta': 'descricao',
            # Seu Número
            'seu número': 'seu_numero',
            'seu numero': 'seu_numero',
            'seu n\u00famero': 'seu_numero',
            # Vinculado a Lote e Lote
            'vinculado a lote': 'vinculado_lote',
            'lote': 'lote_erp',
            # Categoria (legado)
            'categoria': 'categoria',
            # Dados bancários
            'banco': 'banco',
            'agencia': 'agencia',
            'agência': 'agencia',
            'pix': 'pix',
            'chave pix': 'pix',
        }
        
        df.rename(columns=column_mapping, inplace=True)
        
        # Debug: mostrar colunas após mapeamento
        colunas_mapeadas = list(df.columns)
        print(f"DEBUG - Colunas após mapeamento: {colunas_mapeadas}")
        
        # Verificar colunas obrigatórias
        required = ['nome_fornecedor', 'valor', 'data_vencimento']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Colunas obrigatórias não encontradas: {missing}. Colunas disponíveis: {colunas_mapeadas}"
            )
        
        # Gerar lote de importação
        lote = datetime.now().strftime("IMP%Y%m%d%H%M%S")
        
        # Limite para parcelamento automático (R$ 40.000)
        LIMITE_PARCELAMENTO = 40000.0
        
        # Data mínima para importação (só importa títulos com vencimento > 16/01/2026)
        DATA_MINIMA_VENCIMENTO = date(2026, 1, 16)
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                importados = 0
                erros = []
                titulos_parcelados = 0
                titulos_ignorados_data = 0
                titulos_duplicados = 0
                
                for idx, row in df.iterrows():
                    try:
                        # Converter valor
                        valor = row['valor']
                        if isinstance(valor, str):
                            valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        valor = float(valor)
                        
                        # Converter data
                        data_venc = row['data_vencimento']
                        if isinstance(data_venc, str):
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                                try:
                                    data_venc = datetime.strptime(data_venc, fmt).date()
                                    break
                                except:
                                    continue
                        elif hasattr(data_venc, 'date'):
                            data_venc = data_venc.date()
                        
                        # Filtrar títulos com vencimento <= 16/01/2026
                        if data_venc <= DATA_MINIMA_VENCIMENTO:
                            titulos_ignorados_data += 1
                            continue
                        
                        data_emissao = None
                        if 'data_emissao' in row and pd.notna(row['data_emissao']):
                            de = row['data_emissao']
                            if isinstance(de, str):
                                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                                    try:
                                        data_emissao = datetime.strptime(de, fmt).date()
                                        break
                                    except:
                                        continue
                            elif hasattr(de, 'date'):
                                data_emissao = de.date()
                        
                        # Função auxiliar para pegar valor de forma segura
                        def get_val(col):
                            if col in row.index:
                                val = row[col]
                                # Se for Series (coluna duplicada), pegar primeiro valor
                                if hasattr(val, 'iloc'):
                                    val = val.iloc[0]
                                # Converter NaN para None
                                if pd.isna(val):
                                    return None
                                return val
                            return None
                        
                        # Função auxiliar para converter valores monetários BR (1.432,54 -> 1432.54)
                        def get_money(col):
                            val = get_val(col)
                            if val is None:
                                return None
                            if isinstance(val, (int, float)):
                                return float(val)
                            val = str(val).replace('R$', '').replace(' ', '')
                            # Formato brasileiro: 1.432,54
                            if ',' in val:
                                val = val.replace('.', '').replace(',', '.')
                            return float(val) if val else None
                        
                        numero_titulo_original = get_val('numero_titulo')
                        # Converter numero_titulo para string se não for None
                        if numero_titulo_original is not None:
                            numero_titulo_original = str(numero_titulo_original).strip()
                            # Remover .0 se for número inteiro convertido
                            if numero_titulo_original.endswith('.0'):
                                numero_titulo_original = numero_titulo_original[:-2]
                        
                        nome_fornecedor = str(row['nome_fornecedor']).strip()
                        cod_fornecedor = get_val('cod_fornecedor')
                        
                        # Verificar se título já existe (evitar duplicados)
                        # Considera: numero_titulo + fornecedor similar + data_vencimento
                        # Também verifica parcelas do mesmo título (13-P1, 13-P2, 13 (1/2), etc)
                        # Usa os primeiros 20 caracteres do fornecedor para comparação fuzzy
                        fornecedor_prefixo = nome_fornecedor[:20].upper() if nome_fornecedor else ''
                        
                        cur.execute("""
                            SELECT id FROM titulos_importados 
                            WHERE (
                                TRIM(numero_titulo) = %s 
                                OR TRIM(numero_titulo) LIKE %s
                                OR TRIM(numero_titulo) LIKE %s
                            )
                            AND UPPER(LEFT(nome_fornecedor, 20)) = %s
                            AND data_vencimento = %s
                            LIMIT 1
                        """, (
                            numero_titulo_original, 
                            f"{numero_titulo_original}-P%",  # Formato 13-P1, 13-P2
                            f"{numero_titulo_original} (%",  # Formato 13 (1/2), 13 (2/2)
                            fornecedor_prefixo,
                            data_venc
                        ))
                        
                        existing = cur.fetchone()
                        if existing:
                            titulos_duplicados += 1
                            continue  # Pular título duplicado
                        
                        # Verificar se título foi excluído anteriormente (blacklist)
                        chave_titulo = _gerar_chave_titulo(cod_fornecedor, numero_titulo_original)
                        cur.execute("""
                            SELECT id FROM titulos_excluidos 
                            WHERE chave_fornecedor_titulo = %s
                            LIMIT 1
                        """, (chave_titulo,))
                        
                        excluido = cur.fetchone()
                        if excluido:
                            titulos_duplicados += 1
                            continue  # Pular título da blacklist
                        
                        # Verificar se precisa parcelar (valor > 40k)
                        if valor > LIMITE_PARCELAMENTO:
                            import math
                            # Calcular quantas parcelas de 40k cabem
                            parcelas_cheias = int(valor // LIMITE_PARCELAMENTO)
                            residual = round(valor - (parcelas_cheias * LIMITE_PARCELAMENTO), 2)
                            
                            # Total de parcelas (cheias + residual se houver)
                            num_parcelas = parcelas_cheias + (1 if residual > 0 else 0)
                            
                            parcela_atual = 0
                            parcela_ids_importacao = []  # Track IDs para setar titulo_original_id
                            
                            # Criar parcelas de 40k
                            for i in range(parcelas_cheias):
                                parcela_atual += 1
                                numero_titulo_parcela = f"{numero_titulo_original} ({parcela_atual}/{num_parcelas})" if numero_titulo_original else f"PARC-{idx+2}-{parcela_atual}/{num_parcelas}"
                                
                                cur.execute("""
                                    INSERT INTO titulos_importados 
                                    (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, data_emissao, 
                                     descricao, categoria, lote_importacao, banco, agencia, conta, pix,
                                     id_titulo_pagar, num_orcom, filial, empresa, data_pagamento, tipo, tipo_movimento,
                                     situacao, documento_dev, liberacao, empenho, carne, valor_titulo, valor_antecipado,
                                     valor_desconto, valor_desconto_tributacao, instrucao_pagamento, grupo_conta, seu_numero,
                                     vinculado_lote, lote_erp, parcela_numero, parcela_total)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    RETURNING id
                                """, (
                                    numero_titulo_parcela,
                                    nome_fornecedor,
                                    get_val('cod_fornecedor'),
                                    get_val('cnpj_cpf'),
                                    LIMITE_PARCELAMENTO,
                                    data_venc,
                                    data_emissao,
                                    f"[Parcela {parcela_atual}/{num_parcelas} - Total: R$ {valor:,.2f}] {get_val('descricao') or ''}".strip(),
                                    get_val('categoria'),
                                    lote,
                                    get_val('banco'),
                                    get_val('agencia'),
                                    get_val('conta'),
                                    get_val('pix'),
                                    get_val('id_titulo_pagar'),
                                    get_val('num_orcom'),
                                    get_val('filial'),
                                    get_val('empresa'),
                                    None,  # data_pagamento
                                    get_val('tipo'),
                                    get_val('tipo_movimento'),
                                    get_val('situacao'),
                                    get_val('documento_dev'),
                                    get_val('liberacao'),
                                    get_val('empenho'),
                                    get_val('carne'),
                                    valor,  # valor_titulo = valor total original
                                    get_money('valor_antecipado'),
                                    get_money('valor_desconto'),
                                    get_money('valor_desconto_tributacao'),
                                    get_val('instrucao_pagamento'),
                                    get_val('grupo_conta'),
                                    get_val('seu_numero'),
                                    get_val('vinculado_lote'),
                                    get_val('lote_erp'),
                                    parcela_atual,
                                    num_parcelas
                                ))
                                inserted = cur.fetchone()
                                if inserted:
                                    parcela_ids_importacao.append(inserted[0])
                                importados += 1
                            
                            # Criar parcela residual se houver
                            if residual > 0:
                                parcela_atual += 1
                                numero_titulo_parcela = f"{numero_titulo_original} ({parcela_atual}/{num_parcelas})" if numero_titulo_original else f"PARC-{idx+2}-{parcela_atual}/{num_parcelas}"
                                
                                cur.execute("""
                                    INSERT INTO titulos_importados 
                                    (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, data_emissao, 
                                     descricao, categoria, lote_importacao, banco, agencia, conta, pix,
                                     id_titulo_pagar, num_orcom, filial, empresa, data_pagamento, tipo, tipo_movimento,
                                     situacao, documento_dev, liberacao, empenho, carne, valor_titulo, valor_antecipado,
                                     valor_desconto, valor_desconto_tributacao, instrucao_pagamento, grupo_conta, seu_numero,
                                     vinculado_lote, lote_erp, parcela_numero, parcela_total)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    RETURNING id
                                """, (
                                    numero_titulo_parcela,
                                    nome_fornecedor,
                                    get_val('cod_fornecedor'),
                                    get_val('cnpj_cpf'),
                                    residual,
                                    data_venc,
                                    data_emissao,
                                    f"[Parcela {parcela_atual}/{num_parcelas} - Residual - Total: R$ {valor:,.2f}] {get_val('descricao') or ''}".strip(),
                                    get_val('categoria'),
                                    lote,
                                    get_val('banco'),
                                    get_val('agencia'),
                                    get_val('conta'),
                                    get_val('pix'),
                                    get_val('id_titulo_pagar'),
                                    get_val('num_orcom'),
                                    get_val('filial'),
                                    get_val('empresa'),
                                    None,  # data_pagamento
                                    get_val('tipo'),
                                    get_val('tipo_movimento'),
                                    get_val('situacao'),
                                    get_val('documento_dev'),
                                    get_val('liberacao'),
                                    get_val('empenho'),
                                    get_val('carne'),
                                    valor,  # valor_titulo = valor total original
                                    get_money('valor_antecipado'),
                                    get_money('valor_desconto'),
                                    get_money('valor_desconto_tributacao'),
                                    get_val('instrucao_pagamento'),
                                    get_val('grupo_conta'),
                                    get_val('seu_numero'),
                                    get_val('vinculado_lote'),
                                    get_val('lote_erp'),
                                    parcela_atual,
                                    num_parcelas
                                ))
                                inserted = cur.fetchone()
                                if inserted:
                                    parcela_ids_importacao.append(inserted[0])
                                importados += 1
                            
                            # Vincular todas as parcelas com titulo_original_id (usa o ID da primeira parcela)
                            if len(parcela_ids_importacao) > 1:
                                primeiro_id = parcela_ids_importacao[0]
                                cur.execute("""
                                    UPDATE titulos_importados 
                                    SET titulo_original_id = %s 
                                    WHERE id = ANY(%s)
                                """, (primeiro_id, parcela_ids_importacao))
                            
                            titulos_parcelados += 1
                        else:
                            # Título normal (valor <= 40k)
                            cur.execute("""
                                INSERT INTO titulos_importados 
                                (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, data_emissao, 
                                 descricao, categoria, lote_importacao, banco, agencia, conta, pix,
                                 id_titulo_pagar, num_orcom, filial, empresa, data_pagamento, tipo, tipo_movimento,
                                 situacao, documento_dev, liberacao, empenho, carne, valor_titulo, valor_antecipado,
                                 valor_desconto, valor_desconto_tributacao, instrucao_pagamento, grupo_conta, seu_numero,
                                 vinculado_lote, lote_erp)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                numero_titulo_original,
                                nome_fornecedor,
                                get_val('cod_fornecedor'),
                                get_val('cnpj_cpf'),
                                valor,
                                data_venc,
                                data_emissao,
                                get_val('descricao'),
                                get_val('categoria'),
                                lote,
                                get_val('banco'),
                                get_val('agencia'),
                                get_val('conta'),
                                get_val('pix'),
                                get_val('id_titulo_pagar'),
                                get_val('num_orcom'),
                                get_val('filial'),
                                get_val('empresa'),
                                None,  # data_pagamento
                                get_val('tipo'),
                                get_val('tipo_movimento'),
                                get_val('situacao'),
                                get_val('documento_dev'),
                                get_val('liberacao'),
                                get_val('empenho'),
                                get_val('carne'),
                                get_money('valor_titulo'),
                                get_money('valor_antecipado'),
                                get_money('valor_desconto'),
                                get_money('valor_desconto_tributacao'),
                                get_val('instrucao_pagamento'),
                                get_val('grupo_conta'),
                                get_val('seu_numero'),
                                get_val('vinculado_lote'),
                                get_val('lote_erp')
                            ))
                            importados += 1
                    except Exception as e:
                        erros.append(f"Linha {idx + 2}: {str(e)}")
                
                mensagem = f"{importados} novos títulos importados"
                detalhes = []
                if titulos_parcelados > 0:
                    detalhes.append(f"{titulos_parcelados} parcelados (> R$ 40k)")
                if titulos_duplicados > 0:
                    detalhes.append(f"{titulos_duplicados} ignorados (já existem)")
                if titulos_ignorados_data > 0:
                    detalhes.append(f"{titulos_ignorados_data} ignorados (vencimento <= 16/01/2026)")
                if detalhes:
                    mensagem += f" ({', '.join(detalhes)})"
                
                return {
                    "message": mensagem,
                    "lote": lote,
                    "total_linhas": len(df),
                    "importados": importados,
                    "titulos_parcelados": titulos_parcelados,
                    "titulos_duplicados": titulos_duplicados,
                    "titulos_ignorados_data": titulos_ignorados_data,
                    "erros": erros[:20] if erros else [],
                    "colunas_encontradas": list(df.columns)
                }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


@router.delete("/titulos/lote/{lote}")
async def delete_lote_titulos(lote: str):
    """Remove todos os títulos de um lote e registra na blacklist"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar todos os títulos do lote antes de excluir
            cur.execute("SELECT numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento FROM titulos_importados WHERE lote_importacao = %s", (lote,))
            titulos = cur.fetchall()
            
            # Registrar cada um na blacklist
            blacklisted = 0
            for titulo in titulos:
                chave = _gerar_chave_titulo(titulo.get('cod_fornecedor'), titulo['numero_titulo'])
                try:
                    cur.execute("""
                        INSERT INTO titulos_excluidos 
                        (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, chave_fornecedor_titulo, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'excluido_lote')
                        ON CONFLICT (chave_fornecedor_titulo) DO NOTHING
                    """, (
                        titulo['numero_titulo'], titulo['nome_fornecedor'],
                        titulo.get('cod_fornecedor'), titulo['cnpj_cpf'],
                        titulo['valor'], titulo['data_vencimento'], chave
                    ))
                    blacklisted += 1
                except Exception as e:
                    print(f"⚠️ Erro blacklist título: {e}")
            
            # Excluir o lote
            cur.execute("DELETE FROM titulos_importados WHERE lote_importacao = %s", (lote,))
            deleted = cur.rowcount
            return {"message": f"{deleted} títulos removidos do lote {lote} ({blacklisted} bloqueados para reimportação)"}


@router.delete("/titulos/{titulo_id}")
async def delete_titulo(titulo_id: int):
    """Remove um título específico e registra na blacklist para não ser reimportado"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar dados do título antes de excluir
            cur.execute("""
                SELECT numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, 
                       data_vencimento, parcela_numero, parcela_total, titulo_original_id 
                FROM titulos_importados WHERE id = %s
            """, (titulo_id,))
            titulo = cur.fetchone()
            if not titulo:
                raise HTTPException(status_code=404, detail="Título não encontrado")
            
            # Bloquear exclusão de títulos parcelados
            if titulo.get('parcela_numero') or titulo.get('parcela_total') or titulo.get('titulo_original_id'):
                raise HTTPException(
                    status_code=400, 
                    detail="Não é permitido excluir título parcelado. Junte as parcelas primeiro ou exclua o título original."
                )
            
            # Registrar na blacklist (chave = cod_fornecedor + titulo)
            chave = _gerar_chave_titulo(titulo.get('cod_fornecedor'), titulo['numero_titulo'])
            try:
                cur.execute("""
                    INSERT INTO titulos_excluidos 
                    (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, chave_fornecedor_titulo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chave_fornecedor_titulo) DO NOTHING
                """, (
                    titulo['numero_titulo'], titulo['nome_fornecedor'], 
                    titulo.get('cod_fornecedor'), titulo['cnpj_cpf'],
                    titulo['valor'], titulo['data_vencimento'], chave
                ))
            except Exception as e:
                print(f"⚠️ Erro ao registrar título na blacklist: {e}")
            
            # Agora excluir
            cur.execute("DELETE FROM titulos_importados WHERE id = %s", (titulo_id,))
            return {"message": f"Título removido e bloqueado para reimportação (chave: {chave})"}


# ==================== TÍTULOS EXCLUÍDOS (BLACKLIST) ====================

@router.get("/titulos-excluidos")
async def listar_titulos_excluidos():
    """Lista todos os títulos na blacklist (excluídos)"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, 
                       valor, data_vencimento, motivo, excluido_em
                FROM titulos_excluidos 
                ORDER BY excluido_em DESC
            """)
            rows = cur.fetchall()
            return [{
                "id": r['id'],
                "numero_titulo": r['numero_titulo'],
                "nome_fornecedor": r['nome_fornecedor'],
                "cod_fornecedor": r['cod_fornecedor'],
                "cnpj_cpf": r['cnpj_cpf'],
                "valor": float(r['valor']) if r['valor'] else None,
                "data_vencimento": str(r['data_vencimento']) if r['data_vencimento'] else None,
                "motivo": r['motivo'],
                "excluido_em": r['excluido_em'].isoformat() if r['excluido_em'] else None
            } for r in rows]


@router.delete("/titulos-excluidos/{excluido_id}")
async def recuperar_titulo_excluido(excluido_id: int):
    """Recupera um título da blacklist e reinsere como pendente"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar dados do título excluído
            cur.execute("SELECT * FROM titulos_excluidos WHERE id = %s", (excluido_id,))
            excluido = cur.fetchone()
            if not excluido:
                raise HTTPException(status_code=404, detail="Título excluído não encontrado")
            
            # Reinserir na tabela de títulos como pendente
            cur.execute("""
                INSERT INTO titulos_importados 
                (numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento, status, lote_importacao)
                VALUES (%s, %s, %s, %s, %s, %s, 'pendente', 'RECUPERADO')
                RETURNING id
            """, (
                excluido['numero_titulo'],
                excluido['nome_fornecedor'],
                excluido.get('cod_fornecedor'),
                excluido.get('cnpj_cpf'),
                excluido['valor'],
                excluido['data_vencimento']
            ))
            novo_id = cur.fetchone()['id']
            
            # Remover da blacklist
            cur.execute("DELETE FROM titulos_excluidos WHERE id = %s", (excluido_id,))
            
            return {"message": f"Título recuperado como pendente (ID: {novo_id})", "novo_id": novo_id}


class SplitTituloRequest(BaseModel):
    tipo: str  # 'iguais', 'residual', 'customizado'
    numParcelas: Optional[int] = 2
    valorPrimeira: Optional[float] = 40000.0
    valoresParcelas: Optional[List[float]] = None  # Array de valores para split customizado


@router.post("/titulos/{titulo_id}/split")
async def split_titulo(titulo_id: int, request: SplitTituloRequest):
    """Divide um título em múltiplas parcelas"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar o título original
            cur.execute("SELECT * FROM titulos_importados WHERE id = %s", (titulo_id,))
            titulo = cur.fetchone()
            
            if not titulo:
                raise HTTPException(status_code=404, detail="Título não encontrado")
            
            valor_total = float(titulo['valor'])
            parcelas_valores = []
            
            if request.tipo == 'iguais':
                # Dividir em parcelas iguais
                num = request.numParcelas or 2
                valor_parcela = round(valor_total / num, 2)
                # Ajustar última parcela para compensar arredondamento
                for i in range(num - 1):
                    parcelas_valores.append(valor_parcela)
                parcelas_valores.append(round(valor_total - sum(parcelas_valores), 2))
                
            elif request.tipo == 'residual':
                # R$40k + residual
                limite = request.valorPrimeira or 40000.0
                num_cheias = int(valor_total // limite)
                residual = round(valor_total % limite, 2)
                
                for i in range(num_cheias):
                    parcelas_valores.append(limite)
                if residual > 0:
                    parcelas_valores.append(residual)
                    
            elif request.tipo == 'customizado':
                # Se tiver array de valores, usar ele
                if request.valoresParcelas and len(request.valoresParcelas) >= 2:
                    # Validar que a soma bate com o total
                    soma = sum(request.valoresParcelas)
                    if abs(soma - valor_total) > 0.01:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Soma das parcelas ({soma:.2f}) não corresponde ao valor total ({valor_total:.2f})"
                        )
                    parcelas_valores = [round(v, 2) for v in request.valoresParcelas]
                else:
                    # Fallback: Valor customizado para primeira parcela (comportamento antigo)
                    primeira = request.valorPrimeira or (valor_total / 2)
                    if primeira >= valor_total:
                        raise HTTPException(status_code=400, detail="Valor da primeira parcela deve ser menor que o total")
                    parcelas_valores.append(round(primeira, 2))
                    parcelas_valores.append(round(valor_total - primeira, 2))
            
            if len(parcelas_valores) < 2:
                raise HTTPException(status_code=400, detail="Não foi possível dividir o título")
            
            # Criar os novos títulos
            novos_titulos = []
            lote_split = f"SPLIT-{titulo_id}-{len(parcelas_valores)}"
            
            for i, valor in enumerate(parcelas_valores, 1):
                cur.execute("""
                    INSERT INTO titulos_importados (
                        numero_titulo, cod_fornecedor, nome_fornecedor, cnpj_cpf,
                        valor, valor_titulo, data_vencimento, data_emissao, status, lote_importacao,
                        titulo_original_id, parcela_numero, parcela_total
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendente', %s, %s, %s, %s)
                    RETURNING id, numero_titulo, cod_fornecedor, nome_fornecedor, cnpj_cpf,
                              valor, valor_titulo, data_vencimento, data_emissao, status
                """, (
                    f"{titulo['numero_titulo']}-P{i}",
                    titulo['cod_fornecedor'],
                    titulo['nome_fornecedor'],
                    titulo['cnpj_cpf'],
                    valor,
                    valor_total,
                    titulo['data_vencimento'],
                    titulo['data_emissao'],
                    lote_split,
                    titulo_id,
                    i,
                    len(parcelas_valores)
                ))
                novo = cur.fetchone()
                novos_titulos.append({
                    "id": novo['id'],
                    "numero_titulo": novo['numero_titulo'],
                    "cod_fornecedor": novo['cod_fornecedor'],
                    "nome_fornecedor": novo['nome_fornecedor'],
                    "cnpj_cpf": novo['cnpj_cpf'],
                    "valor": float(novo['valor']),
                    "data_vencimento": str(novo['data_vencimento']) if novo['data_vencimento'] else None,
                    "data_emissao": str(novo['data_emissao']) if novo['data_emissao'] else None,
                    "status": novo['status'],
                    "tier": titulo.get('tier', 3) if 'tier' in titulo else 3,
                    "parcela_numero": i,
                    "parcela_total": len(parcelas_valores)
                })
            
            # Deletar o título original
            cur.execute("DELETE FROM titulos_importados WHERE id = %s", (titulo_id,))
            
            return {"message": f"Título dividido em {len(parcelas_valores)} parcelas", "titulos": novos_titulos}


@router.post("/titulos/{titulo_id}/merge")
async def merge_parcelas(titulo_id: int):
    """Junta todas as parcelas de volta em um único título original"""
    import re
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar o título (parcela) fornecido
            cur.execute("SELECT * FROM titulos_importados WHERE id = %s", (titulo_id,))
            parcela = cur.fetchone()
            
            if not parcela:
                raise HTTPException(status_code=404, detail="Título não encontrado")
            
            # Verificar se é uma parcela
            titulo_original_id = parcela.get('titulo_original_id')
            parcela_numero = parcela.get('parcela_numero')
            parcela_total = parcela.get('parcela_total')
            
            if not titulo_original_id and not (parcela_numero and parcela_total):
                raise HTTPException(status_code=400, detail="Este título não é uma parcela")
            
            if titulo_original_id:
                # Parcelas criadas via split manual (têm titulo_original_id)
                cur.execute("""
                    SELECT * FROM titulos_importados 
                    WHERE titulo_original_id = %s
                    ORDER BY parcela_numero
                """, (titulo_original_id,))
                parcelas = cur.fetchall()
            else:
                # Parcelas criadas na importação (NÃO têm titulo_original_id)
                # Encontrar irmãs pelo padrão do numero_titulo e mesmo fornecedor/data
                numero_titulo = parcela.get('numero_titulo', '')
                base_titulo = re.sub(r'\s*\(\d+/\d+\)$', '', numero_titulo)
                base_titulo = re.sub(r'-P\d+$', '', base_titulo)
                
                # Also try to find by titulo_original_id if this parcela itself has an ID
                # that other parcelas point to
                cur.execute("""
                    SELECT * FROM titulos_importados 
                    WHERE (
                        (parcela_numero IS NOT NULL
                         AND parcela_total IS NOT NULL
                         AND LOWER(nome_fornecedor) = LOWER(%s)
                         AND data_vencimento = %s
                         AND (
                             numero_titulo LIKE %s
                             OR numero_titulo LIKE %s
                         ))
                        OR titulo_original_id = %s
                    )
                    ORDER BY parcela_numero
                """, (
                    parcela['nome_fornecedor'],
                    parcela['data_vencimento'],
                    f"{base_titulo} (%",
                    f"{base_titulo}-P%",
                    parcela['id']  # titulo_original_id = this parcela's ID (for parcelas that point to first sibling)
                ))
                parcelas = cur.fetchall()
                
                # Se não encontrou irmãs pelo padrão, incluir pelo menos o próprio título
                if not parcelas:
                    parcelas = [parcela]
            
            if not parcelas:
                raise HTTPException(status_code=404, detail="Nenhuma parcela encontrada")
            
            # Calcular valor total
            valor_total = sum(float(p['valor']) for p in parcelas)
            
            # Usar dados da primeira parcela como base
            primeira = parcelas[0]
            
            # Extrair o número do título original (remover -P1, -P2, (1/3), etc)
            numero_titulo_original = primeira['numero_titulo']
            if numero_titulo_original:
                if '-P' in numero_titulo_original:
                    numero_titulo_original = numero_titulo_original.rsplit('-P', 1)[0]
                else:
                    numero_titulo_original = re.sub(r'\s*\(\d+/\d+\)$', '', numero_titulo_original)
            
            # Criar o título original restaurado
            cur.execute("""
                INSERT INTO titulos_importados (
                    numero_titulo, cod_fornecedor, nome_fornecedor, cnpj_cpf,
                    valor, data_vencimento, data_emissao, status, lote_importacao,
                    descricao, categoria, banco, agencia, conta, pix
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendente', %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                numero_titulo_original,
                primeira['cod_fornecedor'],
                primeira['nome_fornecedor'],
                primeira['cnpj_cpf'],
                valor_total,
                primeira['data_vencimento'],
                primeira['data_emissao'],
                f"MERGED-{titulo_original_id or parcela['id']}",
                # Limpar descrição de parcela (remove "[Parcela X/Y - ...]" do import)
                re.sub(r'^\[Parcela \d+/\d+.*?\]\s*', '', primeira.get('descricao') or '') or None,
                primeira.get('categoria'),
                primeira.get('banco'),
                primeira.get('agencia'),
                primeira.get('conta'),
                primeira.get('pix')
            ))
            novo_titulo = cur.fetchone()
            
            # Deletar todas as parcelas
            parcela_ids = [p['id'] for p in parcelas]
            cur.execute("DELETE FROM titulos_importados WHERE id = ANY(%s)", (parcela_ids,))
            
            # Buscar tier do fornecedor
            cur.execute("""
                SELECT tier FROM fornecedor_prioridades 
                WHERE LOWER(nome_fornecedor) = LOWER(%s)
            """, (primeira['nome_fornecedor'],))
            tier_row = cur.fetchone()
            tier = tier_row['tier'] if tier_row else 3
            
            return {
                "message": f"Parcelas reunificadas com sucesso. Valor total: R$ {valor_total:,.2f}",
                "titulo": {
                    "id": novo_titulo['id'],
                    "numero_titulo": numero_titulo_original,
                    "nome_fornecedor": primeira['nome_fornecedor'],
                    "cnpj_cpf": primeira['cnpj_cpf'],
                    "valor": valor_total,
                    "data_vencimento": str(primeira['data_vencimento']) if primeira['data_vencimento'] else None,
                    "status": "pendente",
                    "tier": tier
                },
                "parcelas_removidas": len(parcelas),
                "parcelas_ids": parcela_ids
            }


@router.put("/titulos/{titulo_id}/status")
async def update_titulo_status(titulo_id: int, status: str):
    """Atualiza o status de um título"""
    if status not in ['pendente', 'agendado', 'pago', 'cancelado']:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE titulos_importados 
                SET status = %s, atualizado_em = NOW()
                WHERE id = %s
            """, (status, titulo_id))
            return {"message": "Status atualizado com sucesso"}


class AgendarTituloRequest(BaseModel):
    titulo_id: int
    data_agendamento: Optional[str] = None  # None = voltar para pendente


@router.put("/titulos/{titulo_id}/agendar")
async def agendar_titulo(titulo_id: int, data_agendamento: Optional[str] = None):
    """Agenda um título para uma data específica ou volta para pendente"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if data_agendamento:
                # Validar data
                try:
                    data_obj = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
                except:
                    raise HTTPException(status_code=400, detail="Data inválida. Use formato YYYY-MM-DD")
                
                cur.execute("""
                    UPDATE titulos_importados 
                    SET data_agendamento = %s, status = 'agendado', atualizado_em = NOW()
                    WHERE id = %s
                """, (data_obj, titulo_id))
            else:
                # Voltar para pendente
                cur.execute("""
                    UPDATE titulos_importados 
                    SET data_agendamento = NULL, status = 'pendente', atualizado_em = NOW()
                    WHERE id = %s
                """, (titulo_id,))
            
            return {"message": "Título atualizado com sucesso", "titulo_id": titulo_id, "data_agendamento": data_agendamento}


@router.put("/titulos/agendar-lote")
async def agendar_titulos_lote(agendamentos: List[dict]):
    """Agenda múltiplos títulos de uma vez"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            atualizados = 0
            for ag in agendamentos:
                titulo_id = ag.get('titulo_id')
                data_ag = ag.get('data_agendamento')
                
                if data_ag:
                    cur.execute("""
                        UPDATE titulos_importados 
                        SET data_agendamento = %s, status = 'agendado', atualizado_em = NOW()
                        WHERE id = %s
                    """, (data_ag, titulo_id))
                else:
                    cur.execute("""
                        UPDATE titulos_importados 
                        SET data_agendamento = NULL, status = 'pendente', atualizado_em = NOW()
                        WHERE id = %s
                    """, (titulo_id,))
                atualizados += 1
            
            return {"message": f"{atualizados} títulos atualizados"}


# ==================== GERAÇÃO DE ROTEIRO ====================

@router.post("/roteiro/gerar")
async def gerar_roteiro(data_inicio: Optional[date] = None, dias: int = 5):
    """
    Gera o roteiro de pagamentos considerando:
    1. Exceções (prioridade máxima)
    2. Tier 1 - Fornecedores críticos
    3. Tier 2 - Alta prioridade
    4. Títulos mais vencidos/próximos do vencimento
    5. Tier 3 e 4 por ordem de vencimento
    """
    if not data_inicio:
        data_inicio = date.today()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Buscar configuração de orçamento
            cur.execute("SELECT orcamento_diario FROM configuracao_orcamento ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            orcamento_diario = float(row[0]) if row else 40000.0
            
            # Buscar exceções ativas
            cur.execute("""
                SELECT id, nome_fornecedor, valor_solicitado, data_necessidade, motivo
                FROM pagamento_excecoes
                WHERE status IN ('pendente', 'aprovado')
                AND data_necessidade BETWEEN %s AND %s
                ORDER BY prioridade_especial ASC, data_necessidade ASC
            """, (data_inicio, data_inicio + timedelta(days=dias)))
            excecoes = cur.fetchall()
            
            # Buscar títulos pendentes com tier
            cur.execute("""
                SELECT t.id, t.nome_fornecedor, t.valor, t.data_vencimento, t.numero_titulo,
                       COALESCE(fp.tier, 3) as tier,
                       COALESCE(fp.max_dias_atraso, 0) as max_atraso
                FROM titulos_importados t
                LEFT JOIN fornecedor_prioridades fp ON LOWER(t.nome_fornecedor) = LOWER(fp.nome_fornecedor)
                WHERE t.status = 'pendente'
                ORDER BY 
                    COALESCE(fp.tier, 3) ASC,
                    t.data_vencimento ASC,
                    t.valor DESC
            """)
            titulos = cur.fetchall()
            
            # Gerar roteiro por dia
            roteiro = []
            titulos_restantes = list(titulos)
            excecoes_restantes = list(excecoes)
            
            for i in range(dias):
                dia = data_inicio + timedelta(days=i)
                
                # Pular apenas domingo (6 = domingo)
                if dia.weekday() == 6:
                    continue
                
                orcamento_dia = orcamento_diario
                itens_dia = []
                
                # 1. Primeiro, processar exceções para este dia
                for exc in excecoes_restantes[:]:
                    if exc[3] <= dia and orcamento_dia >= float(exc[2]):
                        itens_dia.append({
                            "tipo": "excecao",
                            "excecao_id": exc[0],
                            "nome_fornecedor": exc[1],
                            "valor": float(exc[2]),
                            "motivo": f"⚡ EXCEÇÃO: {exc[4]}",
                            "tier": 0,
                            "data_vencimento": exc[3].isoformat()
                        })
                        orcamento_dia -= float(exc[2])
                        excecoes_restantes.remove(exc)
                
                # 2. Processar títulos por prioridade
                for titulo in titulos_restantes[:]:
                    if orcamento_dia <= 0:
                        break
                    
                    titulo_id, nome, valor, vencimento, numero, tier, max_atraso = titulo
                    valor = float(valor)
                    
                    # Verificar se deve pagar neste dia
                    dias_ate_vencimento = (vencimento - dia).days
                    
                    # Tier 1: Pagar antes do vencimento
                    # Tier 2: Pode pagar até 2 dias após
                    # Tier 3: Pode pagar até 5 dias após
                    # Tier 4: Pode pagar até 10 dias após
                    limite_atraso = {1: 0, 2: 2, 3: 5, 4: 10}.get(tier, 5)
                    limite_atraso = max(limite_atraso, max_atraso)
                    
                    # Se já passou do limite ou está no período de pagamento
                    if dias_ate_vencimento <= limite_atraso:
                        if valor <= orcamento_dia:
                            tier_label = {1: "🔴 CRÍTICO", 2: "🟠 ALTA", 3: "🟡 MÉDIA", 4: "🟢 BAIXA"}.get(tier, "⚪ NORMAL")
                            
                            itens_dia.append({
                                "tipo": "titulo",
                                "titulo_id": titulo_id,
                                "nome_fornecedor": nome,
                                "valor": valor,
                                "motivo": f"Tier {tier} ({tier_label}) - Venc: {vencimento.strftime('%d/%m')}",
                                "tier": tier,
                                "data_vencimento": vencimento.isoformat(),
                                "numero_titulo": numero
                            })
                            orcamento_dia -= valor
                            titulos_restantes.remove(titulo)
                
                total_dia = sum(item["valor"] for item in itens_dia)
                
                roteiro.append({
                    "data": dia.isoformat(),
                    "dia_semana": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][dia.weekday()],
                    "orcamento": orcamento_diario,
                    "total_agendado": total_dia,
                    "saldo": orcamento_diario - total_dia,
                    "itens": itens_dia
                })
            
            # Resumo
            total_geral = sum(dia["total_agendado"] for dia in roteiro)
            titulos_nao_agendados = len(titulos_restantes)
            valor_nao_agendado = sum(float(t[2]) for t in titulos_restantes)
            
            return {
                "data_geracao": datetime.now().isoformat(),
                "periodo": {
                    "inicio": data_inicio.isoformat(),
                    "fim": (data_inicio + timedelta(days=dias)).isoformat()
                },
                "orcamento_diario": orcamento_diario,
                "resumo": {
                    "total_agendado": total_geral,
                    "titulos_agendados": sum(len(dia["itens"]) for dia in roteiro),
                    "titulos_pendentes": titulos_nao_agendados,
                    "valor_pendente": valor_nao_agendado
                },
                "roteiro": roteiro
            }


@router.get("/resumo")
async def get_resumo_financeiro():
    """Retorna um resumo do cenário financeiro atual"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Total de títulos pendentes
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor), 0)
                FROM titulos_importados
                WHERE status = 'pendente'
            """)
            total_titulos, valor_total = cur.fetchone()
            
            # Títulos vencidos
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor), 0)
                FROM titulos_importados
                WHERE status = 'pendente' AND data_vencimento < CURRENT_DATE
            """)
            titulos_vencidos, valor_vencidos = cur.fetchone()
            
            # Vencendo hoje
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor), 0)
                FROM titulos_importados
                WHERE status = 'pendente' AND data_vencimento = CURRENT_DATE
            """)
            titulos_hoje, valor_hoje = cur.fetchone()
            
            # Vencendo esta semana
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor), 0)
                FROM titulos_importados
                WHERE status = 'pendente' 
                AND data_vencimento BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            """)
            titulos_semana, valor_semana = cur.fetchone()
            
            # Exceções ativas
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor_solicitado), 0)
                FROM pagamento_excecoes
                WHERE status IN ('pendente', 'aprovado')
            """)
            excecoes_ativas, valor_excecoes = cur.fetchone()
            
            # Por tier
            cur.execute("""
                SELECT COALESCE(fp.tier, 3) as tier, COUNT(*), COALESCE(SUM(t.valor), 0)
                FROM titulos_importados t
                LEFT JOIN fornecedor_prioridades fp ON LOWER(t.nome_fornecedor) = LOWER(fp.nome_fornecedor)
                WHERE t.status = 'pendente'
                GROUP BY COALESCE(fp.tier, 3)
                ORDER BY tier
            """)
            por_tier = {f"tier_{row[0]}": {"quantidade": row[1], "valor": float(row[2])} for row in cur.fetchall()}
            
            # Configuração
            cur.execute("SELECT orcamento_diario FROM configuracao_orcamento ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            orcamento = float(row[0]) if row else 40000.0
            
            return {
                "data_consulta": datetime.now().isoformat(),
                "orcamento_diario": orcamento,
                "titulos": {
                    "total": total_titulos,
                    "valor_total": float(valor_total),
                    "vencidos": {
                        "quantidade": titulos_vencidos,
                        "valor": float(valor_vencidos)
                    },
                    "vencendo_hoje": {
                        "quantidade": titulos_hoje,
                        "valor": float(valor_hoje)
                    },
                    "vencendo_semana": {
                        "quantidade": titulos_semana,
                        "valor": float(valor_semana)
                    }
                },
                "excecoes_ativas": {
                    "quantidade": excecoes_ativas,
                    "valor": float(valor_excecoes)
                },
                "por_tier": por_tier,
                "dias_para_quitar": round(float(valor_total) / orcamento, 1) if orcamento > 0 else 0
            }


@router.get("/fornecedores/recentes")
async def list_fornecedores_recentes(q: Optional[str] = None):
    """
    Lista fornecedores únicos dos títulos importados nos últimos 120 dias.
    Suporta busca por nome OU código do fornecedor com parâmetro ?q=termo
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q and len(q) >= 2:
                cur.execute("""
                    SELECT DISTINCT nome_fornecedor, cod_fornecedor
                    FROM titulos_importados
                    WHERE criado_em >= CURRENT_DATE - INTERVAL '120 days'
                    AND (
                        LOWER(nome_fornecedor) LIKE LOWER(%s)
                        OR cod_fornecedor LIKE %s
                    )
                    ORDER BY nome_fornecedor
                    LIMIT 20
                """, (f"%{q}%", f"%{q}%"))
            else:
                cur.execute("""
                    SELECT DISTINCT nome_fornecedor, cod_fornecedor
                    FROM titulos_importados
                    WHERE criado_em >= CURRENT_DATE - INTERVAL '120 days'
                    ORDER BY nome_fornecedor
                    LIMIT 50
                """)
            
            fornecedores = []
            for row in cur.fetchall():
                fornecedores.append({
                    "nome_fornecedor": row[0],
                    "cod_fornecedor": row[1]
                })
            
            return fornecedores


# ==================== CANCELAMENTO DE DIA ====================

def proximo_dia_util(data: date) -> date:
    """Retorna o próximo dia útil (segunda a sábado)"""
    prox = data + timedelta(days=1)
    while prox.weekday() == 6:  # Pula domingo
        prox += timedelta(days=1)
    return prox


@router.post("/dias/cancelar")
async def cancelar_dia_pagamento(data_cancelar: str, motivo: Optional[str] = None):
    """
    Cancela pagamentos de um dia específico.
    Todos os títulos agendados para este dia são movidos para o próximo dia útil.
    Efeito cascata: se o próximo dia já tiver títulos, também são empurrados.
    """
    try:
        data_obj = datetime.strptime(data_cancelar, '%Y-%m-%d').date()
    except:
        raise HTTPException(status_code=400, detail="Data inválida. Use formato YYYY-MM-DD")
    
    # Verificar se é domingo
    if data_obj.weekday() == 6:
        raise HTTPException(status_code=400, detail="Domingo não é dia de pagamento")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Criar tabela de dias cancelados se não existir
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dias_cancelados (
                    id SERIAL PRIMARY KEY,
                    data DATE NOT NULL UNIQUE,
                    motivo TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Registrar dia como cancelado
            cur.execute("""
                INSERT INTO dias_cancelados (data, motivo)
                VALUES (%s, %s)
                ON CONFLICT (data) DO UPDATE SET motivo = EXCLUDED.motivo
            """, (data_obj, motivo))
            
            # Buscar todos os títulos agendados para este dia e dias seguintes
            # Ordenados por data para fazer o efeito cascata correto
            cur.execute("""
                SELECT id, data_agendamento
                FROM titulos_importados
                WHERE status = 'agendado' AND data_agendamento >= %s
                ORDER BY data_agendamento ASC
            """, (data_obj,))
            titulos_agendados = cur.fetchall()
            
            if not titulos_agendados:
                return {
                    "message": f"Dia {data_cancelar} marcado como cancelado. Nenhum título para reagendar.",
                    "titulos_movidos": 0
                }
            
            # Agrupar títulos por dia
            titulos_por_dia = {}
            for titulo_id, data_ag in titulos_agendados:
                if data_ag not in titulos_por_dia:
                    titulos_por_dia[data_ag] = []
                titulos_por_dia[data_ag].append(titulo_id)
            
            # Buscar todos os dias cancelados
            cur.execute("SELECT data FROM dias_cancelados")
            dias_cancelados = {row[0] for row in cur.fetchall()}
            
            # Função para encontrar próximo dia disponível
            def encontrar_proximo_dia_disponivel(data_atual: date) -> date:
                prox = proximo_dia_util(data_atual)
                while prox in dias_cancelados:
                    prox = proximo_dia_util(prox)
                return prox
            
            # Reagendar em cascata
            titulos_movidos = 0
            datas_ordenadas = sorted(titulos_por_dia.keys())
            
            for data_atual in datas_ordenadas:
                if data_atual in dias_cancelados or data_atual == data_obj:
                    nova_data = encontrar_proximo_dia_disponivel(data_atual)
                    
                    # Mover títulos deste dia
                    for titulo_id in titulos_por_dia[data_atual]:
                        cur.execute("""
                            UPDATE titulos_importados
                            SET data_agendamento = %s
                            WHERE id = %s
                        """, (nova_data, titulo_id))
                        titulos_movidos += 1
                    
                    # Se a nova data já tinha títulos, eles precisarão ser movidos também
                    if nova_data in titulos_por_dia:
                        dias_cancelados.add(nova_data)
            
            dia_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][data_obj.weekday()]
            
            return {
                "message": f"{dia_semana} {data_cancelar} cancelado! {titulos_movidos} títulos reagendados.",
                "data_cancelada": data_cancelar,
                "motivo": motivo,
                "titulos_movidos": titulos_movidos
            }


@router.delete("/dias/cancelar/{data}")
async def remover_cancelamento_dia(data: str):
    """Remove o cancelamento de um dia (reativa o dia para pagamentos)"""
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
    except:
        raise HTTPException(status_code=400, detail="Data inválida. Use formato YYYY-MM-DD")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM dias_cancelados WHERE data = %s", (data_obj,))
            if cur.rowcount > 0:
                return {"message": f"Dia {data} reativado para pagamentos"}
            else:
                return {"message": f"Dia {data} não estava cancelado"}


@router.get("/dias/cancelados")
async def listar_dias_cancelados():
    """Lista todos os dias cancelados"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dias_cancelados (
                    id SERIAL PRIMARY KEY,
                    data DATE NOT NULL UNIQUE,
                    motivo TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                SELECT data, motivo, criado_em
                FROM dias_cancelados
                WHERE data >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY data DESC
            """)
            
            dias = []
            for row in cur.fetchall():
                dia_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][row[0].weekday()]
                dias.append({
                    "data": row[0].isoformat(),
                    "dia_semana": dia_semana,
                    "motivo": row[1],
                    "criado_em": row[2].isoformat() if row[2] else None
                })
            
            return dias
