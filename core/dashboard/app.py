"""
Dashboard AGIR - Interface Web para análise de governança e integridade
"""

import time
import html
import streamlit as st
import pandas as pd
import json
import os
import sys
import base64
import shutil
import sqlite3
import requests
from datetime import datetime
from io import BytesIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

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
if not os.path.exists(DATA_DIR) and os.path.exists("data"):
    DATA_DIR = os.path.abspath("data")
DANI_DATA_DIR = os.path.join(DATA_DIR, "dani", "docs")
TRIGGER_DIR = os.path.join(DATA_DIR, "triggers")
INPUT_DIR = os.path.join(DANI_DATA_DIR, "input")
INPUT_CIG_DIR = os.path.join(INPUT_DIR, "cig")
INPUT_PG_DIR = os.path.join(INPUT_DIR, "pg")
INPUT_COMPLIANCE_DIR = os.path.join(INPUT_DIR, "compliance")
OUTPUT_DIR = os.path.join(DANI_DATA_DIR, "output")
SUMMARY_FILE = os.path.join(DANI_DATA_DIR, "summary_results.json")
PDF_DIR = os.path.join(DANI_DATA_DIR, "result_pdf")
PDF_OUTPUT_DIR = os.path.join(PDF_DIR, "output")
INTEGRITY_DIR = os.path.join(DANI_DATA_DIR, "integridade")
KEYWORDS_FILE = os.path.join(DATA_DIR, "dani", "palavras_chaves.txt")
RAG_DIR = os.path.join(DATA_DIR, "rag")
RAG_DB_FILE = os.path.join(RAG_DIR, "agir_rag.db")
RAG_MANIFEST_FILE = os.path.join(RAG_DIR, "index_manifest.json")
RAG_SPRINT7_DIR = os.path.join(RAG_DIR, "sprint7")
RAG_CLASSIFICATIONS_FILE = os.path.join(RAG_SPRINT7_DIR, "classificacoes.json")
RAG_INDICATORS_FILE = os.path.join(RAG_SPRINT7_DIR, "indicadores_orgaos.csv")
RAG_MATRIX_FILE = os.path.join(RAG_SPRINT7_DIR, "criterios_orgaos.csv")
RAG_MANUAL_SAMPLE_FILE = os.path.join(RAG_SPRINT7_DIR, "validacao_manual_amostra.csv")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
PREFERRED_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
)

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


def can_write_trigger_dir():
    """Verifica se o dashboard consegue criar triggers de processamento."""
    try:
        os.makedirs(TRIGGER_DIR, exist_ok=True)
    except OSError:
        return False
    return os.access(TRIGGER_DIR, os.W_OK)


def create_trigger_file(trigger_path, label):
    """Cria trigger e mostra erro acionavel quando o volume esta sem permissao."""
    try:
        os.makedirs(TRIGGER_DIR, exist_ok=True)
        with open(trigger_path, 'w', encoding='utf-8') as f:
            f.write('start')
        return True
    except PermissionError:
        st.sidebar.error(
            f"Sem permissão para iniciar {label}. "
            f"Corrija a permissão de {TRIGGER_DIR} e tente novamente."
        )
    except OSError as exc:
        st.sidebar.error(f"Não foi possível iniciar {label}: {exc}")
    return False


def load_json_file(path):
    """Carrega um JSON local de forma tolerante."""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def load_rag_manifest():
    """Carrega o manifesto da base RAG."""
    return load_json_file(RAG_MANIFEST_FILE)


def get_vector_index_status(manifest):
    """Retorna status amigavel do indice vetorial local."""
    qdrant_info = (manifest or {}).get("qdrant", {})
    indexed_chunks = qdrant_info.get("indexed_chunks", 0)

    if qdrant_info.get("enabled"):
        return "Pronto", f"{indexed_chunks} pontos indexados"

    reason = qdrant_info.get("reason") or "índice ainda não gerado"
    if "qdrant-client" in reason:
        return "Dependência ausente", "Instale qdrant-client e reindexe"

    return "Indisponível", f"{indexed_chunks} pontos indexados · {reason}"


def load_rag_classifications():
    """Carrega classificacoes de conformidade documental."""
    return load_json_file(RAG_CLASSIFICATIONS_FILE) or []


def load_csv_if_exists(path):
    """Carrega CSV se existir."""
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            return pd.DataFrame()
    return pd.DataFrame()


def get_rag_db_counts():
    """Retorna contagens principais da base auditavel RAG."""
    counts = {"documentos": 0, "chunks": 0, "orgaos": 0, "tipos": 0}
    if not os.path.exists(RAG_DB_FILE):
        return counts

    try:
        with sqlite3.connect(RAG_DB_FILE) as conn:
            counts["documentos"] = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            counts["chunks"] = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            counts["orgaos"] = conn.execute("SELECT COUNT(DISTINCT orgao) FROM documents").fetchone()[0]
            counts["tipos"] = conn.execute("SELECT COUNT(DISTINCT tipo_documento) FROM documents").fetchone()[0]
    except Exception:
        return counts
    return counts


