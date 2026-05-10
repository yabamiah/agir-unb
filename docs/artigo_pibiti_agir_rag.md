# Texto-base para Artigo/Relatório PIBITI

**Título Sugerido**: AGIR-RAG: Automação Inteligente e Recuperação Aumentada para Auditoria de Governança no Setor Público do Distrito Federal
**Autor(es)**: Vinícius Mendes Martins
**Orientação**: Profa. Dra. Fátima de Souza Freire

---

## 1. Introdução

A adoção de mecanismos legais e regulatórios visando o fortalecimento da integridade no setor público – como a exigência de programas de compliance estabelecida pelo Decreto nº 39.736/2019 do Governo do Distrito Federal (GDF) – impõe um novo desafio: como monitorar e auditar em larga escala o cumprimento de tais exigências normativas? O volume de documentos gerados, compostos por atas, normativas internas e manuais de compliance, torna a revisão manual não só onerosa, mas sujeita a inconsistências amostrais.

Este projeto propõe o desenvolvimento de um ecossistema metodológico e algorítmico, o AGIR-RAG, para coletar, extrair e inferir indicadores de maturidade institucional. Utilizamos a abordagem de *Retrieval-Augmented Generation* (RAG) para localizar evidências textuais em documentos oficiais e processar a conformidade de acordo com eixos analíticos predefinidos.

## 2. Metodologia

A pesquisa caracterizou-se como exploratória e aplicada. O projeto AGIR (Automação para uma Governança Inteligente e Responsável) consolidou um pipeline metodológico batizado de "AGIR-RAG Lite".

A implementação dividiu-se em módulos:
1. **Coleta e Ingestão Automática**: Utilização do script LARA-I (robô de scraping) para minerar portais de transparência do GDF.
2. **Extração Textual**: Implementação do robô DANI para leitura e processamento OCR dos artefatos coletados.
3. **Indexação Vetorial Local**: Substituição da plataforma pesada *RAGFlow* por uma infraestrutura customizada empregando o Qdrant em disco e SQLite com FTS5. Isso permitiu reduzir a dependência computacional (GPU) mantendo a rastreabilidade das evidências através de uma abordagem de Busca Híbrida (BM25 + Cosine Similarity).
4. **Recuperação e Classificação Normativa**: Definição de critérios baseados na taxonomia do Índice de Maturidade da Governança Algorítmica (IMGA). As perguntas foram respondidas por meio da integração de *Large Language Models* (LLMs), validando se o trecho documental recuperado "Atende", "Atende Parcialmente" ou "Não Atende" ao critério legal.

## 3. Resultados Preliminares

A prova de conceito validou a ingestão sistêmica dos documentos (Planos de Integridade e Atas de Comitês). A busca híbrida obteve sucesso em encontrar termos não exatos (como sinônimos de "canal de denúncia"), sem perder a acurácia de termos jurídicos estritos, graças à união do banco relacional com o vetor.

A geração de conformidade demonstrou como uma aplicação escalável de Inteligência Artificial permite atribuir pesos aos eixos IMGA e criar painéis de transparência. Como resultado direto da pesquisa, foi concebido e entregue um *Dashboard Interativo* em *Streamlit*, projetado com interfaces amigáveis que dispensam conhecimento técnico (destacando-se os alertas de "Ausência Documental").

## 4. Conclusões e Trabalhos Futuros

O AGIR-RAG Lite comprovou a viabilidade técnica da construção de ferramentas de auditoria contínua para programas de integridade pública. A abordagem descentralizada (dispensando frameworks monolíticos) revelou-se eficaz. Para trabalhos futuros, sugere-se a ampliação da base para empresas licitantes que possuem contratos governamentais (em adequação ao Decreto nº 40.388/2020) e o refinamento do modelo vetorial mediante *fine-tuning* com vocabulário jurídico regionalizado.

## Referências
- BRASIL. Lei nº 12.846/2013 – Lei Anticorrupção.
- DISTRITO FEDERAL. Decreto n. 39.736, de 28 de março de 2019.
- DISTRITO FEDERAL. Decreto nº 40.388/2020.
- GAO, Y. et al. Modular RAG: Transforming RAG Systems into LEGO-like Frameworks. arXiv:2407.21059v1, 2024.
