"""
Dashboard AGIR - Interface Web para análise de governança e integridade
"""

import time
import streamlit as st
import pandas as pd
import json
import os
import base64
import shutil
from datetime import datetime
from io import BytesIO

# Wordcloud (opcional)
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

# ============================================
# Configuração de Caminhos
# ============================================
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DANI_DATA_DIR = os.path.join(DATA_DIR, "dani", "docs")
TRIGGER_DIR = os.path.join(DATA_DIR, "triggers")
INPUT_DIR = os.path.join(DANI_DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DANI_DATA_DIR, "output")
SUMMARY_FILE = os.path.join(DANI_DATA_DIR, "summary_results.json")
PDF_DIR = os.path.join(DANI_DATA_DIR, "result_pdf")
PDF_OUTPUT_DIR = os.path.join(PDF_DIR, "output")
INTEGRITY_DIR = os.path.join(DANI_DATA_DIR, "integridade")
KEYWORDS_FILE = os.path.join(DATA_DIR, "dani", "palavras_chaves.txt")

# Triggers
TRIGGER_LARA = os.path.join(TRIGGER_DIR, "run_lara.trigger")
TRIGGER_DANI = os.path.join(TRIGGER_DIR, "run_dani.trigger")
TRIGGER_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "run_dani_integrity.trigger")
RUNNING_LARA = os.path.join(TRIGGER_DIR, "running_lara.trigger")
RUNNING_DANI = os.path.join(TRIGGER_DIR, "running_dani.trigger")
RUNNING_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "running_dani_integrity.trigger")
COMPLETED_LARA = os.path.join(TRIGGER_DIR, "completed_lara.trigger")
COMPLETED_DANI = os.path.join(TRIGGER_DIR, "completed_dani.trigger")
COMPLETED_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "completed_dani_integrity.trigger")

# ============================================
# Definição dos Eixos IMGA
# ============================================
EIXOS_IMGA = {
    "E1": {"nome": "Estrutura de Governança e Liderança", "peso": 10, "icone": "",
           "descricao": "Avalia o comprometimento da alta administração e a arquitetura decisória"},
    "E2": {"nome": "Cultura de Integridade", "peso": 10, "icone": "",
           "descricao": "Capta o tom normativo, simbólico e cultural atribuído à ética organizacional"},
    "E3": {"nome": "Ambiente de Compliance", "peso": 15, "icone": "",
           "descricao": "Verifica a existência e densidade do arcabouço normativo"},
    "E4": {"nome": "Due Diligence e Terceiros", "peso": 20, "icone": "",
           "descricao": "Identifica práticas preventivas para mitigação de riscos externos"},
    "E5": {"nome": "Comunicação, Treinamento e Monitoramento", "peso": 10, "icone": "",
           "descricao": "Avalia estratégias de difusão e formação em integridade"},
    "E6": {"nome": "Gestão de Riscos e Controles Internos", "peso": 15, "icone": "",
           "descricao": "Analisa integração entre governança, riscos e controles"},
    "E7": {"nome": "Transparência, Accountability e Evidenciação", "peso": 10, "icone": "",
           "descricao": "Avalia abertura informacional e responsabilização"},
    "E8": {"nome": "Efetividade e Maturidade do Programa", "peso": 10, "icone": "",
           "descricao": "Diferencia programas formais de programas efetivamente implementados"},
}

FAIXAS_MATURIDADE = {
    "Incipiente": {"cor": "#ef9a9a", "range": "0-25", "descricao": "Programa em fase inicial"},
    "Basica": {"cor": "#ffe082", "range": "26-50", "descricao": "Estruturas basicas estabelecidas"},
    "Intermediaria": {"cor": "#a5d6a7", "range": "51-75", "descricao": "Programa consolidado"},
    "Avancada": {"cor": "#81d4fa", "range": "76-100", "descricao": "Excelencia em governanca"},
}

# ============================================
# Funções Auxiliares
# ============================================

def load_data():
    """Carrega os dados de resumo gerados pelo DANI."""
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_keywords():
    """Carrega palavras-chave do arquivo."""
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []


def save_keywords(keywords_list):
    """Salva palavras-chave no arquivo."""
    os.makedirs(os.path.dirname(KEYWORDS_FILE), exist_ok=True)
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(keywords_list))


