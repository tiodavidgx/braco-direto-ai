# 📝 Guia de Versionamento do Sistema

## Como Atualizar a Versão

Sempre que houver mudanças significativas no sistema, siga estes passos:

### 1. Editar o arquivo `version.json`

```json
{
  "version": "X.Y.Z",  // ← Atualizar aqui
  "lastUpdate": "YYYY-MM-DD",  // ← Data da atualização
  "changelog": [
    {
      "version": "X.Y.Z",  // Nova versão
      "date": "YYYY-MM-DD",
      "changes": [
        "Descrição da mudança 1",
        "Descrição da mudança 2",
        "Descrição da mudança 3"
      ]
    },
    // Versões anteriores ficam abaixo...
  ]
}
```

### 2. Padrão de Versionamento (Semantic Versioning)

- **MAJOR (X.0.0)**: Mudanças incompatíveis com versões anteriores
  - Exemplo: Reestruturação completa do banco de dados
  - Exemplo: Mudança radical na arquitetura

- **MINOR (0.X.0)**: Novas funcionalidades (compatível com anterior)
  - Exemplo: Novo módulo de relatórios
  - Exemplo: Nova integração com API externa

- **PATCH (0.0.X)**: Correções de bugs e melhorias menores
  - Exemplo: Correção de duplicação de cards
  - Exemplo: Ajuste de layout
  - Exemplo: Otimização de performance

### 3. Exemplos de Atualização

#### Correção de Bug (1.0.0 → 1.0.1)
```json
{
  "version": "1.0.1",
  "lastUpdate": "2025-11-23",
  "changelog": [
    {
      "version": "1.0.1",
      "date": "2025-11-23",
      "changes": [
        "Correção de erro no envio de emails",
        "Ajuste no layout do dashboard"
      ]
    }
  ]
}
```

#### Nova Funcionalidade (1.0.1 → 1.1.0)
```json
{
  "version": "1.1.0",
  "lastUpdate": "2025-11-25",
  "changelog": [
    {
      "version": "1.1.0",
      "date": "2025-11-25",
      "changes": [
        "Adicionado módulo de relatórios personalizados",
        "Implementado exportação para Excel",
        "Novo dashboard de métricas"
      ]
    }
  ]
}
```

#### Mudança Major (1.1.0 → 2.0.0)
```json
{
  "version": "2.0.0",
  "lastUpdate": "2025-12-01",
  "changelog": [
    {
      "version": "2.0.0",
      "date": "2025-12-01",
      "changes": [
        "Migração para novo sistema de autenticação",
        "Reestruturação completa do banco de dados",
        "Nova API REST v2"
      ]
    }
  ]
}
```

### 4. Onde a Versão Aparece

A versão é exibida automaticamente no **rodapé da sidebar** ao lado do perfil do usuário.

### 5. Checklist de Atualização

- [ ] Implementar as mudanças no código
- [ ] Testar todas as funcionalidades afetadas
- [ ] Atualizar `version.json` com nova versão e changelog
- [ ] Commit com mensagem clara: `chore: bump version to X.Y.Z`
- [ ] Verificar se a versão aparece corretamente no frontend

---

## Versão Atual

**v1.0.0** - Sistema de Gestão Braço Direito
- Sistema de prevenção de duplicação de cards no Trello
- Integração completa com WhatsApp
- Gestão de prestadores e montadores
- Jobs automáticos de consulta de notas fiscais
