"""
Rotas para receber dados do bot externo (vendas, montagem, nmresolve)

O bot local envia CSVs diários via HTTP POST.
Usa COPY do PostgreSQL para bulk insert eficiente (5M+ linhas).
Autenticação via X-Bot-Key header.
"""

import os
import io
import csv
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Query, BackgroundTasks
from app.database import get_db_connection

router = APIRouter()

# ============================================================
# Helpers
# ============================================================

def verificar_api_key(api_key: str):
    """Verifica se a API key do bot é válida"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bot_config WHERE api_key = %s AND ativo = TRUE", (api_key,))
        if not cur.fetchone():
            raise HTTPException(status_code=401, detail="API key inválida ou inativa")


def parse_date(value: str):
    """Tenta parsear data em vários formatos brasileiros"""
    if not value or value.strip() in ('', '-', 'null', 'None', 'N/A'):
        return None
    value = value.strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S',
                '%m/%d/%Y %I:%M:%S %p', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value: str):
    """Parse preservando componente de hora. Retorna datetime ou None."""
    if not value or value.strip() in ('', '-', 'null', 'None', 'N/A'):
        return None
    value = value.strip()
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',
                '%m/%d/%Y %I:%M:%S %p',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S',
                '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def clean_value(value: str):
    """Limpa valor para inserção"""
    if value is None:
        return None
    value = value.strip()
    if value.lower() in ('', '-', 'null', 'none', 'n/a', '\\n', 'nan', 'undefined', '#n/a', '#n/d'):
        return None
    return value


# Mapeamento de colunas do CSV para colunas do banco
COLUMN_MAP_VENDAS = {
    'identificador pedido': 'identificador_pedido',
    'identificador nf': 'identificador_nf',
    'identificador segunda nf': 'identificador_segunda_nf',
    'identificdor segunda nf': 'identificador_segunda_nf',  # typo no original
    'filial de saida': 'filial_saida',
    'filial saida segunda nf': 'filial_saida_segunda_nf',
    'numero nf': 'numero_nf',
    'numero segunda nf': 'numero_segunda_nf',
    'serie nf': 'serie_nf',
    'serie segunda nf': 'serie_segunda_nf',
    'filial de venda': 'filial_venda',
    'nome cliente': 'nome_cliente',
    'cpf cnpj cliente': 'cpf_cnpj_cliente',
    'cidade nf': 'cidade_nf',
    'uf nf': 'uf_nf',
    'data emissao': 'data_emissao',
    'data previsao entrega': 'data_previsao_entrega',
    'situacao time line': 'situacao_timeline',
    'data da entrega efetiva': 'data_entrega_efetiva',
    'deseja entrega': 'deseja_entrega',
    'tipo operação de venda': 'tipo_operacao_venda',
    'tipo operacao de venda': 'tipo_operacao_venda',
    'telefone cliente': 'telefone_cliente',
    'situacao nota': 'situacao_nota',
    'produto': 'produto',
    'nome produto': 'nome_produto',
}

COLUMN_MAP_NMRESOLVE = {
    'identificador pedido': 'identificador_pedido',
    'identificador nf': 'identificador_nf',
    'identificador segunda nf': 'identificador_segunda_nf',
    'identificdor segunda nf': 'identificador_segunda_nf',
    'filial de saida': 'filial_saida',
    'filial saida segunda nf': 'filial_saida_segunda_nf',
    'numero nf': 'numero_nf',
    'boletim': 'boletim',
    'modalidade': 'modalidade',
    'situacao do boletim': 'situacao_boletim',
    'situação do boletim': 'situacao_boletim',
    'situacao do servico': 'situacao_servico',
    'situação do serviço': 'situacao_servico',
    'id prestador': 'id_prestador',
    'prestador': 'prestador',
    'data finalização': 'data_finalizacao',
    'data finalizacao': 'data_finalizacao',
    'nome produto': 'nome_produto',
    'produto': 'produto',
}

COLUMN_MAP_MONTAGEM = {
    'identificador pedido': 'identificador_pedido',
    'identificador nf': 'identificador_nf',
    'filial saída': 'filial_saida',
    'filial saida': 'filial_saida',
    'filial venda': 'filial_venda',
    'filial montadora': 'filial_montadora',
    'nota fiscal': 'nota_fiscal',
    'série nota fiscal': 'serie_nota_fiscal',
    'serie nota fiscal': 'serie_nota_fiscal',
    'modalidade servico': 'modalidade_servico',
    'modalidade serviço': 'modalidade_servico',
    'data da previsão montagem': 'data_previsao_montagem',
    'data da previsao montagem': 'data_previsao_montagem',
    'data da montagem': 'data_montagem',
    'situação do boletim': 'situacao_boletim',
    'situacao do boletim': 'situacao_boletim',
    'nome do montador': 'nome_montador',
    'identificador do montador': 'identificador_montador',
    'produto': 'produto',
    'identificador boletim montagem': 'identificador_boletim_montagem',
}

# Mapeamento para a view nova "montagem_mes" (26 colunas)
COLUMN_MAP_MONTAGEM_MES = {
    'identificador pedido': 'identificador_pedido',
    'identificador nf': 'identificador_nf',
    'identificador boletim montagem': 'identificador_boletim_montagem',
    'filial saida': 'filial_saida',
    'filial saída': 'filial_saida',
    'filial venda': 'filial_venda',
    'filial montadora': 'filial_montadora',
    'nota fiscal': 'nota_fiscal',
    'serie nota fiscal': 'serie_nota_fiscal',
    'série nota fiscal': 'serie_nota_fiscal',
    'modalidade servico': 'modalidade_servico',
    'modalidade serviço': 'modalidade_servico',
    'data da previsao montagem': 'data_previsao_montagem',
    'data da previsão montagem': 'data_previsao_montagem',
    'data da emissao nf': 'data_emissao_nf',
    'data da emissão nf': 'data_emissao_nf',
    'data previsao entrega': 'data_previsao_entrega',
    'data previsão entrega': 'data_previsao_entrega',
    'data da entrega': 'data_entrega',
    'situacao do boletim': 'situacao_boletim',
    'situação do boletim': 'situacao_boletim',
    'situacao time line': 'situacao_timeline',
    'situação time line': 'situacao_timeline',
    'identificador do montador': 'identificador_montador',
    'nome do montador': 'nome_montador',
    'produto': 'produto',
    'nome produto': 'nome_produto',
    'uf': 'uf',
    'localidade': 'localidade',
    'bairro': 'bairro',
    'data da montagem': 'data_montagem',
    'data da agenda montagem': 'data_agenda_montagem',
    'observacao montagem': 'observacao_montagem',
    'observação montagem': 'observacao_montagem',
    'telefone completo': 'telefone_completo',
}

# Colunas de data por tabela
DATE_COLUMNS = {
    'vendas': ['data_emissao', 'data_previsao_entrega', 'data_entrega_efetiva'],
    'nmresolve': ['data_finalizacao'],
    'montagem': ['data_previsao_montagem', 'data_montagem'],
    'montagem_mes': [
        'data_previsao_montagem', 'data_emissao_nf', 'data_previsao_entrega',
        'data_entrega', 'data_montagem', 'data_agenda_montagem',
    ],
}

# Colunas que preservam componente de hora (TIMESTAMP no banco)
DATETIME_COLUMNS = {
    'montagem_mes': {'data_entrega', 'data_montagem', 'data_agenda_montagem'},
}

# Colunas do banco por tabela (ordem para INSERT)
DB_COLUMNS = {
    'vendas': [
        'identificador_pedido', 'identificador_nf', 'identificador_segunda_nf',
        'filial_saida', 'filial_saida_segunda_nf', 'numero_nf', 'numero_segunda_nf',
        'serie_nf', 'serie_segunda_nf', 'filial_venda', 'nome_cliente',
        'cpf_cnpj_cliente', 'cidade_nf', 'uf_nf', 'data_emissao',
        'data_previsao_entrega', 'situacao_timeline', 'data_entrega_efetiva',
        'deseja_entrega', 'tipo_operacao_venda', 'telefone_cliente',
        'situacao_nota', 'produto', 'nome_produto', 'lote_importacao',
    ],
    'nmresolve': [
        'identificador_pedido', 'identificador_nf', 'identificador_segunda_nf',
        'filial_saida', 'filial_saida_segunda_nf', 'numero_nf', 'boletim',
        'modalidade', 'situacao_boletim', 'situacao_servico', 'id_prestador',
        'prestador', 'data_finalizacao', 'nome_produto', 'produto', 'lote_importacao',
    ],
    'montagem': [
        'identificador_pedido', 'identificador_nf', 'filial_saida',
        'filial_venda', 'filial_montadora', 'nota_fiscal', 'serie_nota_fiscal',
        'modalidade_servico', 'data_previsao_montagem', 'data_montagem',
        'situacao_boletim', 'nome_montador', 'identificador_montador',
        'produto', 'identificador_boletim_montagem', 'lote_importacao',
    ],
    'montagem_mes': [
        'identificador_pedido', 'identificador_nf', 'identificador_boletim_montagem',
        'filial_saida', 'filial_venda', 'filial_montadora',
        'nota_fiscal', 'serie_nota_fiscal', 'modalidade_servico',
        'data_previsao_montagem', 'data_emissao_nf', 'data_previsao_entrega',
        'data_entrega', 'situacao_boletim', 'situacao_timeline',
        'identificador_montador', 'nome_montador', 'produto', 'nome_produto',
        'uf', 'localidade', 'bairro', 'data_montagem', 'data_agenda_montagem',
        'observacao_montagem', 'telefone_completo', 'lote_importacao',
    ],
}

TABLE_NAMES = {
    'vendas': 'bot_vendas',
    'nmresolve': 'bot_nmresolve',
    'montagem': 'bot_montagem',
    'montagem_mes': 'bot_montagem_mes',
}

COLUMN_MAPS = {
    'vendas': COLUMN_MAP_VENDAS,
    'nmresolve': COLUMN_MAP_NMRESOLVE,
    'montagem': COLUMN_MAP_MONTAGEM,
    'montagem_mes': COLUMN_MAP_MONTAGEM_MES,
}

# Chaves de deduplicação por tabela (import incremental)
DEDUP_KEYS = {
    'vendas': ['identificador_pedido', 'identificador_nf', 'identificador_segunda_nf'],
    'montagem': ['identificador_pedido', 'identificador_nf', 'produto'],
    'nmresolve': ['identificador_pedido', 'identificador_nf', 'boletim'],
    'montagem_mes': ['identificador_boletim_montagem', 'produto'],
}

# Mapeamento para atualizacoes_pedido
COLUMN_MAP_ATUALIZACOES = {
    'identificador pedido': 'identificador_pedido',
    'identificador nf': 'identificador_nf',
    'identificdor segunda nf': 'identificador_segunda_nf',
    'identificador segunda nf': 'identificador_segunda_nf',
    'situacao time line': 'situacao_timeline',
    'data da entrega efetiva': 'data_entrega_efetiva',
    'tipo operacao de venda': 'tipo_operacao_venda',
    'tipo operação de venda': 'tipo_operacao_venda',
}
ATUALIZACAO_KEYS = ['identificador_pedido', 'identificador_nf', 'identificador_segunda_nf']
ATUALIZACAO_UPDATE_COLS = ['situacao_timeline', 'data_entrega_efetiva', 'tipo_operacao_venda']
ATUALIZACAO_DATE_COLS = ['data_entrega_efetiva']


def process_csv_upload(file_content: bytes, tipo: str, filename: str):
    """
    Processa o CSV e faz bulk insert usando COPY para máxima performance.
    Retorna dict com estatísticas da importação.
    """
    start = time.time()
    lote = f"{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    column_map = COLUMN_MAPS[tipo]
    db_columns = DB_COLUMNS[tipo]
    date_cols = DATE_COLUMNS[tipo]
    datetime_cols = DATETIME_COLUMNS.get(tipo, set())
    table = TABLE_NAMES[tipo]

    # Decodificar CSV (tentar vários encodings)
    content_str = None
    for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252', 'iso-8859-1'):
        try:
            content_str = file_content.decode(enc)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    if content_str is None:
        raise HTTPException(status_code=400, detail="Não foi possível decodificar o arquivo. Verifique o encoding.")

    # Detectar separador (tab ou ;)
    first_line = content_str.split('\n')[0]
    if '\t' in first_line:
        delimiter = '\t'
    elif ';' in first_line:
        delimiter = ';'
    else:
        delimiter = ','

    reader = csv.DictReader(io.StringIO(content_str), delimiter=delimiter)

    # Mapear headers do CSV para colunas do banco
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Arquivo CSV vazio ou sem cabeçalho")

    # Log dos headers recebidos para debug
    headers_recebidos = [h.strip() for h in reader.fieldnames]
    print(f"[DADOS_BOT] Tipo: {tipo}, Arquivo: {filename}, Headers ({len(headers_recebidos)}): {headers_recebidos[:5]}...")

    csv_to_db = {}
    for csv_col in reader.fieldnames:
        # Normalizar: lowercase, remover acentos comuns, BOM, espaços extras
        normalized = csv_col.strip().lower()
        # Remover BOM e caracteres invisíveis
        normalized = normalized.lstrip('\ufeff\ufffe\xef\xbb\xbf')
        # Normalizar acentos comuns
        normalized = normalized.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
        normalized = normalized.replace('é', 'e').replace('ê', 'e')
        normalized = normalized.replace('í', 'i').replace('ó', 'o').replace('ô', 'o').replace('ú', 'u')
        normalized = normalized.replace('ç', 'c').replace('ñ', 'n')
        # Normalizar espaços múltiplos
        normalized = ' '.join(normalized.split())

        if normalized in column_map:
            csv_to_db[csv_col] = column_map[normalized]
        else:
            # Tentar match parcial: remover acentos do mapa também
            for map_key, map_val in column_map.items():
                map_norm = map_key.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
                map_norm = map_norm.replace('é', 'e').replace('ê', 'e')
                map_norm = map_norm.replace('í', 'i').replace('ó', 'o').replace('ô', 'o').replace('ú', 'u')
                map_norm = map_norm.replace('ç', 'c').replace('ñ', 'n')
                if normalized == map_norm:
                    csv_to_db[csv_col] = map_val
                    break

    mapped_db_cols = set(csv_to_db.values())
    print(f"[DADOS_BOT] Colunas mapeadas: {len(csv_to_db)}/{len(headers_recebidos)} -> {list(mapped_db_cols)[:5]}...")

    if len(csv_to_db) == 0:
        raise HTTPException(status_code=400, detail=f"Nenhum cabeçalho do CSV corresponde às colunas esperadas. Headers recebidos: {headers_recebidos}")

    # Validar que o CSV realmente pertence ao tipo informado
    # Cada tipo possui colunas exclusivas que não existem nos outros tipos
    REQUIRED_EXCLUSIVE_COLS = {
        'vendas': {'nome_cliente', 'cpf_cnpj_cliente', 'cidade_nf'},
        'nmresolve': {'boletim', 'modalidade', 'situacao_boletim'},
        'montagem': {'filial_montadora', 'nome_montador', 'identificador_boletim_montagem'},
    }
    required = REQUIRED_EXCLUSIVE_COLS.get(tipo, set())
    if required:
        found_exclusive = mapped_db_cols & required
        if len(found_exclusive) == 0:
            # Tentar identificar o tipo correto com base nos headers
            detected = None
            for check_tipo, check_cols in REQUIRED_EXCLUSIVE_COLS.items():
                if check_tipo == tipo:
                    continue
                # Verificar se os headers mapeiam melhor para outro tipo
                check_map = COLUMN_MAPS[check_tipo]
                check_matched = set()
                for csv_col in reader.fieldnames:
                    n = csv_col.strip().lower()
                    n = n.lstrip('\ufeff\ufffe\xef\xbb\xbf')
                    n = n.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
                    n = n.replace('é', 'e').replace('ê', 'e')
                    n = n.replace('í', 'i').replace('ó', 'o').replace('ô', 'o').replace('ú', 'u')
                    n = n.replace('ç', 'c').replace('ñ', 'n')
                    n = ' '.join(n.split())
                    if n in check_map:
                        check_matched.add(check_map[n])
                if check_matched & check_cols:
                    detected = check_tipo
                    break
            hint = f" Os headers parecem ser do tipo '{detected}'." if detected else ""
            raise HTTPException(
                status_code=400,
                detail=f"Os headers do CSV não correspondem ao tipo '{tipo}'. "
                       f"Esperava colunas como {required} mas encontrou {mapped_db_cols}.{hint} "
                       f"Verifique se está enviando o arquivo correto para o endpoint correto."
            )

    # Achar coluna CSV que mapeia para identificador_pedido
    csv_col_pedido = None
    for c, d in csv_to_db.items():
        if d == 'identificador_pedido':
            csv_col_pedido = c
            break

    # Gerar buffer COPY (formato TSV para o PostgreSQL)
    copy_buffer = io.StringIO()
    linhas_recebidas = 0
    linhas_ignoradas = 0

    for row in reader:
        linhas_recebidas += 1

        # Pular linhas com identificador_pedido nulo/vazio
        # Checa pela coluna mapeada OU se não achou mapeamento
        skip = False
        if csv_col_pedido:
            val_pedido = clean_value(row.get(csv_col_pedido, ''))
            if val_pedido is None:
                skip = True
        else:
            # Sem coluna mapeada = não tem como inserir identificador_pedido
            skip = True
        if skip:
            linhas_ignoradas += 1
            continue

        values = []
        for db_col in db_columns:
            if db_col == 'lote_importacao':
                values.append(lote)
                continue

            # Achar a coluna CSV correspondente
            csv_col = None
            for c, d in csv_to_db.items():
                if d == db_col:
                    csv_col = c
                    break

            if csv_col is None:
                values.append('\\N')  # NULL no formato COPY
                continue

            raw = clean_value(row.get(csv_col, ''))
            if raw is None:
                values.append('\\N')
            elif db_col in datetime_cols:
                parsed = parse_datetime(raw)
                values.append(parsed.strftime('%Y-%m-%d %H:%M:%S') if parsed else '\\N')
            elif db_col in date_cols:
                parsed = parse_date(raw)
                values.append(str(parsed) if parsed else '\\N')
            else:
                # Escapar tabs e newlines para formato COPY
                safe = raw.replace('\\', '\\\\').replace('\t', ' ').replace('\n', ' ').replace('\r', '')
                values.append(safe)

        copy_buffer.write('\t'.join(values) + '\n')

    if linhas_recebidas == 0:
        raise HTTPException(status_code=400, detail="Arquivo CSV sem dados")

    linhas_validas = linhas_recebidas - linhas_ignoradas
    if linhas_validas == 0:
        raise HTTPException(status_code=400, detail=f"Todas as {linhas_recebidas} linhas foram ignoradas (identificador_pedido nulo)")

    # Incremental: staging + UPSERT (INSERT ON CONFLICT DO UPDATE)
    copy_buffer.seek(0)
    staging = f"_staging_{table}"
    # Unique constraints por tabela (devem existir no banco)
    constraint_names = {
        'vendas': 'bot_vendas_dedup_uq',
        'nmresolve': 'bot_nmresolve_dedup_uq',
        'montagem': 'bot_montagem_dedup_uq',
        'montagem_mes': 'bot_montagem_mes_dedup_uq',
    }
    constraint = constraint_names[tipo]

    # Tabelas que fazem UPDATE em conflito (atualizam campos mutáveis).
    # Para as demais, mantém o DO NOTHING histórico.
    UPSERT_TABLES = {'montagem_mes'}

    with get_db_connection() as conn:
        cur = conn.cursor()
        columns_str = ', '.join(db_columns)

        # 1. Criar tabela temporária
        cur.execute(f"CREATE TEMP TABLE {staging} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
        for col in db_columns:
            cur.execute(f"ALTER TABLE {staging} ALTER COLUMN {col} DROP NOT NULL")

        # 2. COPY para staging
        cur.copy_expert(
            f"COPY {staging} ({columns_str}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
            copy_buffer
        )

        # 3. Remover nulos da staging
        cur.execute(f"DELETE FROM {staging} WHERE identificador_pedido IS NULL")
        linhas_nulas_removidas = cur.rowcount or 0
        linhas_ignoradas += linhas_nulas_removidas

        # 4. Contar staging
        cur.execute(f"SELECT count(*) FROM {staging}")
        total_staging = cur.fetchone()[0]

        # 5. UPSERT — instantâneo com unique constraint
        if tipo in UPSERT_TABLES:
            dedup_cols = set(DEDUP_KEYS.get(tipo, []))
            # Colunas a atualizar = todas, exceto as chaves de dedup e lote
            update_cols = [
                c for c in db_columns
                if c not in dedup_cols and c != 'lote_importacao'
            ]
            set_clause = ', '.join(
                f"{c} = EXCLUDED.{c}" for c in update_cols
            )
            cur.execute(f"""
                INSERT INTO {table} ({columns_str})
                SELECT {columns_str} FROM {staging}
                ON CONFLICT ON CONSTRAINT {constraint} DO UPDATE SET
                    {set_clause},
                    lote_importacao = EXCLUDED.lote_importacao
            """)
            linhas_afetadas = cur.rowcount or 0
            # Com DO UPDATE, rowcount soma inserts + updates. Não dá pra
            # separar sem xmax, então reportamos tudo como "processadas".
            linhas_inseridas = linhas_afetadas
            linhas_duplicadas = 0
        else:
            cur.execute(f"""
                INSERT INTO {table} ({columns_str})
                SELECT {columns_str} FROM {staging}
                ON CONFLICT ON CONSTRAINT {constraint} DO NOTHING
            """)
            linhas_inseridas = cur.rowcount or 0
            linhas_duplicadas = total_staging - linhas_inseridas

        # Log
        duracao = int((time.time() - start) * 1000)
        cur.execute("""
            INSERT INTO bot_import_log (tipo, lote, arquivo_nome, linhas_recebidas, linhas_inseridas, linhas_ignoradas, duracao_ms, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (tipo, lote, filename, linhas_recebidas, linhas_inseridas, linhas_ignoradas + linhas_duplicadas, duracao, 'sucesso'))
        print(f"[DADOS_BOT] {tipo}: {linhas_inseridas} novas, {linhas_duplicadas} já existentes, {duracao}ms", flush=True)

    duracao = int((time.time() - start) * 1000)
    return {
        "status": "sucesso",
        "tipo": tipo,
        "lote": lote,
        "arquivo": filename,
        "linhas_recebidas": linhas_recebidas,
        "linhas_ignoradas": linhas_ignoradas,
        "linhas_inseridas": linhas_inseridas,
        "linhas_duplicadas_ignoradas": linhas_duplicadas,
        "duracao_ms": duracao,
    }


