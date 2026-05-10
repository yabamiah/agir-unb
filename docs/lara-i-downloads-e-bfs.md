# LARA-I: downloads na sessão do browser e fallback BFS

Documentação técnica das melhorias **(2) downloads com a mesma sessão do Playwright** e **(6) varredura em largura (BFS) limitada** implementadas em `core/models/lara_i.py`.

## Contexto

O LARA-I navega portais (em geral Plone/gov.br) com **Playwright**, localiza páginas de atas, programa de integridade ou compliance, extrai hiperlinks para PDFs e grava arquivos em `data/dani/docs/input/{cig|pg|compliance}/{SIGLA}/`. A orquestração por órgão roda em **paralelo** com um único processo Chromium compartilhado e **um `BrowserContext` + uma `Page` por órgão** (`LaraISession`).

---

## 2. Downloads via `APIRequestContext` (mesma sessão)

### Problema anterior

Os PDFs eram baixados com **`requests.get`**, fora do browser. Isso **não reutiliza cookies, armazenamento de sessão nem o estado TLS** negociado na página. Portais que exigem sessão ou redirecionamentos condicionais podem responder com **403/401** ou HTML de erro em vez do binário PDF.

### Solução

O download passou a usar o **`APIRequestContext`** associado ao mesmo **`BrowserContext`** da navegação:

- Obtido em código como `self.context.request` (tipo `APIRequestContext` no Playwright Python).
- Chamada **`await req.get(url, timeout=timeout_ms)`**, com `timeout_ms` alinhado ao tempo máximo de navegação configurado.
- O corpo é lido com **`await response.body()`** e escrito em disco; status HTTP ≥ 400 gera erro e aciona **retentativas com backoff exponencial** (mesma ideia da melhoria 5, aplicada ao fluxo de download).

### TLS e certificados

O contexto é criado com **`ignore_https_errors=True`**, igual à configuração anterior do browser. O cliente HTTP interno do Playwright **herda** esse comportamento para requisições feitas via `context.request`, o que mantém o comportamento esperado em ambientes com cadeias incomuns (comuns em alguns órgãos), **sem** usar `verify=False` no `requests`.

### Validação leve do conteúdo

Após o download, se os bytes **não** começam com o magic `%PDF` e o cabeçalho `Content-Type` não sugere PDF, é emitido um **aviso** no log; o arquivo ainda pode ser salvo (alguns endpoints entregam PDF com tipo genérico).

### Onde está no código

- Classe **`LaraISession._baixar_pdfs`**: laço por link, `req.get`, gravação do arquivo, retentativas.
- Cada órgão usa sua própria instância de **`LaraISession`**, portanto **cookies e storage ficam isolados por órgão**, coerente com o paralelismo.

---

## 6. Fallback por BFS (crawl limitado na mesma origem)

### Objetivo

Quando a **busca interna do portal** não encontra campo de pesquisa, ou **nenhum termo** retorna resultado útil, o coletor tenta um **plano B**: explorar links **apenas no mesmo host** que a URL inicial do órgão, com limites rígidos de páginas e profundidade, e devolver **URLs de “hubs”** (páginas com vários PDFs ou caminhos alinhados ao tipo de documento).

### Algoritmo (resumo)

1. **Origem**: `scheme://netloc` da URL inicial do órgão.
2. **Fila** (BFS): pares `(url, profundidade)`, começando em `(start_url, 0)`.
3. **Visitados**: conjunto de URLs normalizadas (sem fragmento `#`), para não repetir.
4. Para cada URL retirada da fila:
   - Navega com **`_goto`** (que já inclui esperas pós-navegação e **retentativas** em falhas transitórias).
   - Conta quantos `a[href]` parecem PDF ou documento relacionado, reutilizando a heurística **`_e_provavel_pdf(href, texto)`**.
   - Verifica se o **path** da URL contém palavras-chave conforme o **tipo** (`cig`, `pg`, `compliance`).
5. Se **`keyword_hit`** no path **ou** **`pdf_score >= 2`**, a URL da página atual entra na lista de **hubs**.
6. **Enfileira** até 40 links internos por página (amostra), respeitando **`bfs_max_profundidade`**.
7. Interrompe ao atingir **`bfs_max_paginas`** visitadas.
8. Retorna no máximo **`bfs_max_hubs_retorno`** hubs.

### Integração nos fluxos

- **`buscar_links_atas_cig`**: se não há input de busca, ou após esgotar termos sem sucesso → **`_bfs_coletar_hubs(url, "cig")`**.
- **`buscar_links_programa_integridade`**: idem com tipo **`"pg"`**.
- **`buscar_links_plano_compliance`**: idem com tipo **`"compliance"`**.

As URLs retornadas pelo BFS são as mesmas que o restante do pipeline já espera: uma **lista de páginas** passada para **`extrair_links_cig`**, que abre cada uma e extrai links de PDF com as heurísticas existentes.

### Configuração (`ConfiguracaoLara`)

| Campo | Padrão | Função |
|--------|--------|--------|
| `bfs_habilitado` | `True` | Liga/desliga o fallback. |
| `bfs_max_paginas` | `35` | Teto de páginas visitadas na BFS. |
| `bfs_max_profundidade` | `2` | Profundidade máxima a partir da home do órgão. |
| `bfs_max_hubs_retorno` | `5` | Máximo de hubs devolvidos à extração de PDFs. |

### Palavras-chave por tipo (path)

- **cig**: ex.: `cig`, `governanca`, `ata`, `transparencia`, `acervo`, `comite`, `reuniao`, …
- **pg**: ex.: `integridade`, `programa`, `compliance`, `transparencia`, …
- **compliance**: ex.: `compliance`, `integridade`, `plano`, `transparencia`, …

### Limitações conscientes

- Não substitui **robots.txt** nem política institucional; os limites existem para **reduzir carga** e evitar exploração ampla.
- Sites muito grandes ou com poucos links na home podem **não** ser alcançados em 2 saltos; nesse caso ajuste `bfs_max_profundidade` / `bfs_max_paginas` na configuração (código ou futura exposição via CLI/env).

---

## Referências cruzadas no repositório

- Implementação: `core/models/lara_i.py` (`LaraISession._baixar_pdfs`, `LaraISession._bfs_coletar_hubs`, `LaraI.processar_orgaos`).
- Concorrência entre órgãos: variável de ambiente **`LARA_CONCORRENCIA_ORGAOS`** ou flag **`--concorrencia`** no módulo CLI do LARA-I; ver também `.env.example`.
