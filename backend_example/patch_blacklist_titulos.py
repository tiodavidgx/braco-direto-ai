#!/usr/bin/env python3
"""
Patch: Implementa blacklist de títulos excluídos.
1. Cria tabela titulos_excluidos
2. Ajusta DELETE endpoints para registrar exclusão
3. Ajusta importação para checar blacklist (fornecedor + titulo)
"""

FILE = '/var/www/braco-direto-ai/backend_example/app/routes/gestao_pagamentos.py'

with open(FILE, 'r') as f:
    content = f.read()

changes = 0

# ============================================================
# 1. Adicionar função init_titulos_excluidos no início do arquivo
#    (após os imports/models, antes do primeiro endpoint)
# ============================================================

# Find the first @router to insert before it
first_router = content.find('@router.get("/orcamento")')
if first_router == -1:
    print("❌ Não encontrou @router.get('/orcamento')")
    exit(1)

init_code = '''
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
                # Índice único na chave composta
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_titulos_excluidos_chave
                    ON titulos_excluidos (chave_fornecedor_titulo)
                """)
    except Exception as e:
        print(f"⚠️ Erro ao criar tabela titulos_excluidos: {e}")

# Executar na inicialização do módulo
_ensure_titulos_excluidos_table()


def _gerar_chave_titulo(nome_fornecedor: str, numero_titulo: str) -> str:
    """Gera chave única: UPPER(LEFT(fornecedor, 20)) + '|' + TRIM(titulo)"""
    forn = (nome_fornecedor or '')[:20].upper().strip()
    tit = (numero_titulo or '').strip()
    # Remover sufixos de parcela para pegar a chave base
    # Ex: "13-P1" -> "13", "13 (1/2)" -> "13"
    import re
    tit_base = re.sub(r'[-\s]*P\d+$', '', tit)  # Remove -P1, -P2
    tit_base = re.sub(r'\s*\(\d+/\d+\)$', '', tit_base)  # Remove (1/2)
    return f"{forn}|{tit_base.upper()}"


'''

content = content[:first_router] + init_code + content[first_router:]
print("✅ Função init e _gerar_chave_titulo adicionadas")
changes += 1

# Need to re-find positions since content changed
# ============================================================
# 2. Ajustar DELETE /titulos/{titulo_id} para registrar na blacklist
# ============================================================

old_delete_titulo = '''@router.delete("/titulos/{titulo_id}")
async def delete_titulo(titulo_id: int):
    """Remove um título específico"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM titulos_importados WHERE id = %s", (titulo_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Título não encontrado")
            return {"message": "Título removido com sucesso"}'''

new_delete_titulo = '''@router.delete("/titulos/{titulo_id}")
async def delete_titulo(titulo_id: int):
    """Remove um título específico e registra na blacklist para não ser reimportado"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Buscar dados do título antes de excluir
            cur.execute("SELECT numero_titulo, nome_fornecedor, cod_fornecedor, cnpj_cpf, valor, data_vencimento FROM titulos_importados WHERE id = %s", (titulo_id,))
            titulo = cur.fetchone()
            if not titulo:
                raise HTTPException(status_code=404, detail="Título não encontrado")
            
            # Registrar na blacklist (chave = fornecedor + titulo)
            chave = _gerar_chave_titulo(titulo['nome_fornecedor'], titulo['numero_titulo'])
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
            return {"message": f"Título removido e bloqueado para reimportação (chave: {chave})"}'''

pos = content.find(old_delete_titulo)
if pos == -1:
    print("❌ Não encontrou DELETE /titulos/{titulo_id} original")
    # Try to find it with different formatting
    alt = '@router.delete("/titulos/{titulo_id}")'
    pos2 = content.find(alt)
    print(f"   Posição do decorator: {pos2}")
    if pos2 > 0:
        print(f"   Contexto: {content[pos2:pos2+300]}")
    exit(1)

content = content[:pos] + new_delete_titulo + content[pos + len(old_delete_titulo):]
print("✅ DELETE /titulos/{titulo_id} atualizado com blacklist")
changes += 1

# ============================================================
# 3. Ajustar DELETE /titulos/lote/{lote} para registrar na blacklist
# ============================================================

old_delete_lote = '''@router.delete("/titulos/lote/{lote}")
async def delete_lote_titulos(lote: str):
    """Remove todos os títulos de um lote de importação"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM titulos_importados WHERE lote_importacao = %s", (lote,))
            deleted = cur.rowcount
            return {"message": f"{deleted} títulos removidos do lote {lote}"}'''

new_delete_lote = '''@router.delete("/titulos/lote/{lote}")
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
                chave = _gerar_chave_titulo(titulo['nome_fornecedor'], titulo['numero_titulo'])
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
            return {"message": f"{deleted} títulos removidos do lote {lote} ({blacklisted} bloqueados para reimportação)"}'''

pos = content.find(old_delete_lote)
if pos == -1:
    print("❌ Não encontrou DELETE /titulos/lote/{lote} original")
    exit(1)

content = content[:pos] + new_delete_lote + content[pos + len(old_delete_lote):]
print("✅ DELETE /titulos/lote/{lote} atualizado com blacklist")
changes += 1

# ============================================================
# 4. Ajustar a verificação de duplicados na importação
#    Adicionar check na tabela titulos_excluidos
# ============================================================

# O check atual é:
old_check = '''                        cur.execute("""
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
                            continue  # Pular título duplicado'''

new_check = '''                        # Verificar duplicados na tabela de importados
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
                        chave_titulo = _gerar_chave_titulo(nome_fornecedor, numero_titulo_original)
                        cur.execute("""
                            SELECT id FROM titulos_excluidos 
                            WHERE chave_fornecedor_titulo = %s
                            LIMIT 1
                        """, (chave_titulo,))
                        
                        excluido = cur.fetchone()
                        if excluido:
                            titulos_duplicados += 1
                            continue  # Pular título da blacklist'''

pos = content.find(old_check)
if pos == -1:
    print("❌ Não encontrou o bloco de verificação de duplicados!")
    exit(1)

content = content[:pos] + new_check + content[pos + len(old_check):]
print("✅ Verificação de blacklist adicionada na importação")
changes += 1

# ============================================================
# 5. Adicionar import psycopg2.extras se não tiver
# ============================================================
if 'import psycopg2.extras' not in content and 'psycopg2.extras' in content:
    # Precisa adicionar o import
    import_pos = content.find('import psycopg2')
    if import_pos == -1:
        # Adicionar após os outros imports
        from_db_pos = content.find('from app.database')
        if from_db_pos != -1:
            line_end = content.find('\n', from_db_pos)
            content = content[:line_end+1] + 'import psycopg2.extras\n' + content[line_end+1:]
            print("✅ Import psycopg2.extras adicionado")
            changes += 1

# Check if psycopg2.extras is imported
if 'import psycopg2' not in content:
    # Find first import line
    first_import = content.find('from ')
    if first_import > 0:
        content = content[:first_import] + 'import psycopg2.extras\n' + content[first_import:]
        print("✅ Import psycopg2.extras adicionado no topo")
        changes += 1

# Salvar
with open(FILE + '.bak_blacklist', 'w') as f:
    with open(FILE, 'r') as f2:
        pass  # backup marker

with open(FILE, 'w') as f:
    f.write(content)

print(f"\n✅ Patch completo! {changes} alterações aplicadas.")
print("   - Tabela titulos_excluidos criada automaticamente")
print("   - DELETE individual registra na blacklist")  
print("   - DELETE por lote registra na blacklist")
print("   - Importação verifica blacklist (fornecedor+titulo)")
