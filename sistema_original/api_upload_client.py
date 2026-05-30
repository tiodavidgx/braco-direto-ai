"""
Cliente para API DV Processamento
Envia dados de lotes de        # Importar aqui para evitar import circular
        from database import get_os_by_lote_id, get_prestador_by_name, get_montador_by_name
        
        # Determinar se é lote de prestador ou envio de montador
        if tipo == 'montagem':
            # Para montadores: usar montador_nome e detalhes['quantidade_os']
            nome_empresa = lote['montador_nome']
            
            # Obter informações do montador para pegar o email
            montador = get_montador_by_name(nome_empresa)
            email_contato = montador['email'] if montador and montador.get('email') else "sem-email@novomundo.com.br"
            
            # Quantidade de OS já está salva nos detalhes
            detalhes = lote.get('detalhes', {})
            if isinstance(detalhes, str):
                import json
                detalhes = json.loads(detalhes)
            quantidade_os = detalhes.get('quantidade_os', 0)
            
            lote_ou_envio_id = lote['id']  # ID do envio de montagem
            
        else:
            # Para prestadores: usar prestador_nome e contar OS
            nome_empresa = lote['prestador_nome']
            
            # Obter informações do prestador para pegar o email
            prestador = get_prestador_by_name(nome_empresa)
            email_contato = prestador['email'] if prestador else "sem-email@novomundo.com.br"
            
            # Contar quantidade de OS deste lote
            os_list = get_os_by_lote_id(lote['id'])
            quantidade_os = len(os_list)
            
            lote_ou_envio_id = lote['id']  # ID do lote de serviçoara geração de links de upload de NF
"""

import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import urllib3

# Suprimir avisos de SSL enquanto certificado não está ativo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# Configurações da API
# NOTA: Certificado SSL ainda não está ativo, usando HTTP temporariamente
API_URL = "https://api.link.dev.br/dvprocessamento/"  # HTTPS ativado no novo VPS
API_KEY = "<SUA_API_KEY_AQUI>"

# Quando certificado SSL estiver ativo, alterar para:
# API_URL = "https://api.link.dev.br/dvprocessamento/"

