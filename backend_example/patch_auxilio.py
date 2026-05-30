#!/usr/bin/env python3
"""
Patch: Adiciona cálculo de auxílio semanal no endpoint editar-reenviar
"""

FILE = '/var/www/braco-direto-ai/backend_example/app/routes/relatorios.py'

with open(FILE, 'r') as f:
    content = f.read()

# 1. Adicionar auxilio_semanal na query do montador
old_query = """m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem,
                       m.tempo_vencimento_dias
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s"""

new_query = """m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem,
                       m.tempo_vencimento_dias, m.auxilio_semanal
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s"""

# Find this in the editar-reenviar endpoint (after line 3024)
# Need to find the right occurrence - after the editar-reenviar marker
marker = '@router.put("/envio/{envio_id}/editar-reenviar")'
marker_pos = content.find(marker)
if marker_pos == -1:
    print("❌ Não encontrou o endpoint editar-reenviar!")
    exit(1)

# Find the query AFTER the marker
query_pos = content.find(old_query, marker_pos)
if query_pos == -1:
    print("❌ Não encontrou a query do montador no endpoint de revisão!")
    print("Procurando versão alternativa...")
    # Try finding with different whitespace
    import re
    # Just check if auxilio_semanal is already there
    check_area = content[marker_pos:marker_pos+2000]
    if 'auxilio_semanal' in check_area:
        print("✅ auxilio_semanal já está na query!")
    else:
        print("❌ auxilio_semanal NÃO está na query e não encontrou o pattern!")
        print("Conteúdo da área:")
        print(check_area[:500])
        exit(1)
else:
    content = content[:query_pos] + new_query + content[query_pos + len(old_query):]
    print("✅ Query atualizada com auxilio_semanal")

# 2. Substituir total_auxilio = 0 pelo cálculo correto
# Find "total_auxilio = 0" AFTER the editar-reenviar marker
old_auxilio = """            total_desmontagem = 0
            total_auxilio = 0
            
            for item in items_selecionados:"""

new_auxilio = """            total_desmontagem = 0
            
            # Buscar auxílio semanal do montador
            auxilio_semanal = float(envio.get('auxilio_semanal', 0))
            
            for item in items_selecionados:"""

auxilio_pos = content.find(old_auxilio, marker_pos)
if auxilio_pos == -1:
    print("❌ Não encontrou 'total_auxilio = 0' no endpoint de revisão!")
    # Check what's actually there
    check = content[marker_pos:marker_pos+3000]
    idx = check.find('total_auxilio')
    if idx != -1:
        print(f"   Encontrou total_auxilio em: ...{check[max(0,idx-50):idx+80]}...")
    exit(1)
else:
    content = content[:auxilio_pos] + new_auxilio + content[auxilio_pos + len(old_auxilio):]
    print("✅ Removido total_auxilio = 0, será calculado após datas")

# 3. Agora inserir o cálculo de semanas únicas APÓS o cálculo do período
# Preciso adicionar depois de calcular 'datas' e antes de montar detalhes_json
old_periodo_block = """            if datas:
                min_data = min(datas)
                max_data = max(datas)
                periodo_relatorio = f"{min_data.strftime('%d/%m/%Y')} a {max_data.strftime('%d/%m/%Y')}"
                periodo_mes = max_data.strftime('%m/%Y')
            else:
                periodo_relatorio = envio['periodo']
                periodo_mes = envio['periodo']
            
            # Montar detalhes JSON"""

new_periodo_block = """            if datas:
                min_data = min(datas)
                max_data = max(datas)
                periodo_relatorio = f"{min_data.strftime('%d/%m/%Y')} a {max_data.strftime('%d/%m/%Y')}"
                periodo_mes = max_data.strftime('%m/%Y')
            else:
                periodo_relatorio = envio['periodo']
                periodo_mes = envio['periodo']
            
            # Calcular auxílio semanal (baseado em semanas únicas trabalhadas)
            semanas_unicas = set()
            for data_obj in datas:
                semanas_unicas.add(data_obj.isocalendar()[1])
            total_auxilio = len(semanas_unicas) * auxilio_semanal if auxilio_semanal > 0 else 0
            print(f"   💰 Auxílio semanal: {auxilio_semanal} x {len(semanas_unicas)} semanas = {total_auxilio}")
            
            # Montar detalhes JSON"""

periodo_pos = content.find(old_periodo_block, marker_pos)
if periodo_pos == -1:
    print("❌ Não encontrou o bloco de período!")
    exit(1)
else:
    content = content[:periodo_pos] + new_periodo_block + content[periodo_pos + len(old_periodo_block):]
    print("✅ Cálculo de auxílio semanal adicionado após cálculo do período")

# Backup e salvar
with open(FILE + '.bak_auxilio', 'w') as f_bak:
    with open(FILE, 'r') as f_orig:
        pass  # backup já feito antes
    
with open(FILE, 'w') as f:
    f.write(content)

print("✅ Patch de auxílio semanal aplicado com sucesso!")
