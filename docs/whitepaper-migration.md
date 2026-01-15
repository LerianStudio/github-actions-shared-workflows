# Whitepaper: Migração para Shared Workflows

**Versão:** 1.0
**Data:** 2026-01-15
**Autor:** Lerian DevOps Team

---

## Sumário Executivo

Este documento descreve a migração da infraestrutura de CI/CD da Lerian Studio de pipelines individuais e descentralizadas para um modelo centralizado baseado em **GitHub Actions Shared Workflows**. A mudança representa uma evolução significativa na maturidade operacional, resultando em maior consistência, menor manutenção e melhor governança de segurança.

---

## 1. Contexto: Pipeline Antiga

### 1.1 Arquitetura Anterior

Cada repositório mantinha sua própria cópia completa das workflows de CI/CD:

```
repositorio/
├── .github/
│   └── workflows/
│       ├── build.yml          # ~150-300 linhas cada
│       ├── test.yml
│       ├── lint.yml
│       ├── security.yml
│       ├── release.yml
│       └── pr-validation.yml
```

### 1.2 Problemas Identificados

| Problema | Impacto |
|----------|---------|
| **Duplicação de código** | 15+ repositórios com workflows quase idênticas (~2000+ linhas duplicadas) |
| **Drift de configuração** | Cada repo evoluía independentemente, criando inconsistências |
| **Manutenção descentralizada** | Atualizações exigiam PRs em todos os repositórios |
| **Padrões inconsistentes** | Diferentes thresholds de coverage, versões de ferramentas, flags |
| **Segurança fragmentada** | Secrets gerenciados repo a repo, sem auditoria centralizada |
| **Onboarding lento** | Novos projetos copiavam workflows existentes, herdando problemas |

### 1.3 Exemplo de Workflow Antiga (Build)

```yaml
# Cada repositório tinha ~200 linhas assim
name: Build
on:
  push:
    tags: ['**']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      # ... mais 50+ steps repetidos em cada repo
```

---

## 2. Nova Arquitetura: Shared Workflows

### 2.1 Modelo Centralizado

```
github-actions-shared-workflows/     # Repositório central
├── .github/
│   └── workflows/
│       ├── build.yml               # Reusável, parametrizado
│       ├── go-pr-analysis.yml      # Lint + Test + Security + Coverage
│       ├── pr-validation.yml       # Validação de PR title/description
│       ├── pr-security-scan.yml    # Trivy + SBOM
│       ├── release.yml             # Semantic Release
│       └── typescript-ci.yml       # Pipeline TypeScript completa

repositorio-consumidor/
├── .github/
│   └── workflows/
│       ├── build.yml               # ~30 linhas - apenas referência
│       ├── go-combined-analysis.yml
│       └── release.yml
```

### 2.2 Benefícios Alcançados

| Benefício | Métrica |
|-----------|---------|
| **Redução de código** | De ~300 linhas para ~30 linhas por workflow (90% menos) |
| **Consistência** | 100% dos repos usando mesmas versões de ferramentas |
| **Manutenção centralizada** | 1 PR para atualizar todos os repositórios |
| **Versionamento** | Tags semânticas (`@v1.7.0`) permitem rollback |
| **Governança** | Padrões de segurança aplicados uniformemente |
| **Time-to-market** | Novos repos configurados em minutos, não horas |

### 2.3 Exemplo de Workflow Nova (Build)

```yaml
# Apenas ~30 linhas no repositório consumidor
name: "Build"

on:
  push:
    tags: ['**']

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.7.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      filter_paths: |-
        components/manager
        components/worker
      path_level: 2
      app_name_prefix: "fetcher"
      enable_dockerhub: true
      enable_ghcr: true
      dockerhub_org: lerianstudio
    secrets: inherit
```

---

## 3. Workflows Disponíveis

### 3.1 Catálogo de Workflows (v1.7.0+)

| Workflow | Propósito | Linguagens |
|----------|-----------|------------|
| `build.yml` | Build e push de imagens Docker multi-arch | Go, qualquer Dockerfile |
| `go-pr-analysis.yml` | Lint, test, security, coverage para PRs | Go |
| `pr-validation.yml` | Validação de PR title, description, labels | Agnóstico |
| `pr-security-scan.yml` | Trivy scan + SBOM generation | Agnóstico |
| `release.yml` | Semantic release com changelog automático | Agnóstico |
| `typescript-ci.yml` | Lint, build, test, security para TypeScript | TypeScript/Node.js |
| `gitops-update.yml` | Atualização de manifests GitOps | Agnóstico |
| `api-dog-e2e-tests.yml` | Testes E2E via APIDog | Agnóstico |

### 3.2 Parâmetros Comuns

```yaml
with:
  runner_type: "blacksmith-4vcpu-ubuntu-2404"  # Runner otimizado
  filter_paths: '[...]'                         # Monorepo support
  path_level: 2                                 # Profundidade de path
  app_name_prefix: "service-name"               # Prefixo para artefatos
```

---

## 4. Integração: GPT Changelog

### 4.1 O Que É

O **GPT Changelog** é uma GitHub Action que utiliza IA (OpenAI GPT-4) para gerar changelogs semânticos automaticamente a partir dos commits entre releases.

### 4.2 Funcionamento

```
Commits → Análise GPT → Categorização → CHANGELOG.md
```

1. Detecta commits desde a última tag
2. Envia para GPT-4 categorizar (feat, fix, docs, etc.)
3. Gera markdown formatado com emojis e agrupamentos
4. Comita automaticamente no repositório

### 4.3 Configuração