class APIUploadClient:
    """Cliente para comunicação com a API de upload de notas fiscais"""
    
    def __init__(self, api_url=None, api_key=None, verify_ssl=False):
        """
        Inicializa o cliente da API
        
        Args:
            api_url: URL do endpoint (opcional, usa padrão se não fornecido)
            api_key: Chave de autenticação (opcional, usa padrão se não fornecido)
            verify_ssl: Se deve verificar certificado SSL (False por padrão até certificado estar ativo)
        """
        self.api_url = api_url or API_URL
        self.api_key = api_key or API_KEY
        self.verify_ssl = verify_ssl
        
    def preparar_payload(self, lote, tipo='lote'):
        """
        Prepara o payload JSON para envio à API
        
        Mapeamento:
        - NOME_EMPRESA (prestador_nome ou montador_nome) -> nome
        - EMAIL_CONTATO (usar email do prestador/montador) -> email
        - PERIODO_REF (periodo) -> periodo (formato MM/YYYY)
        - VALOR_TOTAL (valor_total) -> valor_total
        - QTD_OS (contar OS ou quantidade_os) -> quantidade_os
        - DATA_ENVIO (data_envio) -> data_envio (ISO format)
        - LOTE_ID (id) -> lote_id (ou envio_id para montadores)
        
        Args:
            lote: Dicionário com dados do lote/envio do banco local
            tipo: 'lote' para prestadores ou 'montagem' para montadores
            
        Returns:
            dict: Payload formatado para a API
        """
        # Importar aqui para evitar import circular
        from database import get_os_by_lote_id, get_prestador_by_name, get_montador_by_name
        
        # Determinar se é lote de prestador ou envio de montador
        if tipo == 'montagem':
            # Para montadores: usar montador_nome e quantidade_os da coluna
            nome_empresa = lote['montador_nome']
            
            # Obter informações do montador para pegar o email
            montador = get_montador_by_name(nome_empresa)
            email_contato = montador['email'] if montador and montador.get('email') else "sem-email@novomundo.com.br"
            
            # Quantidade de OS já está salva na coluna
            quantidade_os = lote.get('quantidade_os', 0) or 0
            
            lote_ou_envio_id = lote['id']  # ID do envio de montagem
            
        else:
            # Para prestadores: usar prestador_nome e contar OS
            nome_empresa = lote['prestador_nome']
            
            # Obter informações do prestador para pegar o email
            prestador = get_prestador_by_name(nome_empresa)
            email_contato = prestador['email'] if prestador else "sem-email@novomundo.com.br"
            
            # Contar quantidade de OS deste lote
            os_list = get_os_by_lote_id(lote['id'])
            quantidade_os = len(os_list)
            
            lote_ou_envio_id = lote['id']  # ID do lote de serviço
        
        # 🔧 OFFSET para montadores: Adicionar 876231 ao ID para evitar conflito com prestadores
        if tipo == 'montagem':
            lote_id_api = 876231 + lote_ou_envio_id
            print(f"🔧 ID Montagem: {lote_ou_envio_id} → ID API: {lote_id_api}")
        else:
            lote_id_api = lote_ou_envio_id
        
        # Formatar data_envio para ISO 8601 (YYYY-MM-DDTHH:MM:SS)
        print(f"📅 Data envio original: '{lote['data_envio']}' (tipo: {type(lote['data_envio'])})")
        
        try:
            if isinstance(lote['data_envio'], str):
                # Tentar parsear a string para datetime
                data_obj = datetime.fromisoformat(lote['data_envio'].replace('Z', '+00:00'))
            else:
                data_obj = lote['data_envio']
            
            # Formatar para ISO sem microsegundos e sem timezone
            data_envio_iso = data_obj.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            print(f"⚠️ Erro ao processar data_envio: {e}")
            # Usar data/hora atual como fallback
            data_envio_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            print(f"⚠️ Usando data atual como fallback: {data_envio_iso}")
        
        print(f"📅 Data envio formatada: '{data_envio_iso}'")
        
        # Normalizar período para formato MM/AAAA (ano com 4 dígitos)
        periodo_original = lote['periodo']
        print(f"📅 Período original: '{periodo_original}' (tipo: {type(periodo_original)})")
        
        # Extrair mês/ano do período (pode estar como "DD/MM/YYYY - DD/MM/YYYY" ou "MM/YYYY")
        periodo_str = str(periodo_original).strip()
        
        # Se contém " - " ou " – ", é um intervalo de datas, pegar a primeira data
        if ' - ' in periodo_str or ' – ' in periodo_str:
            periodo_str = periodo_str.split(' - ')[0].split(' – ')[0].strip()
        
        # Tentar extrair mês e ano
        try:
            # Se está no formato DD/MM/YYYY, extrair MM/YYYY
            if '/' in periodo_str:
                partes = periodo_str.split('/')
                if len(partes) == 3:  # DD/MM/YYYY
                    mes = partes[1].strip().zfill(2)
                    ano = partes[2].strip()
                elif len(partes) == 2:  # MM/YYYY ou MM/YY
                    mes = partes[0].strip().zfill(2)
                    ano = partes[1].strip()
                    # Se ano tem 2 dígitos, converter para 4
                    if len(ano) == 2:
                        ano = '20' + ano
                else:
                    raise ValueError(f"Formato de período não reconhecido: {periodo_original}")
                
                periodo = f"{mes}/{ano}"
            else:
                # Se não tem barra, não é um formato de data válido
                raise ValueError(f"Período não contém data válida: {periodo_original}")
        except Exception as e:
            print(f"⚠️ Erro ao processar período: {e}")
            # Usar data atual como fallback
            agora = datetime.now()
            periodo = agora.strftime("%m/%Y")
            print(f"⚠️ Usando período atual como fallback: {periodo}")
        
        print(f"📅 Período formatado: '{periodo}'")
        
        # Validar campos obrigatórios
        if not nome_empresa:
            raise ValueError(f"Nome da empresa não pode ser vazio (tipo: {tipo})")
        if not periodo:
            raise ValueError(f"Período não pode ser vazio (tipo: {tipo})")
        if lote.get('valor_total') is None:
            raise ValueError(f"Valor total não pode ser None (tipo: {tipo})")
        if quantidade_os is None or quantidade_os == 0:
            raise ValueError(f"Quantidade de OS deve ser maior que zero (tipo: {tipo})")
        
        payload = {
            "nome": nome_empresa,
            "email": email_contato,
            "periodo": periodo,  # Formato MM/AAAA
            "valor_total": float(lote['valor_total']),
            "quantidade_os": quantidade_os,
            "data_envio": data_envio_iso,
            "lote_id": lote_id_api,  # ID com offset para montadores (876231 + id)
            "tipo": tipo  # Adicionar tipo para identificação na API (opcional)
        }
        
        return payload
    
    def enviar_lote(self, lote, tipo='lote'):
        """
        Envia um lote para a API e retorna a resposta
        
        Args:
            lote: Dicionário com dados do lote
            tipo: 'lote' para prestadores ou 'montagem' para montadores
            
        Returns:
            tuple: (sucesso: bool, resposta: dict, erro: str)
        """
        try:
            # Preparar payload
            payload = self.preparar_payload(lote, tipo)
            
            # Configurar headers com User-Agent para evitar bloqueio do Mod_Security
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                "X-API-Key": self.api_key
            }
            
            # Fazer requisição POST
            # verify=False porque certificado SSL ainda não está ativo
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30,
                verify=self.verify_ssl  # False por padrão até certificado estar ativo
            )
            
            # Verificar status code
            # 200 OK ou 201 Created são sucessos
            if response.status_code in [200, 201]:
                resposta_json = response.json()
                
                # Verificar se o campo success existe e é True
                if resposta_json.get('success'):
                    print(f"✅ API retornou sucesso (HTTP {response.status_code})")
                    print(f"📦 Resposta: {resposta_json}")
                    return True, resposta_json, None
                else:
                    erro_msg = resposta_json.get('message', 'Erro desconhecido')
                    return False, resposta_json, f"API retornou erro: {erro_msg}"
            
            elif response.status_code == 409:
                # Conflito - lote duplicado
                return False, None, "Lote já foi enviado anteriormente (duplicado)"
            
            else:
                return False, None, f"Erro HTTP {response.status_code}: {response.text}"
        
        except requests.exceptions.Timeout:
            return False, None, "Timeout ao conectar com a API"
        
        except requests.exceptions.ConnectionError:
            return False, None, "Erro de conexão com a API"
        
        except json.JSONDecodeError:
            return False, None, "Resposta da API não é um JSON válido"
        
        except Exception as e:
            return False, None, f"Erro inesperado: {str(e)}"
    
    def processar_resposta(self, resposta):
        """
        Processa a resposta da API e extrai os campos relevantes
        
        Resposta esperada:
        {
          "success": true,
          "id_controle": 1,
          "lote_id": 99999,
          "link": "https://api.link.com.br/dvprocessamento/envio-nf/...",
          "hash": "03de0449e11849318f7d67e08377f150",
          "validade_link": "2025-11-12",
          "status": 0,
          "message": "Registro criado com sucesso"
        }
        
        Args:
            resposta: Dicionário com a resposta da API
            
        Returns:
            dict: Campos extraídos e formatados
        """
        return {
            'id_controle': resposta.get('id_controle'),
            'link': resposta.get('link'),
            'hash': resposta.get('hash'),
            'validade_link': resposta.get('validade_link'),
            'status': resposta.get('status', 0),
            'message': resposta.get('message', '')
        }
    
    def enviar_e_salvar(self, item_id, tipo='lote'):
        """
        Envia um lote/envio para a API e salva a resposta no banco
        
        Args:
            item_id: ID do lote (prestador) ou envio (montador) a ser enviado
            tipo: 'lote' para prestadores ou 'montagem' para montadores
            
        Returns:
            tuple: (sucesso: bool, mensagem: str, dados: dict)
        """
        from database import (
            get_db_connection, 
            salvar_resposta_api, 
            verificar_lote_duplicado,
            atualizar_status_api_montagem,
            get_envio_montagem_by_id
        )
        import psycopg2.extras
        
        # Buscar dados do lote/envio
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if tipo == 'montagem':
                cur.execute('SELECT * FROM envios_montagem WHERE id = %s', (item_id,))
            else:
                cur.execute('SELECT * FROM lotes_servico WHERE id = %s', (item_id,))
            item = cur.fetchone()
        conn.close()
        
        if not item:
            return False, f"{'Envio' if tipo == 'montagem' else 'Lote'} não encontrado", None
        
        # Verificar se já foi enviado
        if tipo == 'lote' and verificar_lote_duplicado(item['id'], item['periodo']):
            return False, "Este lote já foi enviado para a API anteriormente", None
        elif tipo == 'montagem' and item.get('id_controle'):
            return False, "Este envio já foi enviado para a API anteriormente", None
        
        # Enviar para API
        sucesso, resposta, erro = self.enviar_lote(item, tipo)
        
        if not sucesso:
            return False, erro or "Erro ao enviar para API", None
        
        # Processar resposta
        dados = self.processar_resposta(resposta)
        
        # Salvar no banco
        if tipo == 'montagem':
            atualizar_status_api_montagem(
                envio_id=item['id'],
                id_controle=dados['id_controle'],
                link=dados['link'],
                validade_link=dados['validade_link'],
                status_api=dados['status'],
                upload_hash=dados.get('hash')
            )
        else:
            salvar_resposta_api(
                lote_id=item['id'],
                id_controle=dados['id_controle'],
                link=dados['link'],
                validade_link=dados['validade_link'],
                status_api=dados['status'],
                message=dados['message'],
                upload_hash=dados.get('hash')
            )
        
        return True, dados['message'], dados


