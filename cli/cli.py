import asyncio

from colorama import Fore, Style

from core.models.dani import Dani
from core.models.lara_i import ConfiguracaoLara, LaraI


class Cli:
    args = ""
    message = f"""
            NOME:
                {Fore.BLUE}AGIR - Automação para uma Governança Inteligente e Responsável{Style.RESET_ALL}

            USO:
                agir [comando]

            VERSÃO:
                {Fore.BLUE}0.0.1{Style.RESET_ALL}

            COMANDOS:
                {Fore.BLUE}lara, l{Style.RESET_ALL}           Ativa o bot LARA-I para coletar documentos da web.
                {Fore.BLUE}dani, d{Style.RESET_ALL}           Ativa o bot DANI para analisar os documentos coletados.
                {Fore.BLUE}help, h{Style.RESET_ALL}           Exibe esta lista de comandos.
                {Fore.BLUE}quit, q{Style.RESET_ALL}           Sair do AGIR.
          """

    def __init__(self) -> None:
        print("Bem-vindo ao sistema AGIR!")
        print(self.message)

    async def execute_commands(self) -> None:
        while True:
            self.args = input("Digite um comando: ").strip().lower()

            commands = {
                "lara": self.trigger_lara,
                "l": self.trigger_lara,
                "dani": self.trigger_dani,
                "d": self.trigger_dani,
                "help": self.__help__,
                "h": self.__help__,
                "quit": self.__quit__,
                "q": self.__quit__,
            }

            command_func = commands.get(self.args)

            if command_func:
                if asyncio.iscoroutinefunction(command_func):
                    await command_func()
                else:
                    command_func()
            else:
                print("Comando não reconhecido.")
                self.__help__()

    async def __help__(self) -> None:
        print(self.message)

    def __quit__(self) -> None:
        print("Até mais!")
        exit(0)

    async def trigger_lara(self) -> None:
        print(f"{Fore.CYAN}--- Iniciando LARA-I ---{Style.RESET_ALL}")
        config = ConfiguracaoLara()
        lara = LaraI(config)

        try:
            await lara.processar_orgaos()
            await lara.upload_pdfs_s3()
            print(
                f"{Fore.GREEN}--- LARA-I concluiu a coleta de documentos. ---{Style.RESET_ALL}"
            )

            sn = (
                input("Deseja continuar e executar a análise com o DANI [S/N]? ")
                .strip()
                .lower()
            )
            if sn == "s":
                self.trigger_dani()
            else:
                self.__quit__()
        except Exception as e:
            print(
                f"{Fore.RED}Ocorreu um erro fatal durante a execução do LARA-I: {e}{Style.RESET_ALL}"
            )

    def trigger_dani(self) -> None:
        print(f"{Fore.CYAN}--- Iniciando DANI ---{Style.RESET_ALL}")
        try:
            dani = Dani()
            dani.run()
            print(
                f"{Fore.GREEN}--- DANI concluiu a análise. Verifique os relatórios no diretório 'data'. ---{Style.RESET_ALL}"
            )
        except Exception as e:
            print(
                f"{Fore.RED}Ocorreu um erro fatal durante a execução do DANI: {e}{Style.RESET_ALL}"
            )


async def main():
    cli = Cli()
    await cli.execute_commands()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário. Saindo...")
