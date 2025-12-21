"""
Classificador de Texto por Eixos Analíticos - Módulo DANI
Substitui embeddings por regras explícitas para garantir explicabilidade e auditoria.
"""

import re
from typing import Dict, List, Optional, Any

class ClassificadorEixos:
    """
    Classificador que mapeia textos a eixos analíticos usando dicionários semânticos.
    """

    def __init__(self, threshold: int = 1):
        """
        Inicializa o classificador baseado em regras.

        Args:
            threshold: Pontuação mínima total para considerar um texto classificado em um eixo.
        """
        self.threshold = threshold
        self.dicionario_eixos = {}
        self.eixos_nomes = {}

    def carregar_dicionario(self, dicionario: List[Dict]) -> None:
        """
        Carrega o dicionário estruturado seguindo a taxonomia Nível 2 do documento.

        Args:
            dicionario: Lista de dicionários contendo axis_id, nome e categorias com sinais.
        """
        print("Processando dicionário analítico...")

        for item in dicionario:
            eixo_id = item.get('axis_id')
            self.eixos_nomes[eixo_id] = item.get('axis_name', eixo_id)

            # Organiza sinais por peso conforme a metodologia
            sinais = {
                "termos": [],      # Peso 1
                "expressoes": [],   # Peso 2
                "subsignals": []    # Peso 3
            }

            for cat in item.get('categories', []):
                sinais["termos"].extend(cat.get('terms', []))
                sinais["expressoes"].extend(cat.get('expressions', []))
                sinais["subsignals"].extend(cat.get('subsignals', []))

            self.dicionario_eixos[eixo_id] = sinais
            print(f"✓ {eixo_id} ({self.eixos_nomes[eixo_id]}) carregado.")

    def classificar_texto(self, texto: str) -> Dict[str, Any]:
        """
        Classifica um texto identificando em quais eixos ele possui sinais.
        """
        texto_lower = texto.lower()
        eixos_detectados = {}

        for eixo_id, sinais in self.dicionario_eixos.items():
            evidencias = []

            # Busca simples de termos e expressões para classificação inicial
            for termo in sinais["termos"] + sinais["expressoes"] + sinais["subsignals"]:
                if re.search(rf"\b{termo}\b", texto_lower):
                    evidencias.append(termo)

            if evidencias:
                eixos_detectados[eixo_id] = evidencias

        return eixos_detectados

    def obter_info_eixo(self, eixo_id: str) -> Optional[str]:
        return self.eixos_nomes.get(eixo_id)