def enviar_lote_para_api(lote_id, api_url=None, api_key=None):
    """
    Função auxiliar para enviar um lote específico
    
    Args:
        lote_id: ID do lote
        api_url: URL da API (opcional)
        api_key: Chave da API (opcional)
        
    Returns:
        tuple: (sucesso: bool, mensagem: str, dados: dict)
    """
    client = APIUploadClient(api_url, api_key)
    return client.enviar_e_salvar(lote_id)


def enviar_lotes_pendentes():
    """
    Envia todos os lotes/envios pendentes (prestadores e montadores) para a API
    
    Returns:
        dict: Estatísticas do processamento
    """
    from database import get_lotes_para_enviar_api, get_envios_montagem_sem_api
    
    # Buscar lotes de prestadores
    lotes = get_lotes_para_enviar_api()
    
    # Buscar envios de montadores
    envios = get_envios_montagem_sem_api()
    
    stats = {
        'total': len(lotes) + len(envios),
        'lotes': {
            'total': len(lotes),
            'sucesso': 0,
            'erro': 0,
            'detalhes': []
        },
        'montagens': {
            'total': len(envios),
            'sucesso': 0,
            'erro': 0,
            'detalhes': []
        }
    }
    
    client = APIUploadClient()
    
    # Processar lotes de prestadores
    print(f"📦 Processando {len(lotes)} lotes de prestadores...")
    for lote in lotes:
        sucesso, mensagem, dados = client.enviar_e_salvar(lote['id'], tipo='lote')
        
        if sucesso:
            stats['lotes']['sucesso'] += 1
            stats['lotes']['detalhes'].append({
                'id': lote['id'],
                'nome': lote.get('prestador_nome', ''),
                'status': 'sucesso',
                'mensagem': mensagem,
                'link': dados.get('link') if dados else None
            })
        else:
            stats['lotes']['erro'] += 1
            stats['lotes']['detalhes'].append({
                'id': lote['id'],
                'nome': lote.get('prestador_nome', ''),
                'status': 'erro',
                'mensagem': mensagem
            })
    
    # Processar envios de montadores
    print(f"🔧 Processando {len(envios)} envios de montadores...")
    for envio in envios:
        sucesso, mensagem, dados = client.enviar_e_salvar(envio['id'], tipo='montagem')
        
        if sucesso:
            stats['montagens']['sucesso'] += 1
            stats['montagens']['detalhes'].append({
                'id': envio['id'],
                'nome': envio.get('montador_nome', ''),
                'status': 'sucesso',
                'mensagem': mensagem,
                'link': dados.get('link') if dados else None
            })
        else:
            stats['montagens']['erro'] += 1
            stats['montagens']['detalhes'].append({
                'id': envio['id'],
                'nome': envio.get('montador_nome', ''),
                'status': 'erro',
                'mensagem': mensagem
            })
    
    return stats