def get_rag_filter_options():
    """Lista orgaos e tipos disponiveis no indice RAG."""
    orgaos = []
    tipos = []

    if os.path.exists(RAG_DB_FILE):
        try:
            with sqlite3.connect(RAG_DB_FILE) as conn:
                orgaos = [
                    row[0]
                    for row in conn.execute("SELECT DISTINCT orgao FROM documents WHERE orgao IS NOT NULL ORDER BY orgao").fetchall()
                    if row[0]
                ]
                tipos = [
                    row[0]
                    for row in conn.execute("SELECT DISTINCT tipo_documento FROM documents WHERE tipo_documento IS NOT NULL ORDER BY tipo_documento").fetchall()
                    if row[0]
                ]
        except Exception:
            orgaos = []
            tipos = []

    if not orgaos:
        for base_dir in (INPUT_CIG_DIR, INPUT_PG_DIR, INPUT_COMPLIANCE_DIR, INTEGRITY_DIR):
            if os.path.exists(base_dir):
                orgaos.extend([name for name in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, name))])
        orgaos = sorted(set(orgaos))

    if not tipos:
        tipos = ["cig", "pg", "compliance", "integridade"]

    return orgaos, tipos


def format_score(value):
    """Formata scores numericos para exibicao."""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def escape_html(value):
    """Escapa conteudo documental antes de renderizar em blocos HTML."""
    return html.escape(str(value or ""), quote=True)


def get_rag_value_items():
    """Valor pratico do RAG Lite para a analise de governanca."""
    return [
        {
            "titulo": "Perguntas com fonte",
            "descricao": "Responde sobre o acervo usando trechos, pagina e documento, reduzindo conclusoes sem lastro.",
        },
        {
            "titulo": "Evidencias auditaveis",
            "descricao": "Mostra os fragmentos recuperados e os scores para revisao tecnica ou validacao manual.",
        },
        {
            "titulo": "Conformidade comparavel",
            "descricao": "Converte criterios normativos em indicadores por orgao, eixo IMGA e classificacao.",
        },
    ]


def show_semantic_diagnostic(diagnostico):
    """Mostra quando a busca semantica caiu para o modo lexical."""
    semantic_status = (diagnostico or {}).get("semantico_status", {})
    if semantic_status.get("enabled") is False:
        reason = semantic_status.get("reason") or "indisponivel"
        st.warning(
            "A busca semântica não foi usada nesta consulta; o resultado veio da busca textual auditável. "
            f"Diagnóstico: {reason}"
        )


def run_rag_search(pergunta, orgao=None, tipos_documento=None, top_k=5):
    """Executa busca hibrida RAG a partir do dashboard."""
    from core.services.rag_retrieval_service import RagRetrievalService

    service = RagRetrievalService(data_dir=DATA_DIR)
    response = service.search(
        pergunta=pergunta,
        orgao=orgao or None,
        tipos_documento=tipos_documento or None,
        top_k=top_k,
    )
    return response.to_dict()


def build_evidence_context(evidencias):
    """Monta contexto curto e citavel a partir das evidencias recuperadas."""
    context_lines = []
    for index, evidence in enumerate(evidencias, start=1):
        context_lines.append(
            "\n".join([
                f"[{index}] Documento: {evidence.get('documento', '')}",
                f"Órgão: {evidence.get('orgao', '')}",
                f"Tipo: {evidence.get('tipo_documento', '')}",
                f"Página: {evidence.get('pagina', '')}",
                f"Trecho: {evidence.get('trecho', '')}",
            ])
        )
    return "\n\n".join(context_lines)


def build_extractive_answer(pergunta, evidencias):
    """Gera resposta fundamentada sem LLM, apenas com trechos recuperados."""
    if not evidencias:
        return (
            "Não encontrei evidências suficientes na base indexada para responder a pergunta. "
            "Tente reformular a consulta, remover filtros ou reindexar os documentos."
        )

    top_evidences = evidencias[:3]
    lines = [
        "Encontrei evidências documentais relacionadas à pergunta.",
        "",
        "Síntese baseada nos trechos recuperados:",
    ]
    for index, evidence in enumerate(top_evidences, start=1):
        trecho = evidence.get("trecho", "")
        resumo = trecho[:420].strip()
        if len(trecho) > 420:
            resumo += "..."
        lines.append(
            f"{index}. {resumo} "
            f"Fonte: {evidence.get('documento', '')}, página {evidence.get('pagina', '')}."
        )

    lines.append("")
    lines.append("Como esta resposta não usou LLM, ela preserva os trechos principais em vez de gerar uma conclusão interpretativa.")
    return "\n".join(lines)


def call_ollama(prompt, model):
    """Chama Ollama local/remoto via API HTTP."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def call_gemini(prompt, model):
    """Chama Gemini via REST quando GEMINI_API_KEY estiver configurada."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada.")

    model = resolve_gemini_model(api_key, model)
    candidate_models = [model]
    for preferred in PREFERRED_GEMINI_MODELS:
        preferred_name = preferred if preferred.startswith("models/") else f"models/{preferred}"
        if preferred_name not in candidate_models:
            candidate_models.append(preferred_name)

    last_http_error = None
    for candidate_model in candidate_models:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/{candidate_model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1},
            },
            timeout=120,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            last_http_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in {500, 502, 503, 504}:
                continue
            raise

        payload = response.json()
        candidates = payload.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(part.get("text", "") for part in parts).strip()

    if last_http_error:
        raise last_http_error
    return ""


