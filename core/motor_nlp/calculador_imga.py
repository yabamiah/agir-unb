"""
Calculador do Índice de Maturidade da Governança Algorítmica (IMGA)
Aplica pesos oficiais (E1-E8) e normalização por volume de palavras.
"""

from typing import Any, Dict, List


class CalculadorIMGA:
    """
    Consolida as pontuações e gera o índice final (0-100) conforme a metodologia AGIR.
    """

    # Pesos extraídos da Tabela de Pesos Específicos do documento
    PESOS_METODOLOGIA = {
        "E1": 0.10,  # Estrutura de Governança e Liderança
        "E2": 0.10,  # Cultura de Integridade
        "E3": 0.15,  # Ambiente de Compliance
        "E4": 0.20,  # Due Diligence e Terceiros (Maior Peso)
        "E5": 0.10,  # Comunicação, Treinamento e Monitoramento
        "E6": 0.15,  # Gestão de Riscos e Controles Internos
        "E7": 0.10,  # Transparência, Accountability e Evidenciação
        "E8": 0.10,  # Efetividade e Maturidade do Programa
    }

    def __init__(self):
        self.pesos = self.PESOS_METODOLOGIA

    def calcular_imga_entidade(
        self, scores_por_eixo: Dict[str, List[int]], total_palavras: int
    ) -> Dict[str, Any]:
        """
        Calcula o IMGA Global com dados detalhados para auditoria.

        S_Ei = Soma dos pesos semânticos do eixo i
        I_Ei = S_Ei normalizado pela densidade de palavras (escala 0-100)
        IMGA_G = Soma ponderada de I_Ei
        """
        if total_palavras == 0:
            return {"imga_global": 0, "indices_eixos": {}, "auditoria": {}}

        indices_normalizados = {}
        auditoria_eixos = {}
        fator_normalizacao = total_palavras / 100

        # Passo 1: Calcula I_Ei para cada eixo com dados de auditoria
        for eixo_id in self.pesos.keys():
            scores = scores_por_eixo.get(eixo_id, [])
            soma_bruta = sum(scores)
            num_segmentos = len(scores)

            # Normalização DANI: (Soma / (Palavras/100)) * Fator de Escala
            densidade = soma_bruta / fator_normalizacao if fator_normalizacao > 0 else 0
            i_ei = min(densidade * 10, 100)  # Fator 10 para escala humana
            i_ei_arredondado = round(i_ei, 2)

            indices_normalizados[eixo_id] = i_ei_arredondado

            # Dados de auditoria para este eixo
            auditoria_eixos[eixo_id] = {
                "soma_bruta": soma_bruta,
                "num_segmentos_pontuados": num_segmentos,
                "fator_normalizacao": round(fator_normalizacao, 2),
                "densidade": round(densidade, 4),
                "indice_pre_cap": round(densidade * 10, 2),
                "indice_final": i_ei_arredondado,
                "peso_metodologia": self.pesos[eixo_id],
                "contribuicao_imga": round(i_ei_arredondado * self.pesos[eixo_id], 4),
            }

        # Passo 2: IMGA Global (Média Ponderada) * 10
        imga_global = (
            sum(indices_normalizados.get(e, 0) * self.pesos[e] for e in self.pesos) * 10
        )

        # Passo 3: Classificacao por Faixas
        faixa = "Incipiente"
        if imga_global > 75:
            faixa = "Avancada"
        elif imga_global > 50:
            faixa = "Intermediaria"
        elif imga_global > 25:
            faixa = "Basica"

        return {
            "imga_global": round(imga_global, 2),
            "faixa": faixa,
            "indices_eixos": indices_normalizados,
            "metadados": {"total_palavras": total_palavras},
            "auditoria": {
                "formula": "I_Ei = min((Soma_Bruta / (Total_Palavras/100)) * 10, 100)",
                "formula_imga": "IMGA = Σ(I_Ei × Peso_Ei)",
                "fator_normalizacao": round(fator_normalizacao, 2),
                "eixos": auditoria_eixos,
            },
        }
