from colorama import Fore, Style

from dani.models import Dani
from lara.models import Lara

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
                {Fore.BLUE}lara, l{Style.RESET_ALL}           Ativa o bot Lara que irá raspar as informações públicas do GDF acerca dos planos de integridade
                {Fore.BLUE}dani, d{Style.RESET_ALL}           Ativa o bot Dani que irá gerar o dashboard com a partir dos parâmetros de qualidade
                {Fore.BLUE}datadisplay, dd{Style.RESET_ALL}   Exibir dados cdo Programa Integridade em planilha
                {Fore.BLUE}help, h{Style.RESET_ALL}           Exibe uma lista de comandos
                {Fore.BLUE}quit, q{Style.RESET_ALL}           Sair do AGIR

            OPÇÕES GLOBAIS:
                help, h          Exibe comandos
                version, v       Imprime a versão
          """
    
    def __init__(self) -> None:
        print("Bem-vindo ao sistema AGIR!")
        print(self.message)
        self.args = input("Digite aqui: ") 
        self.execute_commands()

    def execute_commands(self) -> None:
        commands = {
            'lara': self.trigger_lara, 'l': self.trigger_lara,
            'dani': self.trigger_dani, 'd': self.trigger_dani,
            'datadisplay': self.display_data, 'dd': self.display_data,
            'help': self.__help__, 'h': self.__help__,
            'quit': self.__quit__, 'q': self.__quit__,
            'version': self.__version__, 'v':self.__version__
        }

        if self.args in commands:
            commands[self.args]()
        else:
            print("Comando não reconhecido.")
            commands['help']()


    def __help__(self) -> None:
        print(self.message)

    def __quit__(self) -> None:
        exit(0)
        
    def __version__(self) -> None:
        print(f"{Fore.BLUE}0.0.1{Style.RESET_ALL}")

    def trigger_lara(self) -> None:
        print("Calling to Lara")
        Lara()        

        print("Lara terminou o seu trabalho..")
        sn = input("Deseja continuar com a Dani [S/N]? ")
        if sn == 'S':
            self.trigger_dani()
        else:
            print("Até mais..")            
            exit(0)

    def trigger_dani(self) -> None:
        print("Calling to Dani")
        Dani()


    def display_data(self) -> None:
        print("Display data")
        self.trigger_dani('display_programa')