def resolve_gemini_model(api_key, model):
    """Resolve modelo Gemini configurado ou escolhe um disponivel para generateContent."""
    configured = (model or DEFAULT_GEMINI_MODEL).strip()
    if configured and configured.lower() != "auto":
        return configured if configured.startswith("models/") else f"models/{configured}"

    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    models = [
        item["name"]
        for item in response.json().get("models", [])
        if "generateContent" in item.get("supportedGenerationMethods", [])
    ]
    by_suffix = {name.removeprefix("models/"): name for name in models}
    for preferred in PREFERRED_GEMINI_MODELS:
        if preferred in by_suffix:
            return by_suffix[preferred]
    if not models:
        raise ValueError("Nenhum modelo Gemini com generateContent disponivel para esta chave.")
    return models[0]


def answer_rag_question(pergunta, evidencias, provider="Sem LLM", model=None):
    """Gera uma resposta rastreavel usando modo extrativo, Ollama ou Gemini."""
    if provider == "Sem LLM":
        return build_extractive_answer(pergunta, evidencias)

    if not evidencias:
        return build_extractive_answer(pergunta, evidencias)

    context = build_evidence_context(evidencias)
    prompt = f"""
Você é um assistente documental do projeto AGIR-RAG.
Responda em português do Brasil, de forma objetiva e auditável.
Use somente as evidências fornecidas. Não invente fatos.
Quando fizer uma afirmação, cite a fonte no formato: documento, página.
Se as evidências forem insuficientes, diga claramente que não encontrou base documental suficiente.

Pergunta:
{pergunta}

Evidências:
{context}
""".strip()

    if provider == "Ollama":
        return call_ollama(prompt, model or "llama3.1")
    if provider == "Gemini":
        return call_gemini(prompt, model or DEFAULT_GEMINI_MODEL)
    return build_extractive_answer(pergunta, evidencias)


def run_rag_classification(orgaos=None, tipos_documento=None, max_criterios=None, top_k=5):
    """Gera indicadores de conformidade documental a partir do dashboard."""
    from core.services.rag_classification_service import RagClassificationService

    criteria_path = PROJECT_ROOT / "estrutura_criterios.json"
    service = RagClassificationService(data_dir=DATA_DIR, evidence_top_k=top_k)
    report = service.build_report(
        criteria_path=criteria_path,
        orgaos=orgaos or None,
        tipos_documento=tipos_documento or None,
        max_criterios=max_criterios,
    )
    return report.to_dict()


def classification_report_to_frames(report):
    """Converte o relatorio RAG em tabelas amigaveis para o dashboard."""
    indicadores = pd.DataFrame(report.get("indicadores_orgaos", []))
    classificacoes = pd.DataFrame(report.get("classificacoes", []))

    if not classificacoes.empty:
        classificacoes["trecho_top"] = classificacoes["evidencias"].apply(
            lambda evidencias: (evidencias or [{}])[0].get("trecho", "") if isinstance(evidencias, list) else ""
        )
        classificacoes["documento_top"] = classificacoes["evidencias"].apply(
            lambda evidencias: (evidencias or [{}])[0].get("documento", "") if isinstance(evidencias, list) else ""
        )
        classificacoes["pagina_top"] = classificacoes["evidencias"].apply(
            lambda evidencias: (evidencias or [{}])[0].get("pagina", "") if isinstance(evidencias, list) else ""
        )

    return indicadores, classificacoes


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
    errors = []
    if os.path.exists(SUMMARY_FILE):
        try:
            os.remove(SUMMARY_FILE)
            files_cleared.append("summary_results.json")
        except PermissionError:
            errors.append(f"Sem permissão para remover {SUMMARY_FILE}")
        except OSError as exc:
            errors.append(f"Erro ao remover {SUMMARY_FILE}: {exc}")
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
            os.makedirs(OUTPUT_DIR)
            files_cleared.append("output/")
        except PermissionError:
            errors.append(f"Sem permissão para remover {OUTPUT_DIR}")
        except OSError as exc:
            errors.append(f"Erro ao remover {OUTPUT_DIR}: {exc}")
    return files_cleared, errors


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


def _get_pdfs_por_orgao_em(base_dir: str) -> dict:
    """Lista PDFs por pasta de órgão sob base_dir (ex.: input/cig/)."""
    if not os.path.exists(base_dir):
        return {}
    pdfs_por_orgao = {}
    for orgao in sorted(os.listdir(base_dir)):
        orgao_path = os.path.join(base_dir, orgao)
        if os.path.isdir(orgao_path):
            pdfs = [f for f in sorted(os.listdir(orgao_path)) if f.lower().endswith('.pdf')]
            if pdfs:
                pdfs_por_orgao[orgao] = pdfs
    return pdfs_por_orgao


def get_pdf_CIG():
    """Lista os PDFs de atas CIG (input/cig/)."""
    return _get_pdfs_por_orgao_em(INPUT_CIG_DIR)


