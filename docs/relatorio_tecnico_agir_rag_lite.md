# Relatório Técnico: Arquitetura AGIR-RAG Lite

## 1. Introdução e Justificativa da Mudança

O projeto de pesquisa AGIR, focado no monitoramento e extração de evidências sobre conformidade e integridade no setor público do Governo do Distrito Federal, previu originalmente a adoção da plataforma **RAGFlow** para indexação e análise dos documentos oficiais (planos de integridade, atas CIG, relatórios de compliance).

Contudo, durante as etapas iniciais de desenvolvimento, a implantação local do RAGFlow demonstrou ser inviável dentro das limitações computacionais e financeiras de um projeto de iniciação científica (PIBITI):
1. **Requisitos de Infraestrutura**: O RAGFlow exige um ecossistema complexo baseado em múltiplos contêineres Docker, necessitando de alta alocação de memória RAM e GPU para operar com estabilidade.
2. **Dependência e Opacidade**: Por ser um sistema fechado e monolítico em vários aspectos de seu pipeline, adaptar as regras de classificação de aderência (IMGA) ao motor interno do RAGFlow mostrou-se excessivamente engessado.
3. **Custo de Escalabilidade**: A manutenção do ambiente consumiria tempo valioso do bolsista, desviando o foco da pesquisa sociotécnica para a manutenção de infraestrutura de software.

Portanto, optou-se pela transição para a arquitetura **AGIR-RAG Lite**, uma abordagem customizada, modular e puramente baseada em scripts locais na linguagem Python.

## 2. A Nova Arquitetura AGIR-RAG Lite

A arquitetura AGIR-RAG Lite simplifica drasticamente o stack de software, substituindo a complexidade por componentes especializados e leves:

### 2.1. Componentes Principais
- **Armazenamento Vetorial Local (Qdrant)**: O Qdrant Client opera no modo local (arquivos em disco), eliminando a necessidade de levantar servidores dedicados.
- **Indexação Lexical e Armazenamento (SQLite)**: O SQLite com a extensão `FTS5` possibilita buscas baseadas em texto puro (Full-Text Search), servindo simultaneamente como base de evidências para o RAG e sistema de auditoria transparente das fontes originais.
- **Vetorização (Embeddings Leves)**: A transformação vetorial foi otimizada usando `HashingVectorizer` na Sprint 5 (com suporte direto para upgrade futuro via SentenceTransformers).

### 2.2. Fluxo Operacional
O fluxo de funcionamento foi dividido em três grandes etapas (Sprints 5 a 7):
1. **Extração e Segmentação (Index Service)**: Lemos os PDFs, extraímos o texto nativo ou processado via OCR (DANI), quebramos em chunks granulares com metadados (Órgão, Tipo, Página) e os inserimos no Qdrant e no SQLite simultaneamente.
2. **Recuperação Híbrida (Retrieval Service)**: Uma busca unificada que mescla escores textuais (BM25 via FTS5) e escores semânticos (Cosine Distance no Qdrant).
3. **Classificação e Inferência Normativa (Classification Service)**: Transforma fragmentos documentais em notas metodológicas, conferindo um score do indicador (IMGA).

## 3. Conclusão da Refatoração

A troca para a arquitetura **AGIR-RAG Lite** conferiu ao projeto total autonomia sobre o código. Reduzimos o tempo de ingestão de documentos, dispensamos GPUs pesadas para a indexação inicial e permitimos que as inferências normativas (com o uso da LLM Gemini, de forma modular) fossem facilmente geridas na camada da API web, diretamente a partir do Streamlit.

Os testes comprovaram que a busca lexical aliada à busca semântica leve recupera as evidências exigidas com precisão adequada para as métricas do projeto.
