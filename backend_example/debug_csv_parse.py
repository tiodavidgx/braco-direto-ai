#!/usr/bin/env python3
"""Simulate actual CSV import to find the real problem"""
import pandas as pd
import io
import os

# Read the CSV as the import endpoint does
csv_path = "/Users/david/Documents/GitHub/braco-direto-ai/titulos 12 03.csv"
with open(csv_path, 'rb') as f:
    contents = f.read()

# Same logic as importar_titulos
df = None
for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
    try:
        df = pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine='python')
        print(f"Parsed with encoding: {encoding}")
        break
    except:
        continue

if df is None:
    df = pd.read_csv(io.BytesIO(contents))

print(f"\nOriginal columns: {list(df.columns)}")
print(f"Shape: {df.shape}")

# Normalize columns
df.columns = df.columns.str.lower().str.strip()
print(f"\nLowered columns: {list(df.columns)}")

# Same column mapping as backend
column_mapping = {
    'fornecedor': 'nome_fornecedor',
    'razao_social': 'nome_fornecedor',
    'razão social': 'nome_fornecedor',
    'nome': 'nome_fornecedor',
    'nome fornecedor': 'nome_fornecedor',
    'cod. fornecedor': 'cod_fornecedor',
    'cod.fornecedor': 'cod_fornecedor',
    'cod fornecedor': 'cod_fornecedor',
    'codigo fornecedor': 'cod_fornecedor',
    'cnpj': 'cnpj_cpf',
    'cpf': 'cnpj_cpf',
    'cnpj/cpf': 'cnpj_cpf',
    'cpf cnpj': 'cnpj_cpf',
    'cpf/cnpj': 'cnpj_cpf',
    'numero': 'numero_titulo',
    'título': 'numero_titulo',
    'titulo': 'numero_titulo',
    'nf': 'numero_titulo',
    'nota': 'numero_titulo',
    'num. titulo': 'numero_titulo',
    'num.titulo': 'numero_titulo',
    'num titulo': 'numero_titulo',
    'id  titulo pagar': 'id_titulo_pagar',
    'id titulo pagar': 'id_titulo_pagar',
    'num. orcom': 'num_orcom',
    'num.orcom': 'num_orcom',
    'num orcom': 'num_orcom',
    'filial': 'filial',
    'empresa': 'empresa',
    'parcela': 'parcela_erp',
    'data lancamento': 'data_emissao',
    'data lançamento': 'data_emissao',
    'emissao': 'data_emissao',
    'dt_emissao': 'data_emissao',
    'data emissão': 'data_emissao',
    'data vencimento': 'data_vencimento',
    'vencimento': 'data_vencimento',
    'dt_vencimento': 'data_vencimento',
    'data pagamento': 'data_pagamento',
    'tipo': 'tipo',
    'tipo mov.': 'tipo_movimento',
    'tipo mov': 'tipo_movimento',
    'situação': 'situacao',
    'situacao': 'situacao',
    'documento dev.': 'documento_dev',
    'documento dev': 'documento_dev',
    'liberação': 'liberacao',
    'liberacao': 'liberacao',
    'empenho': 'empenho',
    'carnê': 'carne',
    'carne': 'carne',
    'valor do titulo': 'valor_titulo',
    'valor do título': 'valor_titulo',
    'valor do t\u00edtulo': 'valor_titulo',
    'valor antecipado': 'valor_antecipado',
    'valor desconto': 'valor_desconto',
    'valor desconto tributacao': 'valor_desconto_tributacao',
    'valor desconto tributação': 'valor_desconto_tributacao',
    'valor final': 'valor',
    'instrucao_pagamento': 'instrucao_pagamento',
    'instrução pagamento': 'instrucao_pagamento',
    'instrucao pagamento': 'instrucao_pagamento',
    'grupo de conta': 'grupo_conta',
    'grupo conta': 'grupo_conta',
    'conta': 'conta',
    'descricao': 'descricao',
    'descrição': 'descricao',
    'descrição conta': 'descricao',
    'descricao conta': 'descricao',
    'seu número': 'seu_numero',
    'seu numero': 'seu_numero',
    'seu n\u00famero': 'seu_numero',
    'vinculado a lote': 'vinculado_lote',
    'lote': 'lote_erp',
    'categoria': 'categoria',
    'banco': 'banco',
    'agencia': 'agencia',
    'agência': 'agencia',
    'pix': 'pix',
    'chave pix': 'pix',
}

df.rename(columns=column_mapping, inplace=True)
print(f"\nMapped columns: {list(df.columns)}")

# Check required columns
required = ['nome_fornecedor', 'valor', 'data_vencimento']
missing = [col for col in required if col not in df.columns]
print(f"\nMissing required: {missing}")

if missing:
    print("PROBLEM: Missing required columns! Import would fail with 400 error.")
else:
    print("Required columns present.")

# Show each row data
from datetime import date, datetime
DATA_MINIMA = date(2026, 1, 16)

for idx, row in df.iterrows():
    print(f"\n--- Row {idx} ---")
    try:
        # valor
        valor = row['valor']
        print(f"  valor (raw): {repr(valor)}")
        if isinstance(valor, str):
            valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
        valor = float(valor)
        print(f"  valor (float): {valor}")
        
        # data_vencimento
        data_venc = row['data_vencimento']
        print(f"  data_vencimento (raw): {repr(data_venc)}")
        if isinstance(data_venc, str):
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    data_venc = datetime.strptime(data_venc, fmt).date()
                    break
                except:
                    continue
        elif hasattr(data_venc, 'date'):
            data_venc = data_venc.date()
        print(f"  data_vencimento (parsed): {data_venc}")
        
        if data_venc <= DATA_MINIMA:
            print(f"  >>> DATE FILTERED OUT")
        
        # nome_fornecedor
        nome = str(row['nome_fornecedor']).strip()
        print(f"  nome_fornecedor: {nome}")
        
        # cod_fornecedor
        def get_val(col):
            if col in row.index:
                val = row[col]
                if hasattr(val, 'iloc'):
                    val = val.iloc[0]
                if pd.isna(val):
                    return None
                return val
            return None
        
        cod = get_val('cod_fornecedor')
        print(f"  cod_fornecedor: {repr(cod)}")
        
        # numero_titulo
        num = get_val('numero_titulo')
        print(f"  numero_titulo (raw): {repr(num)}")
        if num is not None:
            num = str(num).strip()
            if num.endswith('.0'):
                num = num[:-2]
        print(f"  numero_titulo (cleaned): {repr(num)}")
        
        # fornecedor_prefixo
        forn_prefix = nome[:20].upper() if nome else ''
        print(f"  fornecedor_prefixo for dup check: {repr(forn_prefix)}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
