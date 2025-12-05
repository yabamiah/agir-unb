import time
import streamlit as st
import pandas as pd
import json
import os
import base64
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DANI_DATA_DIR = os.path.join(DATA_DIR, "dani", "docs")
TRIGGER_DIR = os.path.join(DATA_DIR, "triggers")
INPUT_DIR = os.path.join(DANI_DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DANI_DATA_DIR, "output")
SUMMARY_FILE = os.path.join(DANI_DATA_DIR, "summary_results.json")
PDF_DIR = os.path.join(DANI_DATA_DIR, "result_pdf")
PDF_OUTPUT_DIR = os.path.join(PDF_DIR, "output")

TRIGGER_LARA = os.path.join(TRIGGER_DIR, "run_lara.trigger")
TRIGGER_DANI = os.path.join(TRIGGER_DIR, "run_dani.trigger")
RUNNING_LARA = os.path.join(TRIGGER_DIR, "running_lara.trigger")
RUNNING_DANI = os.path.join(TRIGGER_DIR, "running_dani.trigger")
COMPLETED_LARA = os.path.join(TRIGGER_DIR, "completed_lara.trigger")
COMPLETED_DANI = os.path.join(TRIGGER_DIR, "completed_dani.trigger")


def load_data():
    """Carrega os dados de resumo gerados pelo DANI."""
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


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
    """Lista os PDFs disponíveis por órgão a partir do diretório de input do DANI."""
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

def get_pdf_DANI():
    if not os.path.exists(PDF_DIR):
        return {}

    pdfs_por_orgao = {}
    for orgao in sorted(os.listdir(PDF_DIR)):
        orgao_path = os.path.join(PDF_DIR, orgao)
        if os.path.isdir(orgao_path):
            pdfs = [f for f in sorted(os.listdir(orgao_path)) if f.lower().endswith('.pdf')]
            if pdfs:
                pdfs_por_orgao[orgao] = pdfs
    return pdfs_por_orgao

def get_pdf_output():
    """Lista os PDFs disponíveis por órgão a partir do diretório output dentro de result_pdf."""
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


st.set_page_config(
    page_title="Dashboard AGIR",
    page_icon="📊",
    layout="wide"
)

st.sidebar.title("🤖 Painel de Controle")
st.sidebar.info("Dispare os processos de coleta e análise de dados.")

#os.makedirs(TRIGGER_DIR, exist_ok=True)

is_lara_running = os.path.exists(TRIGGER_LARA) or os.path.exists(RUNNING_LARA)
is_dani_running = os.path.exists(TRIGGER_DANI) or os.path.exists(RUNNING_DANI)
is_lara_completed = os.path.exists(COMPLETED_LARA)
is_dani_completed = os.path.exists(COMPLETED_DANI)

is_process_running = is_lara_running or is_dani_running
is_process_completed = is_lara_completed or is_dani_completed

if st.sidebar.button("Executar LARA-I (Coleta)", disabled=is_process_running):
    with open(TRIGGER_LARA, 'w') as f:
        f.write('start')
    st.sidebar.success("Sinal para iniciar LARA-I enviado!")
    st.toast("O processo de coleta foi iniciado em segundo plano.")
    time.sleep(1)
    st.rerun()

if st.sidebar.button("Executar DANI (Análise)", disabled=is_process_running):
    with open(TRIGGER_DANI, 'w') as f:
        f.write('start')
    st.sidebar.success("Sinal para iniciar DANI enviado!")
    st.toast("O processo de análise foi iniciado em segundo plano.")
    time.sleep(1)
    st.rerun()