# ============================================================
# Endpoints
# ============================================================

def _process_in_background(content: bytes, tipo: str, filename: str):
    """Processa CSV em background thread para não bloquear o servidor."""
    try:
        result = process_csv_upload(content, tipo, filename)
        print(f"[DADOS_BOT] Background OK: {tipo} - {result.get('linhas_inseridas', 0)} linhas em {result.get('duracao_ms', 0)}ms", flush=True)
    except Exception as e:
        print(f"[DADOS_BOT] Background ERRO: {tipo} - {e}", flush=True)
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO bot_import_log (tipo, lote, arquivo_nome, status, erro)
                    VALUES (%s, %s, %s, %s, %s)
                """, (tipo, f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}", filename, 'erro', str(e)[:500]))
                conn.commit()
        except Exception as log_err:
            print(f"[DADOS_BOT] Falha ao logar erro: {log_err}", flush=True)


@router.post("/upload/atualizacoes_pedido")
async def upload_atualizacoes_pedido(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
):
    """
    Recebe CSV de atualizações de pedido e atualiza bot_vendas em background.

    Chaves: identificador_pedido + identificador_nf + identificador_segunda_nf
    Atualiza: situacao_timeline, data_entrega_efetiva, tipo_operacao_venda
    """
    verificar_api_key(x_bot_key)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    filename = file.filename
    tamanho_mb = round(len(content) / (1024 * 1024), 2)

    background_tasks.add_task(_process_atualizacao_background, content, filename)

    return {
        "status": "processando",
        "mensagem": f"Arquivo {filename} ({tamanho_mb} MB) recebido. Atualizações em background.",
        "tipo": "atualizacoes_pedido",
        "arquivo": filename,
        "tamanho_mb": tamanho_mb,
    }


@router.post("/upload/{tipo}")
async def upload_dados_bot(
    tipo: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
):
    """
    Recebe CSV do bot e faz bulk insert em background.
    
    - **tipo**: vendas | nmresolve | montagem | montagem_mes
    - **file**: arquivo CSV (tab ou ; separated)
    - **X-Bot-Key**: chave de autenticação do bot
    
    Retorna imediatamente e processa em background.
    """
    # Validar tipo
    if tipo not in ('vendas', 'nmresolve', 'montagem', 'montagem_mes'):
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}. Use: vendas, nmresolve, montagem, montagem_mes")

    # Autenticar
    verificar_api_key(x_bot_key)

    # Validar arquivo
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    # Ler conteúdo (precisa ler ANTES de ir pro background, pois o file fecha)
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    filename = file.filename
    tamanho_mb = round(len(content) / (1024 * 1024), 2)

    # Agendar processamento em background
    background_tasks.add_task(_process_in_background, content, tipo, filename)

    return {
        "status": "processando",
        "mensagem": f"Arquivo {filename} ({tamanho_mb} MB) recebido. Processamento em background.",
        "tipo": tipo,
        "arquivo": filename,
        "tamanho_mb": tamanho_mb,
    }


@router.get("/status")
async def status_importacoes(
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
    limit: int = Query(20, ge=1, le=100),
):
    """Retorna últimas importações do bot"""
    verificar_api_key(x_bot_key)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT tipo, lote, arquivo_nome, linhas_recebidas, linhas_inseridas,
                   linhas_ignoradas, duracao_ms, status, erro, importado_em
            FROM bot_import_log
            ORDER BY importado_em DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

        # Contagem total por tabela
        counts = {}
        for tabela in ('bot_vendas', 'bot_nmresolve', 'bot_montagem'):
            cur.execute(f"SELECT COUNT(*) FROM {tabela}")
            counts[tabela] = cur.fetchone()[0]

    return {
        "tabelas": counts,
        "ultimas_importacoes": [
            {
                "tipo": r[0], "lote": r[1], "arquivo": r[2],
                "linhas_recebidas": r[3], "linhas_inseridas": r[4],
                "linhas_ignoradas": r[5], "duracao_ms": r[6],
                "status": r[7], "erro": r[8],
                "importado_em": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ],
    }


@router.get("/ultima-atualizacao")
async def ultima_atualizacao(
    authorization: str = Header(None, alias="Authorization"),
):
    """Retorna a data da última importação de cada tabela do bot."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        result = {}
        for tabela in ('bot_vendas', 'bot_nmresolve', 'bot_montagem'):
            cur.execute(f"SELECT MAX(importado_em) FROM {tabela}")
            row = cur.fetchone()
            result[tabela] = row[0].isoformat() if row and row[0] else None
        # Última atualização de pedidos (via bot_import_log)
        cur.execute("SELECT MAX(importado_em) FROM bot_import_log WHERE tipo = 'atualizacoes_pedido' AND status = 'sucesso'")
        row = cur.fetchone()
        result['atualizacoes_pedido'] = row[0].isoformat() if row and row[0] else None
    return result