def get_pdf_programa_integridade_input():
    """Lista PDFs do programa de integridade coletados pelo LARA (input/pg/)."""
    return _get_pdfs_por_orgao_em(INPUT_PG_DIR)


def get_pdf_compliance_input():
    """Lista PDFs de plano de compliance coletados pelo LARA (input/compliance/)."""
    return _get_pdfs_por_orgao_em(INPUT_COMPLIANCE_DIR)


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

st.markdown("""
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
    }
    .agir-status-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        background: #ffffff;
        min-height: 112px;
    }
    .agir-status-card strong {
        display: block;
        color: #111827;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }
    .agir-muted {color: #6b7280; font-size: 0.85rem;}
    .agir-evidence {
        border-left: 4px solid #2563eb;
        background: #f8fafc;
        padding: 0.75rem 0.9rem;
        border-radius: 6px;
        margin-bottom: 0.7rem;
    }
</style>
""", unsafe_allow_html=True)

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
triggers_writable = can_write_trigger_dir()

st.sidebar.subheader("Módulos")

main_modules = [
    "LARA-I - Coleta",
    "DANI - Análise geral",
    "Análise de Integridade/IMGA",
    "Análise com inteligência artificial",
    "Eixos Analíticos",
]

if "main_section" not in st.session_state:
    st.session_state["main_section"] = main_modules[0]

for module_name in main_modules:
    selected = st.session_state["main_section"] == module_name
    if st.sidebar.button(
        module_name,
        key=f"module_nav_{module_name}",
        width="stretch",
        type="primary" if selected else "secondary",
    ):
        st.session_state["main_section"] = module_name
        st.rerun()

main_section = st.session_state["main_section"]

st.sidebar.divider()
st.sidebar.subheader("Status")

if not triggers_writable:
    st.sidebar.warning(f"Triggers sem permissão de escrita: {TRIGGER_DIR}")
elif is_process_running:
    st.sidebar.info("Há um processo em execução.")
else:
    st.sidebar.success("Pronto para executar.")

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
    
    if st.button("Salvar", width="stretch"):
        new_keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        save_keywords(new_keywords)
        st.success(f"{len(new_keywords)} palavras-chave salvas!")
        time.sleep(1)
        st.rerun()

st.sidebar.caption(f"{len(current_keywords)} palavras-chave configuradas")

st.sidebar.divider()

# Limpar Resultados
st.sidebar.subheader("Manutenção")
if st.sidebar.button("Limpar Resultados", width="stretch"):
    cleared, clear_errors = clear_results()
    if cleared:
        st.sidebar.success(f"Limpo: {', '.join(cleared)}")
    if clear_errors:
        st.sidebar.error("Não foi possível limpar todos os resultados. Execute `make fix-data-permissions` e tente novamente.")
        for error in clear_errors[:3]:
            st.sidebar.caption(error)
    if not cleared and not clear_errors:
        st.sidebar.info("Nenhum resultado para limpar")
    time.sleep(2 if clear_errors else 1)
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

summary_data = load_data()
rag_manifest = load_rag_manifest()
rag_counts = get_rag_db_counts()

# ============================================
# Seção: LARA-I - Coleta
# ============================================
if main_section == "LARA-I - Coleta":
    st.subheader("LARA-I - Coleta")
    st.caption("Coleta e organiza documentos institucionais para análise posterior.")

    if st.button(
        "Iniciar coleta LARA-I",
        disabled=is_process_running or not triggers_writable,
        width="stretch",
    ):
        if create_trigger_file(TRIGGER_LARA, "LARA-I"):
            st.toast("Processo de coleta iniciado!")
            time.sleep(1)
            st.rerun()

    st.markdown("#### Documentos coletados")
    doc_tabs = st.tabs(["Atas CIG", "Programas de integridade", "Planos de compliance"])
    doc_sources = [
        (doc_tabs[0], get_pdf_CIG(), INPUT_CIG_DIR),
        (doc_tabs[1], get_pdf_programa_integridade_input(), INPUT_PG_DIR),
        (doc_tabs[2], get_pdf_compliance_input(), INPUT_COMPLIANCE_DIR),
    ]
    for doc_tab, pdfs, base_dir in doc_sources:
        with doc_tab:
            if not pdfs:
                st.info("Nenhum documento disponível nesta categoria.")
            else:
                rows = [
                    {"Órgão": orgao, "Documentos": len(files)}
                    for orgao, files in sorted(pdfs.items())
                ]
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ============================================
# Seção: DANI - Análise geral
# ============================================
if main_section == "DANI - Análise geral":
    st.subheader("DANI - Análise geral")
    st.caption("Analisa documentos com palavras-chave e consolida frequências e ocorrências.")

    if st.button(
        "Iniciar análise geral",
        disabled=is_process_running or not triggers_writable,
        width="stretch",
    ):
        if create_trigger_file(TRIGGER_DANI, "DANI"):
            st.toast("Análise DANI iniciada!")
            time.sleep(1)
            st.rerun()

    if not summary_data:
        st.warning("Nenhum resultado disponível. Execute uma análise primeiro.")
        st.info("Use o comando local do DANI ou habilite o worker para gerar os resultados.")
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
        
        imga_results = summary_data.get('imga_results', {})

        if imga_results:
            st.info("O resultado carregado é de Integridade/IMGA. Acesse o módulo correspondente na sidebar.")
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
                    st.dataframe(df, width="stretch", hide_index=True)
                else:
                    st.info("Nenhuma ocorrência encontrada com as palavras-chave configuradas")
            else:
                st.info("Execute uma análise para ver os resultados")