# Auto-refresh enquanto o processo está rodando ou quando acabou de completar
if is_process_running:
    processo = "LARA-I (Coleta)" if is_lara_running else "DANI (Análise)"
    
    # Banner de status com loader e auto-refresh
    with st.container():
        # CSS para animação do loader
        st.markdown("""
        <style>
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .spinner-icon {
            display: inline-block;
            animation: spin 2s linear infinite;
        }
        .loader-banner {
            padding: 1rem;
            background-color: #e3f2fd;
            border-left: 5px solid #2196f3;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='loader-banner'>
            <h4 style='margin: 0; color: #1565c0;'>
                🔄 <span class='spinner-icon'>⚙️</span> 
                Processo em Execução: {processo}
            </h4>
            <p style='margin: 0.5rem 0 0 0; color: #424242;'>
                ⏱️ O dashboard será atualizado automaticamente quando o processo concluir.<br>
                📊 Aguarde... Processando dados...
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Aguardar 3 segundos antes de atualizar
    time.sleep(3)
    st.rerun()

# Detectar quando um processo acabou de completar e fazer refresh final
if is_process_completed:
    processos_completos = []
    if is_lara_completed:
        processos_completos.append("LARA-I (Coleta)")
    if is_dani_completed:
        processos_completos.append("DANI (Análise)")
    
    processo_completo = " e ".join(processos_completos)
    
    # Banner de sucesso
    with st.container():
        st.markdown("""
        <style>
        .success-banner {
            padding: 1rem;
            background-color: #e8f5e9;
            border-left: 5px solid #4caf50;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='success-banner'>
            <h4 style='margin: 0; color: #2e7d32;'>
                ✅ Processo(s) Concluído(s): {processo_completo}
            </h4>
            <p style='margin: 0.5rem 0 0 0; color: #424242;'>
                📊 Atualizando dashboard com os resultados...
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Remove os arquivos de completed após detectar
    if is_lara_completed and os.path.exists(COMPLETED_LARA):
        os.remove(COMPLETED_LARA)
    if is_dani_completed and os.path.exists(COMPLETED_DANI):
        os.remove(COMPLETED_DANI)
    
    # Aguardar 1 segundo e fazer refresh final
    time.sleep(1)
    st.rerun()

st.title("📊 Dashboard de Análise - AGIR")
st.caption(f"Resultados da última análise. Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

summary_data = load_data()

if not summary_data:
    st.warning("Nenhum dado de análise encontrado. Execute o DANI primeiro para gerar os resultados.")
    st.info("Para iniciar, use os botões no 'Painel de Controle' ao lado.")
else:
    st.success("Dados da última análise carregados com sucesso!")

    col1, col2, col3 = st.columns(3)
    col1.metric("Órgão(s) Analisado(s)", ", ".join(summary_data.get('orgaos_analisados', ['N/A'])))
    col2.metric("Total de Documentos Lidos", len(summary_data.get('documentos_lidos', [])))
    col3.metric("Total de Palavras Lidas", f"{summary_data.get('total_palavras_lidas', 0):,}".replace(",", "."))

    st.subheader("Frequência de Palavras-chave")
    keyword_counts = summary_data.get('contagem_keywords', {})

    if keyword_counts:
        df_keywords = pd.DataFrame(
            keyword_counts.items(),
            columns=['Palavra-chave', 'Ocorrências']
        ).sort_values(by="Ocorrências", ascending=False)

        st.bar_chart(df_keywords.set_index('Palavra-chave'))
    else:
        st.info("Nenhuma ocorrência de palavra-chave encontrada.")

    st.subheader("Relatórios Gerados (.docx)")
    output_files = get_output_files()

    if output_files:
        df_files = pd.DataFrame(output_files, columns=["Órgão", "Arquivo"])
        st.dataframe(df_files, use_container_width=True)
        st.info("Para baixar os relatórios, acesse o diretório `data/dani/docs/output` no seu computador.")
    else:
        st.info("Nenhum relatório .docx foi gerado ainda.")

    with st.expander("📄 Visualizar Atas do Comitê Interno de Governança", expanded=False):
        pdfs_disponiveis = get_pdf_CIG()

        if not pdfs_disponiveis:
            st.info("Nenhum arquivo PDF encontrado no diretório de entrada (`data/dani/docs/input`).")
        else:
            col_pdf1, col_pdf2 = st.columns(2)

            with col_pdf1:
                selected_orgao = st.selectbox("Selecione o órgão", list(pdfs_disponiveis.keys()))

            with col_pdf2:
                selected_pdf = st.selectbox("Selecione o arquivo PDF", pdfs_disponiveis[selected_orgao])

            if selected_orgao and selected_pdf:
                pdf_path = os.path.join(INPUT_DIR, selected_orgao, selected_pdf)

                try:
                    with open(pdf_path, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')

                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(f"Erro: O arquivo '{selected_pdf}' não foi encontrado no caminho esperado.")
                except Exception as e:
                    st.error(f"Ocorreu um erro ao tentar exibir o PDF: {e}")

    with st.expander("📄 Visualizar Resultados DANI", expanded=False):
        pdfs_output = get_pdf_output()

        if not pdfs_output:
            st.info("Nenhum arquivo PDF encontrado no diretório de saída (`data/dani/docs/result_pdf/output`).")
        else:
            col_pdf1, col_pdf2 = st.columns(2)

            with col_pdf1:
                selected_orgao_output = st.selectbox("Selecione o órgão", list(pdfs_output.keys()), key="orgao_output")

            with col_pdf2:
                selected_pdf_output = st.selectbox("Selecione o arquivo PDF", pdfs_output[selected_orgao_output], key="pdf_output")

            if selected_orgao_output and selected_pdf_output:
                pdf_path_output = os.path.join(PDF_OUTPUT_DIR, selected_orgao_output, selected_pdf_output)

                try:
                    with open(pdf_path_output, "rb") as f:
                        base64_pdf_output = base64.b64encode(f.read()).decode('utf-8')

                    pdf_display_output = f'<iframe src="data:application/pdf;base64,{base64_pdf_output}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display_output, unsafe_allow_html=True)
                except FileNotFoundError:
                    st.error(f"Erro: O arquivo '{selected_pdf_output}' não foi encontrado no caminho esperado.")
                except Exception as e:
                    st.error(f"Ocorreu um erro ao tentar exibir o PDF: {e}")