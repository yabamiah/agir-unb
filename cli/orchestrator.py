import asyncio
import os
import time
from datetime import datetime

from loguru import logger

from core.models.lara_i import LaraI, ConfiguracaoLara
from core.models.dani import Dani

TRIGGER_DIR = "/app/data/triggers"
DANI_INPUT_DIR = "/app/data/dani/docs/input"

TRIGGER_LARA = os.path.join(TRIGGER_DIR, "run_lara.trigger")
TRIGGER_DANI = os.path.join(TRIGGER_DIR, "run_dani.trigger")
RUNNING_LARA = os.path.join(TRIGGER_DIR, "running_lara.trigger")
RUNNING_DANI = os.path.join(TRIGGER_DIR, "running_dani.trigger")
COMPLETED_LARA = os.path.join(TRIGGER_DIR, "completed_lara.trigger")
COMPLETED_DANI = os.path.join(TRIGGER_DIR, "completed_dani.trigger")


def log_status(message):
    """Função de log com timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{timestamp}] {message}")


async def run_lara():
    """Executa o processo completo do LARA-I."""
    log_status("Processo LARA-I iniciado.")
    config = ConfiguracaoLara()
    lara = LaraI(config)
    try:
        await lara.processar_orgaos()
        await lara.upload_pdfs_s3()
        log_status("✅ Processo LARA-I concluído com sucesso.")
    except Exception as e:
        log_status(f"❌ Erro no processo LARA-I: {e}")
    finally:
        # Remove o arquivo de running quando termina (mesmo em caso de erro)
        if os.path.exists(RUNNING_LARA):
            os.remove(RUNNING_LARA)
        # Cria arquivo de completed para o dashboard detectar e atualizar
        with open(COMPLETED_LARA, 'w') as f:
            f.write(f"completed_at_{int(time.time())}")


def run_dani():
    """Executa o processo completo do DANI."""
    log_status("Processo DANI iniciado.")
    try:
        dani = Dani()
        dani.run()
        log_status("✅ Processo DANI concluído com sucesso.")
    except Exception as e:
        log_status(f"❌ Erro no processo DANI: {e}")
    finally:
        # Remove o arquivo de running quando termina (mesmo em caso de erro)
        if os.path.exists(RUNNING_DANI):
            os.remove(RUNNING_DANI)
        # Cria arquivo de completed para o dashboard detectar e atualizar
        with open(COMPLETED_DANI, 'w') as f:
            f.write(f"completed_at_{int(time.time())}")


async def main():
    """Loop principal que verifica os gatilhos."""
    log_status("Orquestrador iniciado. Aguardando gatilhos...")
    os.makedirs(TRIGGER_DIR, exist_ok=True)

    while True:
        if os.path.exists(TRIGGER_LARA):
            log_status("Gatilho para LARA encontrado. Removendo gatilho e iniciando processo...")
            os.remove(TRIGGER_LARA)
            
            # Cria arquivo de "running" para o dashboard detectar
            with open(RUNNING_LARA, 'w') as f:
                f.write(f"started_at_{int(time.time())}")

            if os.path.exists(DANI_INPUT_DIR) and os.listdir(DANI_INPUT_DIR):
                log_status("Diretório de entrada do DANI já contém arquivos. Pulando execução do LARA-I.")
                # Remove o arquivo de running já que não vai executar
                if os.path.exists(RUNNING_LARA):
                    os.remove(RUNNING_LARA)
                # Cria arquivo de completed mesmo quando pula a execução
                with open(COMPLETED_LARA, 'w') as f:
                    f.write(f"completed_at_{int(time.time())}")
            else:
                log_status("Diretório de entrada do DANI está vazio. Iniciando processo LARA-I...")
                await run_lara()
            
            log_status("Aguardando próximo gatilho...")

        if os.path.exists(TRIGGER_DANI):
            log_status("Gatilho para DANI encontrado. Removendo gatilho e iniciando processo...")
            os.remove(TRIGGER_DANI)
            
            # Cria arquivo de "running" para o dashboard detectar
            with open(RUNNING_DANI, 'w') as f:
                f.write(f"started_at_{int(time.time())}")
            
            run_dani()
            log_status("Aguardando próximo gatilho...")

        time.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_status("Orquestrador finalizado.")