@router.get("/buscar/{id_pedido}")
async def buscar_dados_pedido(
    id_pedido: str,
    x_bot_key: str = Header(None, alias="X-Bot-Key"),
    authorization: str = Header(None, alias="Authorization"),
):
    """
    Busca dados de um pedido em todas as tabelas do bot.
    Usado pelo CRM para preenchimento automático.
    
    Aceita autenticação via X-Bot-Key OU via Bearer token do sistema.
    """
    # Aceitar bot key OU Bearer token do JWT do sistema
    if x_bot_key:
        verificar_api_key(x_bot_key)
    elif authorization and authorization.startswith("Bearer "):
        pass  # JWT já verificado pelo middleware do sistema
    # Permitir acesso sem auth quando chamado internamente

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Buscar TODAS as vendas/produtos desse pedido (um pedido pode ter vários produtos)
        cur.execute("""
            SELECT DISTINCT ON (identificador_nf, identificador_segunda_nf, produto)
                   identificador_pedido, nome_cliente, telefone_cliente, cpf_cnpj_cliente,
                   cidade_nf, uf_nf, data_emissao, data_previsao_entrega, situacao_timeline,
                   data_entrega_efetiva, tipo_operacao_venda, situacao_nota, produto, nome_produto,
                   identificador_nf, numero_nf, filial_venda, deseja_entrega, serie_nf, filial_saida
            FROM bot_vendas
            WHERE identificador_pedido = %s
            ORDER BY identificador_nf, identificador_segunda_nf, produto, importado_em DESC
        """, (id_pedido,))
        venda_rows = cur.fetchall()

        # Dados do cliente (do primeiro registro)
        cliente = None
        produtos = []
        if venda_rows:
            r = venda_rows[0]
            cliente = {
                "identificador_pedido": r[0],
                "nome_cliente": r[1],
                "telefone_cliente": r[2],
                "cpf_cnpj_cliente": r[3],
                "cidade_nf": r[4],
                "uf_nf": r[5],
                "data_emissao": str(r[6]) if r[6] else None,
                "data_previsao_entrega": str(r[7]) if r[7] else None,
                "situacao_timeline": r[8],
                "data_entrega_efetiva": str(r[9]) if r[9] else None,
                "tipo_operacao_venda": r[10],
                "filial_venda": r[16],
                "deseja_entrega": r[17],
                "filial_saida": r[19],
            }
            # Lista de produtos do pedido
            for row in venda_rows:
                produtos.append({
                    "produto": row[12],
                    "nome_produto": row[13],
                    "identificador_nf": row[14],
                    "numero_nf": row[15],
                    "situacao_nota": row[11],
                    "serie_nf": row[18],
                })

        # Buscar NM Resolves
        cur.execute("""
            SELECT boletim, modalidade, situacao_boletim, situacao_servico,
                   id_prestador, prestador, data_finalizacao, nome_produto,
                   identificador_nf, produto
            FROM bot_nmresolve
            WHERE identificador_pedido = %s
            ORDER BY importado_em DESC
        """, (id_pedido,))
        nmresolve = [
            {
                "boletim": r[0], "modalidade": r[1], "situacao_boletim": r[2],
                "situacao_servico": r[3], "id_prestador": r[4], "prestador": r[5],
                "data_finalizacao": str(r[6]) if r[6] else None, "nome_produto": r[7],
                "identificador_nf": r[8], "produto": r[9],
            }
            for r in cur.fetchall()
        ]

        # Buscar Montagens
        cur.execute("""
            SELECT nota_fiscal, modalidade_servico, data_previsao_montagem, data_montagem,
                   situacao_boletim, nome_montador, identificador_montador,
                   identificador_nf, produto, identificador_boletim_montagem
            FROM bot_montagem
            WHERE identificador_pedido = %s
            ORDER BY importado_em DESC
        """, (id_pedido,))
        montagem = [
            {
                "nota_fiscal": r[0], "modalidade_servico": r[1],
                "data_previsao_montagem": str(r[2]) if r[2] else None,
                "data_montagem": str(r[3]) if r[3] else None,
                "situacao_boletim": r[4], "nome_montador": r[5],
                "identificador_montador": r[6], "identificador_nf": r[7],
                "produto": r[8], "identificador_boletim_montagem": r[9],
            }
            for r in cur.fetchall()
        ]

    if not cliente and not nmresolve and not montagem:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado para este pedido")

    return {
        "id_pedido": id_pedido,
        "cliente": cliente,
        "produtos": produtos,
        "nmresolve": nmresolve,
        "montagem": montagem,
    }