def clear_results():
    """Limpa os resultados salvos."""
    files_cleared = []
    if os.path.exists(SUMMARY_FILE):
        os.remove(SUMMARY_FILE)
        files_cleared.append("summary_results.json")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)
        files_cleared.append("output/")
    return files_cleared


def get_output_files():
    """Lista os arquivos de relatório .docx gerados."""
    if not os.path.exists(OUTPUT_DIR):
        return []
    all_files = []
    for orgao_dir in sorted(os.listdir(OUTPUT_DIR)):
        orgao_path = os.path.join(OUTPUT_DIR, orgao_dir)
        if os.path.isdir(orgao_path):
            for file in sorted(os.listdir(orgao_path)):
                if file.endswith('.docx'):
                    all_files.append((orgao_dir, file))
    return all_files


def get_pdf_CIG():
    """Lista os PDFs disponíveis por órgão a partir do diretório de input."""
    if not os.path.exists(INPUT_DIR):
        return {}
    pdfs_por_orgao = {}
    for orgao in sorted(os.listdir(INPUT_DIR)):
        orgao_path = os.path.join(INPUT_DIR, orgao)
        if os.path.isdir(orgao_path):
            pdfs = [f for f in sorted(os.listdir(orgao_path)) if f.lower().endswith('.pdf')]
            if pdfs:
                pdfs_por_orgao[orgao] = pdfs
    return pdfs_por_orgao


def get_pdf_output():
    """Lista os PDFs disponíveis por órgão a partir do diretório output."""
    if not os.path.exists(PDF_OUTPUT_DIR):
        return {}
    pdfs_por_orgao = {}
    for orgao in sorted(os.listdir(PDF_OUTPUT_DIR)):
        orgao_path = os.path.join(PDF_OUTPUT_DIR, orgao)
        if os.path.isdir(orgao_path):
            pdfs = [f for f in sorted(os.listdir(orgao_path)) if f.lower().endswith('.pdf')]
            if pdfs:
                pdfs_por_orgao[orgao] = pdfs
    return pdfs_por_orgao


def get_pdf_integridade():
    """Lista os PDFs disponíveis por órgão a partir do diretório de integridade."""
    if not os.path.exists(INTEGRITY_DIR):
        return {}
    pdfs_por_orgao = {}
    for orgao in sorted(os.listdir(INTEGRITY_DIR)):
        orgao_path = os.path.join(INTEGRITY_DIR, orgao)
        if os.path.isdir(orgao_path):
            pdfs = [f for f in sorted(os.listdir(orgao_path)) if f.lower().endswith('.pdf')]
            if pdfs:
                pdfs_por_orgao[orgao] = pdfs
    return pdfs_por_orgao


# ============================================
# Configuração da Página
# ============================================
st.set_page_config(
    page_title="Dashboard AGIR",
    page_icon="📊",
    layout="wide"
)

# ============================================
# Sidebar - Painel de Controle
# ============================================
st.sidebar.title("Painel de Controle")

# Status dos processos
is_lara_running = os.path.exists(TRIGGER_LARA) or os.path.exists(RUNNING_LARA)
is_dani_running = os.path.exists(TRIGGER_DANI) or os.path.exists(RUNNING_DANI)
is_dani_integrity_running = os.path.exists(TRIGGER_DANI_INTEGRITY) or os.path.exists(RUNNING_DANI_INTEGRITY)
is_lara_completed = os.path.exists(COMPLETED_LARA)
is_dani_completed = os.path.exists(COMPLETED_DANI)
is_dani_integrity_completed = os.path.exists(COMPLETED_DANI_INTEGRITY)
is_process_running = is_lara_running or is_dani_running or is_dani_integrity_running
is_process_completed = is_lara_completed or is_dani_completed or is_dani_integrity_completed

st.sidebar.subheader("Executar")

if st.sidebar.button("LARA-I (Coleta)", disabled=True, use_container_width=True):
    os.makedirs(TRIGGER_DIR, exist_ok=True)
    with open(TRIGGER_LARA, 'w') as f:
        f.write('start')
    st.toast("Processo de coleta iniciado!")
    time.sleep(1)
    st.rerun()

if st.sidebar.button("DANI (Analise Geral)", disabled=True, use_container_width=True):
    os.makedirs(TRIGGER_DIR, exist_ok=True)
    with open(TRIGGER_DANI, 'w') as f:
        f.write('start')
    st.toast("Análise DANI iniciada!")
    time.sleep(1)
    st.rerun()

