"""
DANI Worker - Processador em Background
Monitora triggers e executa DANI conforme solicitado pelo dashboard.
"""

import os
import sys
import time

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

# Configuração de caminhos
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
TRIGGER_DIR = os.path.join(DATA_DIR, "triggers")
KEYWORDS_FILE = os.getenv(
    "KEYWORDS_FILE", os.path.join(DATA_DIR, "dani", "palavras_chaves.txt")
)

# Triggers
TRIGGER_DANI = os.path.join(TRIGGER_DIR, "run_dani.trigger")
TRIGGER_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "run_dani_integrity.trigger")

# Status files
RUNNING_DANI = os.path.join(TRIGGER_DIR, "running_dani.trigger")
RUNNING_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "running_dani_integrity.trigger")
COMPLETED_DANI = os.path.join(TRIGGER_DIR, "completed_dani.trigger")
COMPLETED_DANI_INTEGRITY = os.path.join(TRIGGER_DIR, "completed_dani_integrity.trigger")

# Configurar logger
logger.add(
    os.path.join(DATA_DIR, "logs", "dani_worker.log"),
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)


def run_dani_normal():
    """Executa DANI no modo normal (análise geral)."""
    from core.models.dani import Dani

    logger.info("🚀 Iniciando DANI (modo normal)...")

    try:
        d = Dani(all_orgaos=True, keywords_file=KEYWORDS_FILE)
        d.run()
        logger.info("✅ DANI (normal) concluído com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao executar DANI: {e}")
        return False


def run_dani_integrity():
    """Executa DANI no modo integridade (IMGA)."""
    from core.models.dani import Dani

    logger.info("🚀 Iniciando DANI (modo integridade/IMGA)...")

    try:
        d = Dani(
            only_integrity_plans=True, all_orgaos=True, keywords_file=KEYWORDS_FILE
        )
        d.run()
        logger.info("✅ DANI (integridade/IMGA) concluído com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao executar DANI (integridade): {e}")
        return False


def process_trigger(trigger_path, running_path, completed_path, process_func, name):
    """Processa um trigger se existir."""
    if os.path.exists(trigger_path):
        logger.info(f"📥 Trigger {name} detectado!")

        # Remove trigger e cria running flag
        os.remove(trigger_path)
        with open(running_path, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

        try:
            process_func()
        finally:
            # Remove running flag
            if os.path.exists(running_path):
                os.remove(running_path)

            # Cria completed flag
            with open(completed_path, "w") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

        return True
    return False


def main():
    """Loop principal do worker."""
    logger.info("=" * 60)
    logger.info("🤖 DANI Worker iniciado")
    logger.info(f"📁 Diretório de triggers: {TRIGGER_DIR}")
    logger.info(f"📄 Arquivo de keywords: {KEYWORDS_FILE}")
    logger.info("=" * 60)

    # Garantir que diretório de triggers existe
    os.makedirs(TRIGGER_DIR, exist_ok=True)

    while True:
        try:
            # Verificar trigger DANI normal
            process_trigger(
                TRIGGER_DANI, RUNNING_DANI, COMPLETED_DANI, run_dani_normal, "DANI"
            )

            # Verificar trigger DANI integridade
            process_trigger(
                TRIGGER_DANI_INTEGRITY,
                RUNNING_DANI_INTEGRITY,
                COMPLETED_DANI_INTEGRITY,
                run_dani_integrity,
                "DANI Integridade",
            )

        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")

        # Aguardar antes de verificar novamente
        time.sleep(2)


if __name__ == "__main__":
    main()