# ============================================
# Seção: Análise de Integridade/IMGA
# ============================================
if main_section == "Análise de Integridade/IMGA":
    st.subheader("Análise de Integridade/IMGA")
    st.caption("Avalia maturidade de governança e integridade com base nos eixos IMGA.")

    if st.button(
        "Iniciar análise de Integridade/IMGA",
        disabled=is_process_running or not triggers_writable,
        width="stretch",
        type="primary",
    ):
        if create_trigger_file(TRIGGER_DANI_INTEGRITY, "DANI/IMGA"):
            st.toast("Análise IMGA iniciada!")
            time.sleep(1)
            st.rerun()

    imga_results = (summary_data or {}).get('imga_results', {})
    if not summary_data:
        st.warning("Nenhum resultado disponível. Execute a análise de Integridade/IMGA primeiro.")
    elif not imga_results:
        st.info("O resultado carregado não contém dados IMGA. Execute a análise de Integridade/IMGA.")
    else:
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
                        width="stretch",
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
                                                
                                                st.image(buf, width="stretch")
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
                            st.dataframe(df, width="stretch", hide_index=True)
                    
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
                                    width="stretch",
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
                                st.dataframe(df_audit, width="stretch", hide_index=True)
                                
                                # Soma das contribuições = IMGA Global
                                total_contrib = sum(d.get('contribuicao_imga', 0) for d in auditoria.get('eixos', {}).values())
                                st.markdown(f"**IMGA Global = Σ Contribuições = {round(total_contrib, 2)}**")