if st.sidebar.button("DANI (Integridade/IMGA)", disabled=is_process_running, use_container_width=True, type="primary"):
    os.makedirs(TRIGGER_DIR, exist_ok=True)
    with open(TRIGGER_DANI_INTEGRITY, 'w') as f:
        f.write('start')
    st.toast("Análise IMGA iniciada!")
    time.sleep(1)
    st.rerun()

st.sidebar.divider()

# Gerenciamento de Palavras-chave
st.sidebar.subheader("Palavras-chave")
current_keywords = load_keywords()

with st.sidebar.expander("Editar Palavras-chave", expanded=False):
    keywords_text = st.text_area(
        "Uma palavra por linha:",
        value='\n'.join(current_keywords),
        height=150,
        key="keywords_input"
    )
    
    if st.button("Salvar", use_container_width=True):
        new_keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        save_keywords(new_keywords)
        st.success(f"{len(new_keywords)} palavras-chave salvas!")
        time.sleep(1)
        st.rerun()

st.sidebar.caption(f"{len(current_keywords)} palavras-chave configuradas")

st.sidebar.divider()

# Limpar Resultados
st.sidebar.subheader("Manutenção")
if st.sidebar.button("Limpar Resultados", use_container_width=True):
    cleared = clear_results()
    if cleared:
        st.sidebar.success(f"Limpo: {', '.join(cleared)}")
    else:
        st.sidebar.info("Nenhum resultado para limpar")
    time.sleep(1)
    st.rerun()

