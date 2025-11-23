# Sistema de Versionamento Automático

Este projeto usa **versionamento automático** com Semantic Versioning (MAJOR.MINOR.PATCH).

## 🚀 Como Funciona

A versão é **incrementada automaticamente** a cada commit através do Git hook `post-commit`:

1. **A cada commit**, a versão PATCH é incrementada automaticamente
2. A mensagem do commit é adicionada ao changelog
3. A data é atualizada automaticamente
4. O arquivo `version.json` é modificado e incluído no commit

## 📊 Semantic Versioning

- **MAJOR** (X.0.0): Mudanças incompatíveis com versões anteriores
- **MINOR** (0.X.0): Novas funcionalidades compatíveis
- **PATCH** (0.0.X): Correções de bugs e melhorias pequenas (incrementado automaticamente)

## 🔧 Quando Atualizar Manualmente

### Incrementar MINOR (nova funcionalidade)

Edite o `version.json` antes de fazer commit:

```json
{
  "version": "1.2.0",
  "lastUpdate": "2025-11-22",
  "changelog": [
    {
      "version": "1.2.0",
      "date": "2025-11-22",
      "changes": [
        "Nova funcionalidade de exportação em PDF",
        "Integração com novo serviço de pagamento"
      ]
    }
  ]
}
```

### Incrementar MAJOR (breaking change)

```json
{
  "version": "2.0.0",
  "lastUpdate": "2025-11-22",
  "changelog": [
    {
      "version": "2.0.0",
      "date": "2025-11-22",
      "changes": [
        "BREAKING: Nova arquitetura de autenticação",
        "BREAKING: API endpoints reestruturados"
      ]
    }
  ]
}
```

## ⚙️ Scripts Disponíveis

```bash
# Atualizar versão manualmente (incrementa PATCH)
npm run version:update

# Fazer commit com versionamento automático (padrão)
git commit -m "sua mensagem"

# Fazer commit SEM versionamento automático
git commit --no-verify -m "sua mensagem"
```

## 📁 Arquivos do Sistema

- **`/version.json`**: Armazena a versão atual e changelog
- **`/scripts/update-version.cjs`**: Script Node.js que incrementa a versão
- **`/.husky/post-commit`**: Git hook que executa após cada commit
- **`/src/components/AppSidebar.tsx`**: Exibe a versão no sidebar da aplicação

## 🔄 Fluxo Automático

```
1. git commit -m "fix: correção de bug"
   ↓
2. Git executa .husky/post-commit
   ↓
3. Script update-version.cjs roda
   ↓
4. version.json atualizado (1.1.0 → 1.1.1)
   ↓
5. version.json adicionado ao commit automaticamente
   ↓
6. Versão exibida no frontend é atualizada
```

## 💡 Exemplo de Uso

### Commit Normal (incremento automático)
```bash
git add .
git commit -m "fix: corrigido problema no login"
# Versão automaticamente muda de 1.1.0 → 1.1.1
```

### Nova Feature (incremento manual MINOR)
```bash
# 1. Editar version.json manualmente para 1.2.0
# 2. Adicionar changelog da feature
git add version.json
git commit -m "feat: adicionado sistema de notificações"
# Após o commit, a versão será 1.2.1 automaticamente
```

## 🎯 Estrutura do version.json

```json
{
  "version": "1.1.0",
  "lastUpdate": "2025-11-22",
  "changelog": [
    {
      "version": "1.1.0",
      "date": "2025-11-22",
      "changes": [
        "Descrição da mudança 1",
        "Descrição da mudança 2"
      ]
    }
  ]
}
```

O sistema mantém automaticamente as últimas 10 versões no changelog.