@router.delete("/limpar/{tipo}")
async def limpar_tabela(
    tipo: str,
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
    confirmar: bool = Query(False),
):
    """Limpa todos os dados de uma tabela (para reimportação completa)"""
    if tipo not in ('vendas', 'nmresolve', 'montagem'):
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")

    verificar_api_key(x_bot_key)

    if not confirmar:
        raise HTTPException(status_code=400, detail="Adicione ?confirmar=true para confirmar a limpeza")

    table = TABLE_NAMES[tipo]
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY")
        cur.execute("""
            INSERT INTO bot_import_log (tipo, lote, arquivo_nome, status, erro)
            VALUES (%s, %s, %s, %s, %s)
        """, (tipo, f"truncate_{datetime.now().strftime('%Y%m%d_%H%M%S')}", '', 'sucesso', 'Tabela limpa via API'))

    return {"status": "sucesso", "mensagem": f"Tabela {table} limpa com sucesso"}


def process_atualizacoes_pedido(file_content: bytes, filename: str):
    """
    Processa CSV de atualizacoes_pedido e faz UPDATE na bot_vendas.
    Chaves: identificador_pedido + identificador_nf + identificador_segunda_nf
    Atualiza: situacao_timeline, data_entrega_efetiva, tipo_operacao_venda
    """
    start = time.time()
    lote = f"atualizacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Decodificar CSV
    content_str = None
    for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252', 'iso-8859-1'):
        try:
            content_str = file_content.decode(enc)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    if content_str is None:
        raise HTTPException(status_code=400, detail="Não foi possível decodificar o arquivo.")

    # Detectar separador
    first_line = content_str.split('\n')[0]
    if '\t' in first_line:
        delimiter = '\t'
    elif ';' in first_line:
        delimiter = ';'
    else:
        delimiter = ','

    reader = csv.DictReader(io.StringIO(content_str), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Arquivo CSV vazio ou sem cabeçalho")

    # Mapear headers
    csv_to_db = {}
    for csv_col in reader.fieldnames:
        normalized = csv_col.strip().lower()
        normalized = normalized.lstrip('\ufeff\ufffe\xef\xbb\xbf')
        normalized = normalized.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
        normalized = normalized.replace('é', 'e').replace('ê', 'e')
        normalized = normalized.replace('í', 'i').replace('ó', 'o').replace('ô', 'o').replace('ú', 'u')
        normalized = normalized.replace('ç', 'c').replace('ñ', 'n')
        normalized = ' '.join(normalized.split())
        if normalized in COLUMN_MAP_ATUALIZACOES:
            csv_to_db[csv_col] = COLUMN_MAP_ATUALIZACOES[normalized]

    print(f"[ATUALIZACOES] Arquivo: {filename}, Colunas mapeadas: {list(csv_to_db.values())}")

    # Verificar se temos as colunas-chave
    mapped_cols = set(csv_to_db.values())
    for key in ATUALIZACAO_KEYS:
        if key not in mapped_cols:
            raise HTTPException(status_code=400, detail=f"Coluna chave '{key}' não encontrada no CSV")

    # Achar colunas CSV para cada DB col
    def get_csv_col(db_col):
        for c, d in csv_to_db.items():
            if d == db_col:
                return c
        return None

    linhas_recebidas = 0
    linhas_atualizadas = 0
    linhas_ignoradas = 0

    with get_db_connection() as conn:
        cur = conn.cursor()

        for row in reader:
            linhas_recebidas += 1

            # Extrair chaves
            key_pedido = clean_value(row.get(get_csv_col('identificador_pedido'), ''))
            key_nf = clean_value(row.get(get_csv_col('identificador_nf'), ''))
            key_segunda_nf = clean_value(row.get(get_csv_col('identificador_segunda_nf'), ''))

            if not key_pedido:
                linhas_ignoradas += 1
                continue

            # Montar SET clause apenas com colunas presentes
            set_parts = []
            params = []
            for col in ATUALIZACAO_UPDATE_COLS:
                csv_col = get_csv_col(col)
                if csv_col is None:
                    continue
                raw = clean_value(row.get(csv_col, ''))
                if col in ATUALIZACAO_DATE_COLS:
                    val = parse_date(raw) if raw else None
                else:
                    val = raw
                set_parts.append(f"{col} = %s")
                params.append(val)

            if not set_parts:
                linhas_ignoradas += 1
                continue

            set_parts.append("updated_at = NOW()")

            # WHERE com IS NOT DISTINCT FROM para NULLs
            where = """
                identificador_pedido = %s
                AND identificador_nf IS NOT DISTINCT FROM %s
                AND identificador_segunda_nf IS NOT DISTINCT FROM %s
            """
            params.extend([key_pedido, key_nf, key_segunda_nf])

            cur.execute(
                f"UPDATE bot_vendas SET {', '.join(set_parts)} WHERE {where}",
                params
            )
            linhas_atualizadas += cur.rowcount

        # Log da importação
        duracao = int((time.time() - start) * 1000)
        cur.execute("""
            INSERT INTO bot_import_log (tipo, lote, arquivo_nome, linhas_recebidas, linhas_inseridas, linhas_ignoradas, duracao_ms, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('atualizacoes_pedido', lote, filename, linhas_recebidas, linhas_atualizadas, linhas_ignoradas, duracao, 'sucesso'))
        conn.commit()

    duracao = int((time.time() - start) * 1000)
    return {
        "status": "sucesso",
        "tipo": "atualizacoes_pedido",
        "lote": lote,
        "arquivo": filename,
        "linhas_recebidas": linhas_recebidas,
        "linhas_atualizadas": linhas_atualizadas,
        "linhas_ignoradas": linhas_ignoradas,
        "duracao_ms": duracao,
    }


def _process_atualizacao_background(content: bytes, filename: str):
    try:
        process_atualizacoes_pedido(content, filename)
    except Exception as e:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO bot_import_log (tipo, lote, arquivo_nome, status, erro)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('atualizacoes_pedido', f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}", filename, 'erro', str(e)))
        except Exception:
            pass



