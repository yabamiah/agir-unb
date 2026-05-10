"""
Módulo de Pontuação de Maturidade - Projeto AGIR
Aplica pesos semânticos (1-3) e boosters operacionais (+1) com cap de 5.
"""

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ResultadoMaturidade:
    score_final: int
    eixo_id: str
    evidencias: List[str]
    detalhe_boosters: Dict[str, bool]


class PontuadorMaturidadeDANI:
    """
    Avalia a qualidade da evidência baseada em regras de reforço e pesos de sinais.
    """

    def __init__(self):
        # Boosters conforme Anexo 2 do documento
        self.boosters_config = {
            "B1_ACAO": [
                "implementou",
                "realiza",
                "executa",
                "monitora",
                "apura",
                "investiga",
                "audita",
            ],
            "B2_PERIODICIDADE": [
                "anualmente",
                "mensalmente",
                "trimestralmente",
                "periodicamente",
                "contínua",
            ],
            "B3_RESPONSAVEL": [
                "conselho",
                "diretoria",
                "compliance officer",
                "auditoria",
                "comitê",
            ],
            "B4_ARTEFATO": [
                "política",
                "manual",
                "regimento",
                "fluxo",
                "plano",
                "relatório",
            ],
        }
        self.cap = 5

    def calcular_score_eixo(
        self, texto: str, eixo_id: str, sinais_eixo: Dict[str, List[str]]
    ) -> ResultadoMaturidade:
        """
        Calcula a pontuação de maturidade para um eixo específico em um trecho.
        """
        texto_lower = texto.lower()
        score_base = 0
        evidencias_encontradas = []

        # 1. Determina o peso base do sinal mais forte encontrado
        # Subsignals (Peso 3)
        for s in sinais_eixo.get("subsignals", []):
            if re.search(rf"\b{s}\b", texto_lower):
                score_base = max(score_base, 3)
                evidencias_encontradas.append(s)

        # Expressions (Peso 2)
        if score_base < 2:
            for e in sinais_eixo.get("expressoes", []):
                if e in texto_lower:
                    score_base = max(score_base, 2)
                    evidencias_encontradas.append(e)

        # Terms (Peso 1)
        if score_base < 1:
            for t in sinais_eixo.get("termos", []):
                if re.search(rf"\b{t}\b", texto_lower):
                    score_base = max(score_base, 1)
                    evidencias_encontradas.append(t)

        if score_base == 0:
            return ResultadoMaturidade(0, eixo_id, [], {})

        # 2. Aplica Boosters (+1 cada)
        boost_total = 0
        detalhe = {}
        for b_id, padrões in self.boosters_config.items():
            encontrou = any(re.search(rf"\b{p}", texto_lower) for p in padrões)
            if encontrou:
                boost_total += 1
            detalhe[b_id] = encontrou

        # 3. Score Final com Cap
        score_final = min(score_base + boost_total, self.cap)

        return ResultadoMaturidade(
            score_final=score_final,
            eixo_id=eixo_id,
            evidencias=list(set(evidencias_encontradas)),
            detalhe_boosters=detalhe,
        )