if __name__ == "__main__":
    # Teste da API
    print("🔍 Buscando itens pendentes...")
    stats = enviar_lotes_pendentes()
    
    print(f"\n📊 Resultado Geral:")
    print(f"   Total: {stats['total']}")
    
    print(f"\n📦 Lotes de Prestadores:")
    print(f"   Total: {stats['lotes']['total']}")
    print(f"   ✅ Sucesso: {stats['lotes']['sucesso']}")
    print(f"   ❌ Erro: {stats['lotes']['erro']}")
    
    if stats['lotes']['detalhes']:
        print(f"\n   📝 Detalhes:")
        for det in stats['lotes']['detalhes']:
            emoji = "✅" if det['status'] == 'sucesso' else "❌"
            print(f"      {emoji} Lote #{det['id']} ({det['nome']}): {det['mensagem']}")
            if det.get('link'):
                print(f"         🔗 Link: {det['link']}")
    
    print(f"\n🔧 Envios de Montadores:")
    print(f"   Total: {stats['montagens']['total']}")
    print(f"   ✅ Sucesso: {stats['montagens']['sucesso']}")
    print(f"   ❌ Erro: {stats['montagens']['erro']}")
    
    if stats['montagens']['detalhes']:
        print(f"\n   📝 Detalhes:")
        for det in stats['montagens']['detalhes']:
            emoji = "✅" if det['status'] == 'sucesso' else "❌"
            print(f"      {emoji} Envio #{det['id']} ({det['nome']}): {det['mensagem']}")
            if det.get('link'):
                print(f"         🔗 Link: {det['link']}")
