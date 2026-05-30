# Guia de Geração de PDFs com ReportLab

## 📄 Visão Geral

Os relatórios do sistema agora utilizam **ReportLab**, uma biblioteca Python poderosa para criar PDFs programaticamente com design profissional e totalmente customizável.

## 🎨 Design dos Relatórios

### Características Visuais

- **Cores Temáticas**: Azul primário (#2563eb) e verde para destaques
- **Layout Profissional**: Margens adequadas, espaçamento consistente
- **Cabeçalho e Rodapé**: Em todas as páginas com informações relevantes
- **Tabelas Estilizadas**: Com alternância de cores e bordas suaves
- **Tipografia Clara**: Hierarquia visual bem definida

### Elementos Incluídos

1. **Cabeçalho Decorativo**
   - Linha superior colorida
   - Título do relatório
   - Subtítulo com período

2. **Box de Informações**
   - Dados do prestador/montador
   - Período de referência
   - Identificadores

3. **Tabelas de Dados**
   - Cabeçalhos destacados em azul
   - Linhas alternadas para melhor leitura
   - Alinhamento apropriado por tipo de dado

4. **Resumo Financeiro**
   - Totalizadores destacados
   - Valor final em verde para destaque
   - Cálculos claros e organizados

5. **Instruções e Observações**
   - Próximos passos em bullet points
   - Observações em texto menor
   - Links e orientações claras

## 📁 Estrutura de Arquivos

```
backend_example/
├── app/
│   ├── utils/
│   │   └── pdf_generator.py    # Gerador de PDFs com ReportLab
│   └── routes/
│       └── relatorios.py        # Rotas de relatórios (atualizado)
└── requirements.txt             # reportlab==4.0.7
```

## 🔧 Uso

### Relatório de Prestador

```python
from app.utils.pdf_generator import gerar_pdf_prestador

lote_data = {
    'id': 123,
    'prestador_nome': 'João Silva',
    'periodo': 'Janeiro/2024',
    'valor_total': 5000.00,
    'os_list': [
        {
            'os_numero': 'OS-001',
            'cliente_nome': 'Cliente ABC',
            'servico_descricao': 'Instalação',
            'valor': 150.00
        },
        # ... mais OS
    ]
}

pdf_path = gerar_pdf_prestador(lote_data, '/tmp/relatorio.pdf')
```

### Relatório de Montador

```python
from app.utils.pdf_generator import gerar_pdf_montador

envio_data = {
    'id': 456,
    'montador_nome': 'Maria Santos',
    'periodo': 'Janeiro/2024',
    'percentual_comissao': 15.0,
    'total_comissoes': 2000.00,
    'auxilio_semanal': 500.00,
    'valor_final': 2500.00,
    'montagens': [
        {
            'pedido': 'PED-001',
            'cliente': 'Cliente XYZ',
            'produto': 'Guarda-roupa',
            'comissao': 100.00
        },
        # ... mais montagens
    ]
}

pdf_path = gerar_pdf_montador(envio_data, '/tmp/relatorio.pdf')
```

## 🎯 Customização

### Alterar Cores

Edite as constantes no início de `pdf_generator.py`:

```python
COR_PRIMARIA = colors.HexColor('#2563eb')      # Azul principal
COR_SECUNDARIA = colors.HexColor('#1e40af')    # Azul escuro
COR_SUCESSO = colors.HexColor('#10b981')       # Verde
```

### Alterar Layout

Ajuste as margens no `SimpleDocTemplate`:

```python
doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    rightMargin=2*cm,    # Margem direita
    leftMargin=2*cm,     # Margem esquerda
    topMargin=3.5*cm,    # Margem superior
    bottomMargin=2.5*cm  # Margem inferior
)
```

### Adicionar Logotipo

No cabeçalho, adicione:

```python
def header(self, canvas, doc):
    canvas.saveState()
    
    # Adicionar logo
    logo_path = Path(__file__).parent.parent / 'assets' / 'logo.png'
    if logo_path.exists():
        canvas.drawImage(str(logo_path), 2*cm, A4[1] - 2*cm, 
                        width=3*cm, height=1*cm, preserveAspectRatio=True)
    
    # ... resto do código
```

## 📊 Comparação: WeasyPrint vs ReportLab

| Aspecto | WeasyPrint | ReportLab |
|---------|------------|-----------|
| **Método** | HTML → PDF | Python → PDF |
| **Controle** | CSS | Código Python |
| **Performance** | Média | Rápida |
| **Flexibilidade** | Limitada | Total |
| **Complexidade** | Média | Maior |
| **Resultado** | Bom | Excelente |

### Vantagens do ReportLab

✅ **Performance superior** - Geração mais rápida de PDFs  
✅ **Controle total** - Posicionamento pixel-perfect  
✅ **Sem dependências externas** - Não precisa de renderizadores HTML  
✅ **Recursos avançados** - Gráficos, formas, imagens complexas  
✅ **Tamanho menor** - PDFs otimizados  

## 🚀 Melhorias Futuras

- [ ] Adicionar gráficos de desempenho
- [ ] Incluir código QR para validação
- [ ] Assinatura digital
- [ ] Múltiplos idiomas
- [ ] Temas customizáveis por empresa

## 📚 Recursos

- [Documentação ReportLab](https://www.reportlab.com/docs/)
- [User Guide PDF](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Exemplos de Código](https://github.com/MrBitBucket/reportlab-mirror)

## ⚠️ Observações

- Os PDFs são salvos temporariamente em `/tmp/`
- Arquivos temporários devem ser limpos após o envio
- ReportLab requer menos memória que WeasyPrint
- Ideal para geração em lote de relatórios