# ============================================
# Banner de Processo em Execução
# ============================================
if is_process_running:
    if is_dani_integrity_running:
        processo = "DANI (Integridade/IMGA)"
    elif is_lara_running:
        processo = "LARA-I (Coleta)"
    else:
        processo = "DANI (Análise)"
    
    # Banner Customizado (Mais escuro que st.info)
    st.markdown(f"""
    <div style='background-color: #bbdefb; padding: 15px; border-radius: 5px; border-left: 5px solid #1976d2; color: #0d47a1;'>
        <h4>🔄 Processo em execução: {processo}</h4>
        <p>Aguarde, a página será atualizada automaticamente...</p>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()

# Banner de Conclusão
if is_process_completed:
    processos = []
    if is_lara_completed:
        processos.append("LARA-I")
        os.remove(COMPLETED_LARA) if os.path.exists(COMPLETED_LARA) else None
    if is_dani_completed:
        processos.append("DANI")
        os.remove(COMPLETED_DANI) if os.path.exists(COMPLETED_DANI) else None
    if is_dani_integrity_completed:
        processos.append("DANI/IMGA")
        os.remove(COMPLETED_DANI_INTEGRITY) if os.path.exists(COMPLETED_DANI_INTEGRITY) else None
    
    st.markdown(f"""
    <div style='background-color: #c8e6c9; padding: 15px; border-radius: 5px; border-left: 5px solid #2e7d32; color: #1b5e20;'>
        <h4>✅ Concluído: {', '.join(processos)}</h4>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(1)
    st.rerun()

# ============================================
# Conteúdo Principal
# ============================================
st.title("Dashboard AGIR")
st.caption(f"Ambiente de Governança, Integridade e Resultados | Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Tabs principais
tab_resultados, tab_eixos, tab_docs = st.tabs([
    "Resultados", "Eixos Analíticos", "Documentos"
])

summary_data = load_data()

# ============================================
# Tab: Resultados (Consolidada)
# ============================================
with tab_resultados:
    if not summary_data:
        st.warning("Nenhum resultado disponível. Execute uma análise primeiro.")
        st.info("Use o painel lateral para iniciar DANI ou DANI/IMGA")
    else:
        # Métricas resumo
        metadata = summary_data.get('metadata', {})
        resumo = summary_data.get('resumo_geral', {})
        tipo_analise = metadata.get('tipo_analise', 'N/A')
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tipo de Análise", tipo_analise.title())
        col2.metric("Documentos", resumo.get('total_documentos_lidos', 0))
        col3.metric("Palavras", f"{resumo.get('total_palavras_lidas', 0):,}".replace(",", "."))
        col4.metric("Ocorrências", resumo.get('total_ocorrencias', 0))
        
        st.divider()
        
        # Se for análise de integridade, mostrar resultados IMGA
        imga_results = summary_data.get('imga_results', {})
        
        if imga_results:
            st.subheader("Indice de Maturidade da Governanca Algoritmica (IMGA)")
            
            # Resumo IMGA
            docs_count = len(imga_results)
            avg_imga = sum(r.get('imga_global', 0) for r in imga_results.values()) / docs_count if docs_count else 0
            
            col1, col2 = st.columns(2)
            col1.metric("Documentos Analisados", docs_count)
            col2.metric("IMGA Medio", f"{avg_imga:.1f}")
            
            st.divider()
            
            # Quadro Consolidado de Termos (todas as empresas)
            with st.expander("Quadro Consolidado - Termos Encontrados (Todas as Empresas)", expanded=True):
                # Agregar todos os termos por eixo
                termos_consolidados = {}
                for eixo_id in EIXOS_IMGA.keys():
                    termos_consolidados[eixo_id] = {
                        'termos': set(),
                        'total_ocorrencias': 0,
                        'empresas_count': 0,
                        'empresas': []
                    }
                
                for filename, result in imga_results.items():
                    estatisticas = result.get('estatisticas_eixos', {})
                    for eixo_id, stats in estatisticas.items():
                        if eixo_id in termos_consolidados:
                            termos_lista = stats.get('termos_lista', [])
                            if termos_lista:
                                termos_consolidados[eixo_id]['termos'].update(termos_lista)
                                termos_consolidados[eixo_id]['total_ocorrencias'] += stats.get('total_ocorrencias', 0)
                                termos_consolidados[eixo_id]['empresas_count'] += 1
                                termos_consolidados[eixo_id]['empresas'].append(filename)
                
                # Criar tabela consolidada
                dados_consolidados = []
                for eixo_id, dados in termos_consolidados.items():
                    termos_unicos = sorted(list(dados['termos']))
                    if termos_unicos:
                        dados_consolidados.append({
                            "Eixo": eixo_id,
                            "Nome": EIXOS_IMGA.get(eixo_id, {}).get('nome', eixo_id),
                            "Termos Unicos": len(termos_unicos),
                            "Total Ocorr.": dados['total_ocorrencias'],
                            "Empresas": dados['empresas_count'],
                            "Termos Encontrados": ", ".join(termos_unicos)
                        })
                
                if dados_consolidados:
                    df_consolidado = pd.DataFrame(dados_consolidados)
                    st.dataframe(
                        df_consolidado,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Termos Encontrados": st.column_config.TextColumn(
                                "Termos Encontrados",
                                width="large"
                            )
                        }
                    )
                else:
                    st.info("Nenhum termo encontrado nos documentos analisados")
            
            # Nuvens de Palavras por Eixo (Quadro Separado)
            if WORDCLOUD_AVAILABLE:
                with st.expander("Nuvens de Palavras por Eixo", expanded=True):
                    # Reagregar termos para o wordcloud
                    termos_para_nuvem = {}
                    for eixo_id in EIXOS_IMGA.keys():
                        termos_para_nuvem[eixo_id] = set()
                    
                    for filename, result in imga_results.items():
                        estatisticas = result.get('estatisticas_eixos', {})
                        for eixo_id, stats in estatisticas.items():
                            if eixo_id in termos_para_nuvem:
                                termos_lista = stats.get('termos_lista', [])
                                termos_para_nuvem[eixo_id].update(termos_lista)
                    
                    # Filtrar apenas eixos com termos
                    eixos_com_termos = [(eixo_id, termos) for eixo_id, termos in termos_para_nuvem.items() if termos]
                    
                    if eixos_com_termos:
                        # Criar colunas para exibir 2 wordclouds por linha
                        for i in range(0, len(eixos_com_termos), 2):
                            cols = st.columns(2)
                            for j, col in enumerate(cols):
                                if i + j < len(eixos_com_termos):
                                    eixo_id, termos = eixos_com_termos[i + j]
                                    termos_texto = " ".join(list(termos))
                                    
                                    if termos_texto.strip():
                                        with col:
                                            st.caption(f"{eixo_id} - {EIXOS_IMGA.get(eixo_id, {}).get('nome', eixo_id)}")
                                            
                                            try:
                                                # Gerar wordcloud
                                                wc = WordCloud(
                                                    width=400,
                                                    height=200,
                                                    background_color='white',
                                                    colormap='viridis',
                                                    max_words=50
                                                ).generate(termos_texto)
                                                
                                                # Converter para imagem
                                                fig, ax = plt.subplots(figsize=(6, 3))
                                                ax.imshow(wc, interpolation='bilinear')
                                                ax.axis('off')
                                                
                                                # Salvar em buffer
                                                buf = BytesIO()
                                                fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
                                                buf.seek(0)
                                                plt.close(fig)
                                                
                                                st.image(buf, use_container_width=True)
                                            except Exception as e:
                                                st.warning(f"Erro ao gerar nuvem: {e}")
                    else:
                        st.info("Nenhum termo encontrado para gerar nuvens de palavras")
            
            st.divider()
            
            # Resultados por documento
            for filename, result in imga_results.items():
                imga_global = result.get('imga_global', 0)
                faixa = result.get('faixa', 'N/A')
                faixa_info = FAIXAS_MATURIDADE.get(faixa, {})
                
                with st.expander(f"**{filename}** — IMGA: {imga_global} ({faixa})", expanded=True):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Card de resultado
                        st.markdown(f"""
                        <div style='background: {faixa_info.get("cor", "#f5f5f5")}; padding: 1rem; border-radius: 10px; text-align: center;'>
                            <h1 style='margin: 0; color: #000; font-weight: 800;'>{imga_global}</h1>
                            <p style='margin: 0.5rem 0 0 0; font-weight: bold; color: #000;'>{faixa}</p>
                            <small>{faixa_info.get("range", "")}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Metadados
                        metadados = result.get('metadados', {})
                        st.caption(f"{metadados.get('total_palavras', 0):,} palavras".replace(",", "."))
                        st.caption(f"{metadados.get('segmentos_analisados', 0)} segmentos")
                    
                    with col2:
                        # Índices por eixo com estatísticas
                        indices = result.get('indices_eixos', {})
                        estatisticas = result.get('estatisticas_eixos', {})
                        
                        if indices:
                            dados_tabela = []
                            for k, v in indices.items():
                                stats = estatisticas.get(k, {})
                                dados_tabela.append({
                                    "Eixo": f"{EIXOS_IMGA.get(k, {}).get('icone', '')} {k}",
                                    "Nome": EIXOS_IMGA.get(k, {}).get('nome', k),
                                    "Índice": v,
                                    "Termos": stats.get('termos_encontrados', 0),
                                    "Ocorr.": stats.get('total_ocorrencias', 0),
                                })
                            df = pd.DataFrame(dados_tabela)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Detalhes de termos encontrados
                    estatisticas_doc = result.get('estatisticas_eixos', {})
                    if estatisticas_doc:
                        with st.expander("Detalhes dos Termos Encontrados", expanded=False):
                            termos_data = []
                            for eixo_id, stats in estatisticas_doc.items():
                                if stats.get('termos_encontrados', 0) > 0:
                                    termos_lista = stats.get('termos_lista', [])
                                    boosters = stats.get('boosters', {})
                                    boosters_ativos = [b.replace('B1_', '').replace('B2_', '').replace('B3_', '').replace('B4_', '') 
                                                       for b, c in boosters.items() if c > 0]
                                    
                                    termos_data.append({
                                        "Eixo": eixo_id,
                                        "Nome": EIXOS_IMGA.get(eixo_id, {}).get('nome', eixo_id),
                                        "Qtd. Termos": len(termos_lista),
                                        "Termos Encontrados": ", ".join(sorted(termos_lista)),
                                        "Boosters Ativos": ", ".join(boosters_ativos) if boosters_ativos else "-"
                                    })
                            
                            if termos_data:
                                df_termos = pd.DataFrame(termos_data)
                                st.dataframe(
                                    df_termos, 
                                    use_container_width=True, 
                                    hide_index=True,
                                    column_config={
                                        "Termos Encontrados": st.column_config.TextColumn(
                                            "Termos Encontrados",
                                            width="large"
                                        )
                                    }
                                )
                    
                    # Auditoria de Cálculo
                    auditoria = result.get('auditoria', {})
                    if auditoria:
                        with st.expander("Auditoria de Cálculo", expanded=False):
                            st.markdown("**Fórmulas Utilizadas:**")
                            st.code(auditoria.get('formula', 'N/A'), language=None)
                            st.code(auditoria.get('formula_imga', 'N/A'), language=None)
                            st.caption(f"Fator de Normalização: {auditoria.get('fator_normalizacao', 0)} (Total Palavras / 100)")
                            
                            st.markdown("**Detalhamento por Eixo:**")
                            audit_data = []
                            for eixo_id, dados in auditoria.get('eixos', {}).items():
                                audit_data.append({
                                    "Eixo": eixo_id,
                                    "Soma Bruta": dados.get('soma_bruta', 0),
                                    "Segmentos": dados.get('num_segmentos_pontuados', 0),
                                    "Densidade": dados.get('densidade', 0),
                                    "Índice (pré-cap)": dados.get('indice_pre_cap', 0),
                                    "Índice Final": dados.get('indice_final', 0),
                                    "Peso": f"{int(dados.get('peso_metodologia', 0)*100)}%",
                                    "Contribuição": dados.get('contribuicao_imga', 0)
                                })
                            if audit_data:
                                df_audit = pd.DataFrame(audit_data)
                                st.dataframe(df_audit, use_container_width=True, hide_index=True)
                                
                                # Soma das contribuições = IMGA Global
                                total_contrib = sum(d.get('contribuicao_imga', 0) for d in auditoria.get('eixos', {}).values())
                                st.markdown(f"**IMGA Global = Σ Contribuições = {round(total_contrib, 2)}**")
        
        else:
            # Análise normal (keywords)
            st.subheader("Frequência de Palavras-chave")
            keyword_counts = summary_data.get('contagem_keywords_geral', {})
            
            if keyword_counts:
                filtered_kw = {k: v for k, v in keyword_counts.items() if v > 0}
                if filtered_kw:
                    df = pd.DataFrame(list(filtered_kw.items()), columns=['Palavra', 'Ocorrências'])
                    df = df.sort_values('Ocorrências', ascending=False).head(20)
                    st.bar_chart(df.set_index('Palavra'))
                else:
                    st.info("Nenhuma ocorrência encontrada com as palavras-chave configuradas")
            else:
                st.info("Execute uma análise para ver os resultados")

# ============================================
# Tab: Eixos Analíticos
# ============================================
with tab_eixos:
    st.subheader("Taxonomia Analítica IMGA")
    st.caption("Eixos utilizados na classificação automatizada dos relatórios de integridade")
    
    # Exibir eixos em cards
    for eixo_id, info in EIXOS_IMGA.items():
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 1])
            
            with col1:
                st.markdown(f"### {eixo_id}")
                st.caption(eixo_id)
            
            with col2:
                st.markdown(f"**{info['nome']}**")
                st.caption(info['descricao'])
            
            with col3:
                st.metric("Peso", f"{info['peso']}%")
            
            st.divider()
    
    # Faixas de maturidade
    st.subheader("Faixas de Maturidade")
    
    cols = st.columns(4)
    for i, (faixa, info) in enumerate(FAIXAS_MATURIDADE.items()):
        with cols[i]:
            st.markdown(f"""
            <div style='background: {info["cor"]}; padding: 1rem; border-radius: 8px; text-align: center;'>
                <strong>{faixa}</strong><br>
                <small>{info["range"]}</small><br>
                <small>{info["descricao"]}</small>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# Tab: Documentos
# ============================================
with tab_docs:
    st.subheader("Visualizador de Documentos")
    
    doc_type = st.selectbox("Selecione o tipo:", [
        "Atas CIG (Input)", 
        "Planos de Integridade (Input IMGA)",
        "Resultados DANI (Output)"
    ])
    
    if doc_type == "Atas CIG (Input)":
        pdfs = get_pdf_CIG()
        base_dir = INPUT_DIR
    elif doc_type == "Planos de Integridade (Input IMGA)":
        pdfs = get_pdf_integridade()
        base_dir = INTEGRITY_DIR
    else:
        pdfs = get_pdf_output()
        base_dir = PDF_OUTPUT_DIR
    
    if not pdfs:
        st.info("Nenhum documento disponível nesta categoria")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            orgao = st.selectbox("Órgão:", list(pdfs.keys()))
        
        with col2:
            if orgao:
                arquivo = st.selectbox("Arquivo:", pdfs[orgao])
        
        if orgao and arquivo:
            pdf_path = os.path.join(base_dir, orgao, arquivo)
            
            try:
                with open(pdf_path, "rb") as f:
                    pdf_data = base64.b64encode(f.read()).decode('utf-8')
                
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{pdf_data}" width="100%" height="700" type="application/pdf"></iframe>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Erro ao carregar PDF: {e}")