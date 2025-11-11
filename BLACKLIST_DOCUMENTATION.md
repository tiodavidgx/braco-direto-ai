# 🛡️ Sistema de Blacklist

## 🎯 Visão Geral

Sistema para impedir o reenvio de O.S. (Ordens de Serviço) e Boletins de Montagem duplicados ou cancelados.

**Funcionalidades:**
- ✅ Adicionar múltiplas O.S./Boletins à blacklist por vez
- ✅ Motivo opcional para cada item
- ✅ Remoção individual da blacklist
- ✅ Busca e filtros
- ✅ Verificação automática durante envio de relatórios
- ✅ Interface separada por tipo (Prestadores/Montadores)

---

## 📂 Estrutura do Banco de Dados

### Tabela: `os_blacklist` (Para Prestadores)

```sql
CREATE TABLE os_blacklist (
    id SERIAL PRIMARY KEY,
    prestador_id INTEGER REFERENCES prestadores(id) ON DELETE CASCADE,
    os_numero TEXT NOT NULL,
    data_adicao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT
);

CREATE UNIQUE INDEX idx_unique_os_blacklist 
ON os_blacklist (prestador_id, os_numero);
```

### Tabela: `boletins_blacklist` (Para Montadores)

```sql
CREATE TABLE boletins_blacklist (
    id SERIAL PRIMARY KEY,
    montador_id INTEGER REFERENCES montadores(id) ON DELETE CASCADE,
    boletim TEXT NOT NULL,
    data_adicao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT
);

CREATE UNIQUE INDEX idx_unique_boletim_blacklist 
ON boletins_blacklist (montador_id, boletim);
```

**Campos:**
- `id`: Identificador único
- `prestador_id` / `montador_id`: Referência à entidade
- `os_numero` / `boletim`: Número da OS ou Boletim
- `data_adicao`: Timestamp de quando foi adicionado
- `motivo`: Motivo opcional da blacklist

**Índices Únicos:** Garantem que a mesma OS/Boletim não seja adicionada duas vezes para a mesma entidade.

---

## 🔌 Backend: Endpoints da API

### 1. Adicionar OS à Blacklist

**POST** `/api/v1/blacklist/os`

```python
# backend/app/routes/blacklist.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()

class OSBlacklistAdd(BaseModel):
    prestador_id: int
    os_numero: str
    motivo: str = None

@router.post("/os")
def adicionar_os_blacklist(item: OSBlacklistAdd):
    """Adiciona uma O.S. à blacklist"""
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO os_blacklist (prestador_id, os_numero, motivo)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (item.prestador_id, item.os_numero, item.motivo))
            
            blacklist_id = cur.fetchone()[0]
        
        conn.commit()
        return {
            "success": True,
            "message": f"O.S. {item.os_numero} adicionada à blacklist",
            "id": blacklist_id
        }
    
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"O.S. {item.os_numero} já está na blacklist"
        )
    
    finally:
        conn.close()
```

### 2. Listar Blacklist de OS

**GET** `/api/v1/blacklist/os`

```python
@router.get("/os")
def listar_os_blacklist():
    """Lista todas as O.S. na blacklist"""
    
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                osb.id,
                osb.prestador_id,
                osb.os_numero,
                osb.motivo,
                osb.data_adicao,
                p.nome as prestador_nome
            FROM os_blacklist osb
            JOIN prestadores p ON p.id = osb.prestador_id
            ORDER BY osb.data_adicao DESC
        """)
        
        items = cur.fetchall()
    
    conn.close()
    return items
```

### 3. Remover OS da Blacklist

**DELETE** `/api/v1/blacklist/os/{id}`

```python
@router.delete("/os/{id}")
def remover_os_blacklist(id: int):
    """Remove uma O.S. da blacklist"""
    
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM os_blacklist WHERE id = %s", (id,))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item não encontrado")
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Item removido da blacklist"}
```