```yaml
generate_changelog:
  name: Generate AI-powered Changelog
  runs-on: blacksmith-4vcpu-ubuntu-2404
  needs: release
  steps:
    - uses: actions/create-github-app-token@v1
      id: app-token
      with:
        app-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
        private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}

    - uses: LerianStudio/github-actions-gptchangelog@main
      with:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}
        # ... demais secrets
```

### 4.4 Exemplo de Output

```markdown
## [v1.2.0] - 2026-01-15

### ✨ Features
- Add multi-currency support for international transactions
- Implement real-time balance synchronization

### 🐛 Bug Fixes
- Fix race condition in concurrent payment processing
- Resolve memory leak in long-running connections

### 🔧 Maintenance
- Update dependencies to latest versions
- Improve error logging granularity
```

---

## 5. Guia de Migração

### 5.1 Checklist de Migração

- [ ] Identificar workflows existentes no repositório
- [ ] Mapear parâmetros para equivalentes shared
- [ ] Atualizar referências para `@v1.7.0`
- [ ] Configurar secrets necessários (se não herdados)
- [ ] Testar em branch antes de merge
- [ ] Implementar GPT Changelog (opcional)

### 5.2 Migração Passo a Passo

**Antes (pipeline antiga):**
```yaml
name: Build
on:
  push:
    tags: ['**']
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: lerianstudio/myapp:${{ github.ref_name }}
          # ... mais configurações
```

**Depois (shared workflow):**
```yaml
name: "Build"
on:
  push:
    tags: ['**']
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.7.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      app_name_prefix: "myapp"
      enable_dockerhub: true
      dockerhub_org: lerianstudio
    secrets: inherit
```

---

## 6. Status de Migração por Repositório

### 6.1 Repositórios Migrados ✅

| Repositório | Versão Shared | GPT Changelog | Status |
|-------------|---------------|---------------|--------|
| midaz | v1.7.0 | ✅ @main | Produção |
| fetcher | v1.7.0 | ✅ @main | Produção |
| plugin-br-pix-indirect-btg | v1.7.0 | ✅ @main | Produção |
| plugin-crm | v1.3.3 | ❌ | Parcial |
| reporter | v1.3.3 | ❌ | Parcial |
| tracer | v1.2.0 | ❌ | Parcial |

### 6.2 Pendências

| Repositório | Ação Necessária |
|-------------|-----------------|
| plugin-crm | Atualizar para v1.7.0 + GPT Changelog |
| reporter | Atualizar para v1.7.0 + GPT Changelog |
| tracer | Atualizar para v1.7.0 + GPT Changelog |
| lib-commons-golang | Avaliar migração |
| midaz-sdk-typescript | Usar typescript-ci.yml@v1.8.0 |

---

## 7. Governança e Versionamento

### 7.1 Política de Versões

| Tipo | Formato | Uso |
|------|---------|-----|
| **Produção** | `@v1.7.0` | Repos em produção, estável |
| **Desenvolvimento** | `@main` | Apenas para testes |
| **Específico** | `@v1.7.0-beta.1` | Features em validação |

### 7.2 Processo de Atualização

1. Nova feature desenvolvida em branch
2. Tag beta criada (`v1.x.0-beta.1`)
3. Testes em repositórios piloto
4. Tag release criada (`v1.x.0`)
5. Comunicação para equipes atualizarem referências

### 7.3 Breaking Changes

Mudanças que quebram compatibilidade:
- Bump de major version (`v1.x.x` → `v2.x.x`)
- Documentação de migração obrigatória
- Período de suporte para versão anterior

---

## 8. Troubleshooting

### 8.1 Problemas Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `workflow not found` | Versão inexistente | Verificar tags disponíveis |
| `secrets not inherited` | Falta `secrets: inherit` | Adicionar ao job |
| `permission denied` | Falta permissões no workflow | Adicionar bloco `permissions:` |
| `coverage threshold` | Coverage abaixo do mínimo | Aumentar testes ou ajustar threshold |

### 8.2 GPT Changelog - Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `429 insufficient_quota` | Quota OpenAI excedida | Verificar billing OpenAI |
| `sed: no match` | Changelog mal formatado | Verificar formato do CHANGELOG.md |
| `GPG signature failed` | Chave GPG inválida | Regenerar secret GPG |

---

## 9. Conclusão

A migração para Shared Workflows representa um salto de maturidade na infraestrutura de CI/CD da Lerian Studio:

- **Eficiência:** 90% menos código de configuração por repositório
- **Consistência:** Padrões uniformes em toda a organização
- **Agilidade:** Atualizações propagadas com um único PR
- **Qualidade:** Thresholds de coverage e segurança padronizados
- **Automação:** Changelogs gerados por IA, releases semânticos

A adoção contínua e evolução das shared workflows garante que a Lerian mantenha práticas de DevOps de classe mundial.

---

## Apêndice A: Referências

- [GitHub Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [LerianStudio/github-actions-shared-workflows](https://github.com/LerianStudio/github-actions-shared-workflows)
- [LerianStudio/github-actions-gptchangelog](https://github.com/LerianStudio/github-actions-gptchangelog)
- [Semantic Versioning](https://semver.org/)

---

## Apêndice B: Secrets Necessários

```yaml
# Secrets organizacionais (herdados automaticamente)
DOCKER_USERNAME
DOCKER_PASSWORD
GITHUB_TOKEN
OPENAI_API_KEY
LERIAN_CI_CD_USER_GPG_KEY
LERIAN_CI_CD_USER_GPG_KEY_PASSWORD
LERIAN_CI_CD_USER_NAME
LERIAN_CI_CD_USER_EMAIL
LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID
LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY
```
