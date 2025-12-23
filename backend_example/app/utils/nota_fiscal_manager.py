"""
Módulo unificado para gerenciar notas fiscais
Consolida funções duplicadas de prestador e montador
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.database import get_db_connection

logger = logging.getLogger('NotaFiscalManager')


class NotaFiscalManager:
    """
    Gerencia operações de notas fiscais para prestadores e montadores
    Unifica lógica duplicada e fornece interface consistente
    """
    
    @staticmethod
    def salvar_arquivos_info(
        entity_type: str,
        entity_id: int,
        arquivos: List[Dict],
        stats: Dict
    ) -> bool:
        """
        Salva informações dos arquivos de NF no banco
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID do lote (prestador) ou envio (montador)
            arquivos: Lista de dicionários com info dos arquivos
            stats: Estatísticas (total_arquivos, total_tamanho)
            
        Returns:
            True se salvou com sucesso
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                if entity_type == 'prestador':
                    table = 'lotes_servico'
                    id_field = 'id'
                else:
                    table = 'envios_montagem'
                    id_field = 'id'
                
                # Garantir que as colunas existem
                cur.execute(f"""
                    ALTER TABLE {table} 
                    ADD COLUMN IF NOT EXISTS total_arquivos_nf INTEGER,
                    ADD COLUMN IF NOT EXISTS tamanho_total_nf BIGINT,
                    ADD COLUMN IF NOT EXISTS data_ultima_consulta TIMESTAMP
                """)
                conn.commit()
                
                # Atualizar registro
                cur.execute(f"""
                    UPDATE {table}
                    SET 
                        total_arquivos_nf = %s,
                        tamanho_total_nf = %s,
                        data_ultima_consulta = NOW()
                    WHERE {id_field} = %s
                """, (stats['total_arquivos'], stats['total_tamanho'], entity_id))
                
                conn.commit()
                logger.info(f"Arquivos info salvos para {entity_type} #{entity_id}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar arquivos info: {e}")
            return False
    
    @staticmethod
    def atualizar_status_arquivo(
        entity_type: str,
        entity_id: int,
        status: int
    ) -> bool:
        """
        Atualiza status de arquivo
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            status: 0=pendente, 1=em processamento, 2=baixado
            
        Returns:
            True se atualizou com sucesso
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                if entity_type == 'prestador':
                    table = 'lotes_servico'
                else:
                    table = 'envios_montagem'
                    # Garantir coluna existe
                    cur.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN IF NOT EXISTS status_arquivo INTEGER DEFAULT 0
                    """)
                    conn.commit()
                
                cur.execute(f"""
                    UPDATE {table}
                    SET status_arquivo = %s
                    WHERE id = %s
                """, (status, entity_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao atualizar status arquivo: {e}")
            return False
    
    @staticmethod
    def salvar_nota_fiscal(
        entity_type: str,
        entity_id: int,
        caminho_arquivo: str
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Salva caminho da nota fiscal e calcula vencimento
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            caminho_arquivo: Caminho do arquivo salvo
            
        Returns:
            Tupla (sucesso, data_vencimento)
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                if entity_type == 'prestador':
                    # Buscar tempo de vencimento do prestador
                    cur.execute("""
                        SELECT p.tempo_vencimento_dias 
                        FROM lotes_servico ls
                        JOIN prestadores p ON ls.prestador_id = p.id
                        WHERE ls.id = %s
                    """, (entity_id,))
                    table = 'lotes_servico'
                else:
                    # Buscar tempo de vencimento do montador
                    cur.execute("""
                        SELECT m.tempo_vencimento_dias 
                        FROM envios_montagem em
                        JOIN montadores m ON em.montador_id = m.id
                        WHERE em.id = %s
                    """, (entity_id,))
                    table = 'envios_montagem'
                
                result = cur.fetchone()
                dias_vencimento = result[0] if result and result[0] else 30
                
                # Calcular data de vencimento
                data_vencimento = datetime.now() + timedelta(days=dias_vencimento)
                
                # Atualizar registro
                cur.execute(f"""
                    UPDATE {table}
                    SET 
                        nota_fiscal_path = %s,
                        status_api = 1,
                        data_recebimento_nf = NOW(),
                        data_vencimento_pagamento = %s
                    WHERE id = %s
                """, (caminho_arquivo, data_vencimento, entity_id))
                
                conn.commit()
                
                logger.info(f"NF salva para {entity_type} #{entity_id} - Vencimento: {data_vencimento.strftime('%d/%m/%Y')}")
                return True, data_vencimento
                
        except Exception as e:
            logger.error(f"Erro ao salvar NF: {e}")
            return False, None
    
    @staticmethod
    def atualizar_status_api(
        entity_type: str,
        entity_id: int,
        status: int
    ) -> bool:
        """
        Atualiza status da API
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            status: 0=aguardando, 1=recebido, 2=expirado
            
        Returns:
            True se atualizou com sucesso
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                table = 'lotes_servico' if entity_type == 'prestador' else 'envios_montagem'
                
                cur.execute(f"""
                    UPDATE {table}
                    SET status_api = %s
                    WHERE id = %s
                """, (status, entity_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao atualizar status API: {e}")
            return False
    
    @staticmethod
    def criar_notificacao(
        entity_type: str,
        entity_id: int,
        tipo: str,
        titulo: str,
        mensagem: str,
        icone: str = '📋',
        prioridade: int = 0
    ) -> bool:
        """
        Cria uma notificação no sistema
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            tipo: Tipo da notificação
            titulo: Título
            mensagem: Mensagem
            icone: Emoji do ícone
            prioridade: Nível de prioridade
            
        Returns:
            True se criou com sucesso
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                if entity_type == 'montador':
                    # Garantir que a coluna existe
                    cur.execute("""
                        ALTER TABLE notificacoes 
                        ADD COLUMN IF NOT EXISTS envio_montagem_id INTEGER REFERENCES envios_montagem(id)
                    """)
                    conn.commit()
                    
                    cur.execute("""
                        INSERT INTO notificacoes 
                        (tipo, titulo, mensagem, envio_montagem_id, icone, prioridade, data_criacao, lida)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), false)
                    """, (tipo, titulo, mensagem, entity_id, icone, prioridade))
                else:
                    cur.execute("""
                        INSERT INTO notificacoes 
                        (tipo, titulo, mensagem, lote_id, icone, prioridade, data_criacao, lida)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), false)
                    """, (tipo, titulo, mensagem, entity_id, icone, prioridade))
                
                conn.commit()
                logger.info(f"Notificação criada para {entity_type} #{entity_id}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao criar notificação: {e}")
            return False
    
    @staticmethod
    def verificar_notificacao_existe(
        entity_type: str,
        entity_id: int
    ) -> bool:
        """
        Verifica se já existe notificação para a entidade
        
        Args:
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            
        Returns:
            True se já existe notificação
        """
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                if entity_type == 'montador':
                    cur.execute("""
                        SELECT COUNT(*) FROM notificacoes WHERE envio_montagem_id = %s
                    """, (entity_id,))
                else:
                    cur.execute("""
                        SELECT COUNT(*) FROM notificacoes WHERE lote_id = %s
                    """, (entity_id,))
                
                return cur.fetchone()[0] > 0
                
        except Exception as e:
            logger.error(f"Erro ao verificar notificação: {e}")
            return False
    
    @staticmethod
    def baixar_arquivos(
        client,
        entity_type: str,
        entity_id: int,
        arquivos: List[Dict],
        pasta_base: str = 'uploads'
    ) -> Tuple[int, int, str]:
        """
        Baixa arquivos de NF
        
        Args:
            client: Cliente de consulta NF
            entity_type: 'prestador' ou 'montador'
            entity_id: ID da entidade
            arquivos: Lista de arquivos para baixar
            pasta_base: Pasta base para downloads
            
        Returns:
            Tupla (downloads_realizados, erros, pasta_destino)
        """
        if entity_type == 'prestador':
            pasta_destino = os.path.join(pasta_base, f"lote_{entity_id}")
        else:
            pasta_destino = os.path.join(pasta_base, f"montagem_{entity_id}")
        
        os.makedirs(pasta_destino, exist_ok=True)
        
        downloads = 0
        erros = 0
        
        for arquivo in arquivos:
            nome_arquivo = arquivo['nome_original']
            caminho_local = os.path.join(pasta_destino, nome_arquivo)
            
            if os.path.exists(caminho_local):
                logger.info(f"Já existe: {nome_arquivo}")
                downloads += 1
                continue
            
            logger.info(f"Baixando: {nome_arquivo} ({arquivo['tamanho_formatado']})")
            
            sucesso, mensagem = client.baixar_arquivo(
                arquivo['link_download'],
                caminho_local
            )
            
            if sucesso:
                downloads += 1
            else:
                logger.error(f"Erro no download: {mensagem}")
                erros += 1
        
        return downloads, erros, pasta_destino


# Instância global
nf_manager = NotaFiscalManager()