# ============================================
# Seção: Análise com inteligência artificial
# ============================================
if main_section == "Análise com inteligência artificial":
    st.subheader("Análise com inteligência artificial")
    st.caption("AGIR-RAG Lite transforma documentos públicos em respostas citáveis, evidências revisáveis e indicadores de conformidade.")

    orgaos_rag, tipos_rag = get_rag_filter_options()
    sprint7_indicators = load_csv_if_exists(RAG_INDICATORS_FILE)
    sprint7_matrix = load_csv_if_exists(RAG_MATRIX_FILE)
    sprint7_classifications = load_rag_classifications()

    value_cols = st.columns(3)
    for col, item in zip(value_cols, get_rag_value_items()):
        with col:
            st.markdown(f"""
            <div class="agir-status-card">
                <strong>{escape_html(item["titulo"])}</strong>
                <div class="agir-muted">{escape_html(item["descricao"])}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Documentos", rag_counts["documentos"])
    col2.metric("Chunks", rag_counts["chunks"])
    col3.metric("Órgãos", rag_counts["orgaos"])
    col4.metric("Classificações", len(sprint7_classifications))

    status_cols = st.columns(3)
    with status_cols[0]:
        sqlite_status = "Pronto" if rag_counts["chunks"] > 0 else "Vazio"
        st.markdown(f"""
        <div class="agir-status-card">
            <strong>Base auditável</strong>
            <div>{sqlite_status}</div>
            <div class="agir-muted">{RAG_DB_FILE}</div>
        </div>
        """, unsafe_allow_html=True)
    with status_cols[1]:
        qdrant_status, qdrant_detail = get_vector_index_status(rag_manifest)
        st.markdown(f"""
        <div class="agir-status-card">
            <strong>Índice vetorial</strong>
            <div>{qdrant_status}</div>
            <div class="agir-muted">{qdrant_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    with status_cols[2]:
        report_status = "Gerado" if not sprint7_indicators.empty else "Pendente"
        st.markdown(f"""
        <div class="agir-status-card">
            <strong>Indicadores de conformidade</strong>
            <div>{report_status}</div>
            <div class="agir-muted">Classificações, matriz comparativa e amostra de validação</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    qa_tab, search_tab, classify_tab, indicators_tab = st.tabs([
        "Perguntar ao acervo",
        "Buscar evidências",
        "Gerar conformidade",
        "Indicadores",
    ])

    with qa_tab:
        st.markdown("#### Pergunte aos documentos")
        st.caption("Use para responder perguntas de auditoria com evidências rastreáveis. Gemini é o modo atual quando a chave estiver configurada.")

        if "rag_chat_history" not in st.session_state:
            st.session_state["rag_chat_history"] = []

        gemini_available = bool(os.getenv("GEMINI_API_KEY", "").strip())
        provider_options = ["Gemini", "Sem LLM", "Ollama"] if gemini_available else ["Sem LLM", "Ollama"]
        llm_status = (
            f"Gemini ativo como padrão ({DEFAULT_GEMINI_MODEL})."
            if gemini_available
            else "Configure GEMINI_API_KEY para ativar Gemini como modo padrão."
        )
        st.caption(f"{llm_status} Ollama permanece disponível via OLLAMA_BASE_URL.")

        with st.form("rag_qa_form"):
            pergunta_chat = st.text_area(
                "Pergunta",
                value="O órgão possui evidências de programa de integridade formalizado?",
                height=90,
                key="rag_qa_question",
            )
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                orgao_chat = st.selectbox(
                    "Órgão",
                    ["Todos"] + orgaos_rag,
                    index=0,
                    key="rag_qa_orgao",
                )
            with col2:
                tipos_chat = st.multiselect(
                    "Tipos documentais",
                    tipos_rag,
                    default=tipos_rag[:2] if len(tipos_rag) >= 2 else tipos_rag,
                    key="rag_qa_tipos",
                )
            with col3:
                top_k_chat = st.number_input("Fontes", min_value=1, max_value=10, value=5, step=1, key="rag_qa_top_k")

            col1, col2 = st.columns([1, 2])
            with col1:
                provider = st.selectbox("Modo de resposta", provider_options, key="rag_qa_provider")
            with col2:
                default_model = "llama3.1" if provider == "Ollama" else DEFAULT_GEMINI_MODEL
                model = st.text_input(
                    "Modelo",
                    value=default_model,
                    disabled=provider == "Sem LLM",
                    key="rag_qa_model",
                )

            ask_submitted = st.form_submit_button("Responder com evidências", width="stretch")

        if ask_submitted:
            if not pergunta_chat.strip():
                st.warning("Informe uma pergunta para consultar o acervo.")
            elif rag_counts["chunks"] == 0:
                st.warning("A base RAG está vazia. Execute a indexação antes de perguntar ao acervo.")
            else:
                with st.spinner("Recuperando evidências e preparando resposta..."):
                    try:
                        search_result = run_rag_search(
                            pergunta=pergunta_chat,
                            orgao=None if orgao_chat == "Todos" else orgao_chat,
                            tipos_documento=tipos_chat,
                            top_k=int(top_k_chat),
                        )
                        evidencias = search_result.get("evidencias", [])
                        answer = answer_rag_question(
                            pergunta=pergunta_chat,
                            evidencias=evidencias,
                            provider=provider,
                            model=model,
                        )
                        st.session_state["rag_chat_history"].insert(
                            0,
                            {
                                "pergunta": pergunta_chat,
                                "resposta": answer,
                                "provider": provider,
                                "modelo": model if provider != "Sem LLM" else "extrativo",
                                "evidencias": evidencias,
                                "diagnostico": search_result.get("diagnostico", {}),
                            },
                        )
                    except Exception as exc:
                        st.error(f"Erro ao responder com RAG: {exc}")

        if not st.session_state["rag_chat_history"]:
            st.info("Faça uma pergunta para iniciar a interação com o acervo documental.")
        else:
            for item_index, item in enumerate(st.session_state["rag_chat_history"], start=1):
                with st.container():
                    st.markdown(f"**Pergunta {item_index}:** {item['pergunta']}")
                    st.markdown(item["resposta"])
                    st.caption(f"Modo: {item['provider']} · Modelo: {item['modelo']} · Fontes: {len(item['evidencias'])}")
                    show_semantic_diagnostic(item.get("diagnostico"))

                    with st.expander("Ver evidências usadas", expanded=item_index == 1):
                        if not item["evidencias"]:
                            st.info("Nenhuma evidência foi recuperada para esta resposta.")
                        for idx, evidencia in enumerate(item["evidencias"], start=1):
                            st.markdown(f"""
                            <div class="agir-evidence">
                                <strong>{idx}. {escape_html(evidencia.get('documento', ''))}</strong>
                                <div class="agir-muted">
                                    {escape_html(evidencia.get('orgao', ''))} · {escape_html(evidencia.get('tipo_documento', ''))}
                                    · página {escape_html(evidencia.get('pagina', ''))}
                                    · score {escape_html(format_score(evidencia.get('score')))}
                                </div>
                                <p>{escape_html(evidencia.get('trecho', ''))}</p>
                            </div>
                            """, unsafe_allow_html=True)

                    st.divider()

    with search_tab:
        st.markdown("#### Consulta documental")
        with st.form("rag_search_form"):
            pergunta = st.text_input(
                "Pergunta normativa",
                value="A organização possui plano de integridade publicado?",
            )
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                orgao_selecionado = st.selectbox(
                    "Órgão",
                    ["Todos"] + orgaos_rag,
                    index=0,
                    key="rag_search_orgao",
                )
            with col2:
                tipos_selecionados = st.multiselect(
                    "Tipos documentais",
                    tipos_rag,
                    default=tipos_rag[:2] if len(tipos_rag) >= 2 else tipos_rag,
                    key="rag_search_tipos",
                )
            with col3:
                top_k = st.number_input("Evidências", min_value=1, max_value=20, value=5, step=1)

            submitted = st.form_submit_button("Buscar evidências", width="stretch")

        if submitted:
            if not pergunta.strip():
                st.warning("Informe uma pergunta normativa.")
            elif rag_counts["chunks"] == 0:
                st.warning("A base RAG está vazia. Execute a indexação da Sprint 5 antes da busca.")
            else:
                with st.spinner("Executando recuperação híbrida..."):
                    try:
                        result = run_rag_search(
                            pergunta=pergunta,
                            orgao=None if orgao_selecionado == "Todos" else orgao_selecionado,
                            tipos_documento=tipos_selecionados,
                            top_k=int(top_k),
                        )
                        st.session_state["rag_search_result"] = result
                    except Exception as exc:
                        st.error(f"Erro na busca RAG: {exc}")

        result = st.session_state.get("rag_search_result")
        if result:
            evidencias = result.get("evidencias", [])
            diagnostico = result.get("diagnostico", {})
            st.caption(
                f"{len(evidencias)} evidência(s) retornada(s) | "
                f"lexical: {diagnostico.get('lexical_resultados', 0)} | "
                f"semântico: {diagnostico.get('semantico_resultados', 0)}"
            )

            if not evidencias:
                st.info("Nenhuma evidência encontrada para a consulta.")
            show_semantic_diagnostic(diagnostico)
            for idx, evidencia in enumerate(evidencias, start=1):
                st.markdown(f"""
                <div class="agir-evidence">
                    <strong>{idx}. {escape_html(evidencia.get('documento', ''))}</strong>
                    <div class="agir-muted">
                        {escape_html(evidencia.get('orgao', ''))} · {escape_html(evidencia.get('tipo_documento', ''))}
                        · página {escape_html(evidencia.get('pagina', ''))}
                        · score {escape_html(format_score(evidencia.get('score')))}
                    </div>
                    <p>{escape_html(evidencia.get('trecho', ''))}</p>
                </div>
                """, unsafe_allow_html=True)

    with classify_tab:
        st.markdown("#### Gerar conformidade documental")
        st.caption("Avalia os critérios normativos com base nas evidências recuperadas e calcula indicadores auditáveis por órgão.")

        with st.form("rag_classification_form"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                orgaos_classificacao = st.multiselect(
                    "Órgãos",
                    orgaos_rag,
                    default=orgaos_rag[:1],
                    key="rag_class_orgaos",
                )
            with col2:
                tipos_classificacao = st.multiselect(
                    "Tipos documentais",
                    tipos_rag,
                    default=tipos_rag,
                    key="rag_class_tipos",
                )
            with col3:
                max_criterios = st.number_input(
                    "Critérios",
                    min_value=1,
                    max_value=200,
                    value=10,
                    step=1,
                    help="Limite de critérios para execução controlada.",
                )

            top_k_classificacao = st.slider("Evidências por critério", min_value=1, max_value=10, value=5)
            run_classification = st.form_submit_button("Calcular conformidade", width="stretch")

        if run_classification:
            if rag_counts["chunks"] == 0:
                st.warning("A base RAG está vazia. Execute a indexação da Sprint 5 antes da classificação.")
            elif not orgaos_classificacao:
                st.warning("Selecione ao menos um órgão.")
            else:
                with st.spinner("Avaliando critérios e recalculando indicadores..."):
                    try:
                        report = run_rag_classification(
                            orgaos=orgaos_classificacao,
                            tipos_documento=tipos_classificacao,
                            max_criterios=int(max_criterios),
                            top_k=int(top_k_classificacao),
                        )
                        st.session_state["rag_classification_report"] = report
                        sprint7_indicators = load_csv_if_exists(RAG_INDICATORS_FILE)
                        sprint7_matrix = load_csv_if_exists(RAG_MATRIX_FILE)
                        sprint7_classifications = load_rag_classifications()
                        st.success("Indicadores de conformidade gerados com sucesso.")
                    except Exception as exc:
                        st.error(f"Erro ao gerar classificação: {exc}")

        report = st.session_state.get("rag_classification_report")
        if report:
            indicadores_report, classificacoes_report = classification_report_to_frames(report)
            parametros = report.get("parametros", {})
            arquivos = report.get("arquivos", {})

            st.markdown("#### Resultado da conformidade")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Órgãos avaliados", len(parametros.get("orgaos") or []))
            col2.metric("Critérios avaliados", len(classificacoes_report))
            col3.metric(
                "Conformidade média",
                f"{format_score(indicadores_report.get('conformidade_percentual', pd.Series([0])).mean())}%",
            )
            col4.metric(
                "IMGA médio",
                format_score(indicadores_report.get("imga_global", pd.Series([0])).mean()),
            )

            if not classificacoes_report.empty and "classificacao" in classificacoes_report.columns:
                distribuicao = (
                    classificacoes_report["classificacao"]
                    .value_counts()
                    .rename_axis("Classificação")
                    .reset_index(name="Critérios")
                )
                st.markdown("##### Distribuição dos achados")
                st.dataframe(distribuicao, width="stretch", hide_index=True)

            if not indicadores_report.empty:
                st.markdown("##### Síntese por órgão")
                colunas_indicadores = [
                    col
                    for col in [
                        "orgao",
                        "criterios_avaliados",
                        "conformidade_percentual",
                        "imga_global",
                        "faixa",
                    ]
                    if col in indicadores_report.columns
                ]
                st.dataframe(
                    indicadores_report[colunas_indicadores],
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "conformidade_percentual": st.column_config.NumberColumn("Conformidade", format="%.1f%%"),
                        "imga_global": st.column_config.NumberColumn("IMGA", format="%.2f"),
                    },
                )

            if not classificacoes_report.empty:
                st.markdown("##### Critérios e evidência principal")
                colunas_classificacoes = [
                    col
                    for col in [
                        "orgao",
                        "criterio",
                        "eixo_imga",
                        "classificacao",
                        "score_recuperacao",
                        "justificativa",
                        "documento_top",
                        "pagina_top",
                        "trecho_top",
                    ]
                    if col in classificacoes_report.columns
                ]
                st.dataframe(
                    classificacoes_report[colunas_classificacoes],
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "score_recuperacao": st.column_config.NumberColumn("Score", format="%.3f"),
                        "justificativa": st.column_config.TextColumn("Justificativa", width="large"),
                        "trecho_top": st.column_config.TextColumn("Trecho principal", width="large"),
                    },
                )

            if arquivos:
                with st.expander("Arquivos gerados", expanded=False):
                    for nome, caminho in arquivos.items():
                        st.caption(f"{nome}: {caminho}")

    with indicators_tab:
        st.markdown("#### Indicadores de conformidade documental")

        if sprint7_indicators.empty:
            st.info("Nenhum indicador de conformidade encontrado. Gere os resultados em Conformidade.")
        else:
            display_indicators = sprint7_indicators.copy()
            if "imga_global" in display_indicators.columns:
                display_indicators = display_indicators.sort_values("imga_global", ascending=False)

            col1, col2, col3 = st.columns(3)
            col1.metric("Órgãos avaliados", len(display_indicators))
            col2.metric(
                "IMGA médio",
                format_score(display_indicators.get("imga_global", pd.Series([0])).mean()),
            )
            col3.metric(
                "Conformidade média",
                f"{format_score(display_indicators.get('conformidade_percentual', pd.Series([0])).mean())}%",
            )

            chart_cols = [col for col in ["orgao", "imga_global", "conformidade_percentual"] if col in display_indicators.columns]
            if len(chart_cols) >= 2:
                chart_df = display_indicators[chart_cols].set_index("orgao")
                st.bar_chart(chart_df)

            st.dataframe(display_indicators, width="stretch", hide_index=True)

        st.markdown("#### Matriz órgão x critério")
        if sprint7_matrix.empty:
            st.caption("A matriz será exibida após o cálculo dos indicadores de conformidade.")
        else:
            filtros_col1, filtros_col2 = st.columns(2)
            with filtros_col1:
                filtro_orgao = st.multiselect(
                    "Filtrar órgãos",
                    sorted(sprint7_matrix["orgao"].dropna().unique()) if "orgao" in sprint7_matrix.columns else [],
                    key="rag_report_orgao_filter",
                )
            with filtros_col2:
                filtro_classificacao = st.multiselect(
                    "Filtrar classificações",
                    sorted(sprint7_matrix["classificacao"].dropna().unique()) if "classificacao" in sprint7_matrix.columns else [],
                    key="rag_report_class_filter",
                )

            filtered_matrix = sprint7_matrix.copy()
            if filtro_orgao and "orgao" in filtered_matrix.columns:
                filtered_matrix = filtered_matrix[filtered_matrix["orgao"].isin(filtro_orgao)]
            if filtro_classificacao and "classificacao" in filtered_matrix.columns:
                filtered_matrix = filtered_matrix[filtered_matrix["classificacao"].isin(filtro_classificacao)]

            st.dataframe(
                filtered_matrix,
                width="stretch",
                hide_index=True,
                column_config={
                    "trecho_top": st.column_config.TextColumn("Trecho principal", width="large"),
                    "score_recuperacao": st.column_config.NumberColumn("Score", format="%.3f"),
                },
            )

        st.markdown("#### Validação manual")
        if os.path.exists(RAG_MANUAL_SAMPLE_FILE):
            st.download_button(
                "Baixar amostra de validação",
                data=open(RAG_MANUAL_SAMPLE_FILE, "rb").read(),
                file_name="validacao_manual_amostra.csv",
                mime="text/csv",
                width="stretch",
            )
        else:
            st.caption("A amostra de validação manual ainda não foi gerada.")

# ============================================
# Seção: Eixos Analíticos
# ============================================
if main_section == "Eixos Analíticos":
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
# Seção: Documentos
# ============================================
if main_section == "Documentos":
    st.subheader("Visualizador de Documentos")
    
    doc_type = st.selectbox("Selecione o tipo:", [
        "Atas CIG (Input)",
        "Programa de integridade (Input)",
        "Plano de compliance (Input)",
        "Planos de Integridade (Input IMGA)",
        "Resultados DANI (Output)"
    ])
    
    if doc_type == "Atas CIG (Input)":
        pdfs = get_pdf_CIG()
        base_dir = INPUT_CIG_DIR
    elif doc_type == "Programa de integridade (Input)":
        pdfs = get_pdf_programa_integridade_input()
        base_dir = INPUT_PG_DIR
    elif doc_type == "Plano de compliance (Input)":
        pdfs = get_pdf_compliance_input()
        base_dir = INPUT_COMPLIANCE_DIR
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