### 4. Verificar Lista de OS

**POST** `/api/v1/blacklist/os/check`

```python
class CheckOSList(BaseModel):
    os_numbers: list[str]

@router.post("/os/check")
def verificar_os_blacklist(data: CheckOSList):
    """
    Verifica quais O.S. de uma lista estão na blacklist
    Retorna array com números que estão bloqueados
    """
    
    if not data.os_numbers:
        return []
    
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT os_numero 
            FROM os_blacklist 
            WHERE os_numero = ANY(%s)
        """, (data.os_numbers,))
        
        blacklisted = [row['os_numero'] for row in cur.fetchall()]
    
    conn.close()
    return blacklisted
```

### 5. Endpoints para Boletins (Montadores)

**Estrutura idêntica**, mudando apenas:
- Rota: `/api/v1/blacklist/boletins`
- Tabela: `boletins_blacklist`
- Campo: `boletim` ao invés de `os_numero`
- Parâmetro: `montador_id` ao invés de `prestador_id`

```python
# POST /api/v1/blacklist/boletins
class BoletimBlacklistAdd(BaseModel):
    montador_id: int
    boletim: str
    motivo: str = None

@router.post("/boletins")
def adicionar_boletim_blacklist(item: BoletimBlacklistAdd):
    # Mesma lógica da OS, mudando tabela e campos
    ...

# GET /api/v1/blacklist/boletins
@router.get("/boletins")
def listar_boletins_blacklist():
    # Mesma lógica da OS
    ...

# DELETE /api/v1/blacklist/boletins/{id}
@router.delete("/boletins/{id}")
def remover_boletim_blacklist(id: int):
    # Mesma lógica da OS
    ...

# POST /api/v1/blacklist/boletins/check
@router.post("/boletins/check")
def verificar_boletins_blacklist(data: CheckOSList):
    # Mesma lógica da OS
    ...
```

---

## 🔄 Integração no Envio de Relatórios

### Fluxo de Verificação

Antes de enviar relatórios, o sistema deve:

1. **Coletar todos os números** de OS/Boletins que serão enviados
2. **Verificar na blacklist** usando endpoint `/check`
3. **Filtrar itens bloqueados** da lista de envio
4. **Mostrar warning** ao usuário informando quantos itens foram ignorados
5. **Prosseguir** apenas com itens não bloqueados

### Exemplo de Integração no Backend

```python
# No endpoint POST /api/v1/relatorios/enviar-lote

@router.post("/enviar-lote")
async def enviar_relatorios_lote(request: EnvioLoteRequest):
    # ... código anterior ...
    
    # Extrair números de OS/Boletins
    df = pd.DataFrame([item.dict() for item in request.dados])
    
    if request.tipo == 'prestador':
        numeros = df['os_numero'].dropna().tolist()
        
        # Verificar blacklist
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT os_numero 
                FROM os_blacklist 
                WHERE os_numero = ANY(%s)
            """, (numeros,))
            blacklisted = [row[0] for row in cur.fetchall()]
        conn.close()
        
        # Filtrar itens da blacklist
        df = df[~df['os_numero'].isin(blacklisted)]
        
        if blacklisted:
            return {
                "warning": f"{len(blacklisted)} O.S. na blacklist foram ignoradas",
                "blacklisted_items": blacklisted,
                "items_to_send": len(df)
            }
    
    else:  # montador
        numeros = df['boletim'].dropna().tolist()
        
        # Mesma lógica para boletins
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT boletim 
                FROM boletins_blacklist 
                WHERE boletim = ANY(%s)
            """, (numeros,))
            blacklisted = [row[0] for row in cur.fetchall()]
        conn.close()
        
        df = df[~df['boletim'].isin(blacklisted)]
        
        if blacklisted:
            return {
                "warning": f"{len(blacklisted)} boletins na blacklist foram ignorados",
                "blacklisted_items": blacklisted,
                "items_to_send": len(df)
            }
    
    # Prosseguir com envio apenas dos itens não bloqueados
    # ... resto do código de envio ...
```

