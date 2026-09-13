"""Normalizador Orçamento — projeção estimada a partir do histórico do DRE.

Não existe hoje um orçamento formal definido pela diretoria (confirmado em
busca real no Google Drive, 13/09/2026, por título e por conteúdo — nenhum
resultado de planilha de orçamento/budget/previsão interna da empresa; o
único "alvo" existente é uma meta única de faturamento bruto mensal em
`Planejamento_estrategico_Indicadores.xlsx`, sem quebra por linha de DRE).

Por decisão explícita do usuário (13/09/2026), este normalizador NÃO inventa
uma meta oficial — calcula uma "projeção estimada" mês a mês a partir da
média acumulada dos meses REAIS ANTERIORES do próprio DRE (nunca usa o
próprio mês pra estimar ele mesmo, senão deixaria de ser uma previsão).
Método escolhido pelo usuário entre 3 opções apresentadas (média móvel 3
meses, média acumulada, tendência linear): média acumulada de TODOS os meses
reais anteriores. Motivo: o Lucro Líquido real oscila muito mês a mês
(jan-jul/2026 variou entre -R$298 mil e +R$122 mil, puxado por reset
trimestral de imposto e itens pontuais como rescisão) — uma média móvel
curta herdaria quase toda essa volatilidade e uma regressão linear, com só 7
meses de dado e um padrão de dente de serra por causa do trimestre fiscal,
captaria ruído como se fosse tendência real. A média acumulada é mais
estável e mais fácil de defender numa reunião de diretoria.

Entrada esperada (`meses`): mesma estrutura de entrada do normalize_financeiro
— lista de dicts, um por mês real do DRE, com period ("AAAA-MM") e as linhas
abaixo. Deixar sempre explícito na tela que o resultado é estimativa, não
meta aprovada pela diretoria.
"""

LINHAS_PROJETADAS = [
    "receita_bruta",
    "despesas_pessoal",
    "despesas_gerais",
    "despesas_bancarias",
    "lucro_liquido",
]


def _proximo_period(period: str) -> str:
    ano, mes = period.split("-")
    ano, mes = int(ano), int(mes) + 1
    if mes > 12:
        mes = 1
        ano += 1
    return f"{ano:04d}-{mes:02d}"


def normalize_orcamento(meses: list[dict]) -> dict:
    meses_ordenados = sorted(meses, key=lambda x: x.get("period", ""))

    historico: dict[str, list[float]] = {linha: [] for linha in LINHAS_PROJETADAS}
    serie = []

    for m in meses_ordenados:
        linha_resultado = {"period": m.get("period")}
        for linha in LINHAS_PROJETADAS:
            realizado = float(m.get(linha) or 0)
            anteriores = historico[linha]
            if anteriores:
                estimado = sum(anteriores) / len(anteriores)
                variacao_valor = realizado - estimado
                variacao_pct = round(100 * variacao_valor / estimado, 1) if estimado else None
            else:
                estimado = None
                variacao_valor = None
                variacao_pct = None
            linha_resultado[linha] = {
                "realizado": round(realizado, 2),
                "orcamento_estimado": round(estimado, 2) if estimado is not None else None,
                "variacao_valor": round(variacao_valor, 2) if variacao_valor is not None else None,
                "variacao_pct": variacao_pct,
            }
            anteriores.append(realizado)
        serie.append(linha_resultado)

    projecao_proximo_mes = None
    if meses_ordenados:
        projecao_proximo_mes = {
            "period": _proximo_period(meses_ordenados[-1].get("period")),
            **{
                linha: round(sum(historico[linha]) / len(historico[linha]), 2)
                for linha in LINHAS_PROJETADAS
            },
        }

    return {
        "serie_mensal": serie,
        "projecao_proximo_mes": projecao_proximo_mes,
        "metodo": "media_acumulada",
        "aviso": (
            "Orçamento ESTIMADO, não é meta oficial da diretoria — não existe hoje uma "
            "planilha de orçamento formal da empresa (confirmado em busca no Google "
            "Drive, 13/09/2026, por título e por conteúdo). Cada mês é estimado pela "
            "média acumulada dos meses reais ANTERIORES do próprio DRE (nunca usa o "
            "mês atual pra estimar ele mesmo). O primeiro mês da série nunca tem "
            "estimativa, por falta de histórico anterior."
        ),
    }