---

## 📱 Frontend: Integração nas Páginas

**IMPORTANTE**: A blacklist está integrada DENTRO das páginas de Prestadores e Montadores, não é uma página separada.

### Localização

- **Prestadores**: `/prestadores` → Aba "Blacklist de O.S."
- **Montadores**: `/montadores` → Aba "Blacklist de Boletins"

### Componentes Principais

1. **Tabs**: Alterna entre "Lista" e "Blacklist"
2. **Card de Adição**:
   - Select de entidade (Prestador/Montador)
   - Input de números (aceita múltiplos separados por vírgula)
   - Input de motivo (opcional)
   - Botão de adicionar
3. **Card de Lista**:
   - Campo de busca
   - Tabela com itens na blacklist
   - Botão de remover por item

### Estado e Hooks

**Para Prestadores:**
```typescript
const [blacklistItems, setBlacklistItems] = useState<BlacklistItem[]>([]);
const [prestadorSelecionado, setPrestadorSelecionado] = useState<number | null>(null);
const [numerosOS, setNumerosOS] = useState(""); // Ex: "OS001, OS002, OS003"
const [motivo, setMotivo] = useState("");
const [searchBlacklist, setSearchBlacklist] = useState("");
```

**Para Montadores:**
```typescript
const [blacklistItems, setBlacklistItems] = useState<BlacklistItem[]>([]);
const [montadorSelecionado, setMontadorSelecionado] = useState<number | null>(null);
const [numerosBoletim, setNumerosBoletim] = useState(""); // Ex: "BOL001, BOL002"
const [motivo, setMotivo] = useState("");
const [searchBlacklist, setSearchBlacklist] = useState("");
```

### Validações

- ✅ Entidade deve estar selecionada
- ✅ Números não podem estar vazios
- ✅ Split por vírgula e trim de cada número
- ✅ Duplicatas são bloqueadas pelo backend (índice único)

---

## 🧪 Testes e Validação

### Casos de Teste

1. **Adicionar item único**: Selecionar entidade e adicionar um número
2. **Adicionar múltiplos**: Testar "OS001, OS002, OS003"
3. **Duplicata**: Tentar adicionar mesmo número duas vezes
4. **Remover**: Verificar se remove corretamente
5. **Busca**: Testar filtro por nome, número e motivo
6. **Troca de tab**: Verificar se limpa estado ao trocar
7. **Envio bloqueado**: Verificar se impede envio de itens na blacklist

---

## 📋 Checklist de Implementação

### Backend
- [x] Criar tabelas `os_blacklist` e `boletins_blacklist`
- [ ] Implementar endpoints de blacklist
- [ ] Adicionar verificação no endpoint de envio
- [ ] Testar com dados reais
- [ ] Documentar no BACKEND_DOCUMENTATION.md

### Frontend
- [x] Criar página Blacklist
- [x] Adicionar rota `/blacklist`
- [x] Adicionar item no menu lateral
- [ ] Integrar verificação na página de Envio de Relatórios
- [ ] Mostrar warnings quando itens forem bloqueados
- [ ] Testar fluxo completo

---

## 🆘 Troubleshooting

### Erro: "Item já está na blacklist"
- **Causa**: Índice único impede duplicatas
- **Solução**: Verificar se item já existe antes de adicionar

### Itens da blacklist não aparecem
- **Causa**: JOIN com tabela de entidades pode falhar se entidade foi deletada
- **Solução**: `ON DELETE CASCADE` na foreign key garante limpeza automática

### Busca não funciona
- **Causa**: Case sensitivity no banco
- **Solução**: Usar `.toLowerCase()` no frontend e filtros SQL com `ILIKE`

---

**Sistema Braço Direito** - Novo Mundo 🤝
