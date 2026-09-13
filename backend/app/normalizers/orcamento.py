"""Normalizador Orçamento — projeção estimada a partir do histórico do DRE.

Não existe hoje um orçamento formal definido pela diretoria (confirmado em
busca real no Google Drive, 13/09/2026, por título e por conteúdo — nenhum
resultado de planilha de orçamento/budget/previsão interna da empresa; o
único "alvo" existente é uma meta única de faturamento bruto mensal em
`Planejamento_estrategico_Indicadores.xlsx`, sem quebra por linha de DRE, e
com um componente "SELIC 13,449047%" que é texto congelado numa célula, não
fórmula viva — não reaproveitável).

MÉTODO BASE (decisão do usuário, 13/09/2026): cada mês é estimado pela média
acumulada dos meses REAIS ANTERIORES da própria série (nunca usa o próprio
mês pra se estimar). Motivo, entre 3 opções apresentadas (média móvel 3
meses, média acumulada, tendência linear): o Lucro Líquido real oscila muito
mês a mês (jan-jul/2026 variou entre -R$298 mil e +R$122 mil, puxado por
reset trimestral de imposto e itens pontuais como rescisão) — média móvel
curta herdaria quase toda essa volatilidade, e regressão linear com só 7
pontos e padrão de dente de serra captaria ruído como tendência real. A
média acumulada é mais estável e mais defensável numa reunião de diretoria.

CONTA A CONTA (pedido do usuário, 13/09/2026): além das 5 linhas agregadas
do DRE (receita_bruta, despesas_pessoal, despesas_gerais, despesas_bancarias,
lucro_liquido), o mesmo método de projeção é aplicado conta por conta dentro
de `contas_detalhadas` — confirmado por investigação real (13/09/2026) que o
DRE já abre "Despesas Gerais" em ~37 contas individuais com valor mensal real
(ex: Combustível, Locação de veículos, Assessoria, Manutenção de veículos,
Manutenção de sistemas, Manutenção de máquina e equipamento, etc.), embora
nenhuma tenha coluna de previsto/orçado na fonte.

MANUTENÇÃO (pedido específico do usuário): não é uma conta só — são pelo
menos 3 contas reais no DRE (Manutenção de sistemas, de veículos, de máquina
e equipamento). Cada linha em `contas_detalhadas` cujo nome contém
"manutenção" (case-insensitive) é marcada com `categoria_manutencao: true`
no resultado, pra o frontend conseguir destacar/agrupar sem precisar
hardcodar nomes. O checklist técnico de manutenção preventiva da pasta Frota
(`Manutencao_preventiva.xlsx`) foi checado e NÃO tem valor em R$ (só datas de
troca de óleo por placa) — não é fonte pra custo, por isso usamos as contas
do próprio DRE.

NOVOS CONTRATOS (pedido do usuário, decisão de método 13/09/2026: somar ao
orçamento estimado, não só mostrar separado): contratos públicos (Licitação)
têm valor TOTAL e prazo em dias, não valor mensal — por isso o valor mensal é
uma APROXIMAÇÃO (valor_total ÷ validade_dias × 30, distribuição uniforme ao
longo do contrato). Pra cada mês projetado (com estimativa), soma-se o valor
mensal aproximado de todo contrato de `contratos_novos` que esteja ativo
naquele mês (data_inicio + validade_dias cobre o mês) SÓ no
`orcamento_estimado` da linha `receita_bruta` (nunca no realizado, que já é
fato). Os contratos considerados em cada mês ficam listados em
`contratos_novos_considerados` pra transparência (nunca embutir o ajuste sem
mostrar de onde veio).

MACRO (SELIC/IPCA): por decisão do usuário, NÃO incluído nesta versão — não
existe hoje vínculo comprovado entre indicador macro e os números reais da
ALS (as oscilações observadas têm causa específica identificada: reset
trimestral de imposto, rescisão pontual — não mercado). Usuário pediu pra
investigar separadamente se IPCA/reajuste sindical de salário e preço de
combustível têm vínculo real antes de considerar de novo.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

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


def _projetar(pontos: list[tuple[str, float]]) -> tuple[list[dict], dict | None]:
    """pontos: lista (period, valor) já ordenada por period. Retorna
    (serie, projecao_proximo_mes) usando média acumulada dos pontos
    ANTERIORES (nunca o próprio ponto)."""
    historico: list[float] = []
    serie = []
    for period, valor in pontos:
        if historico:
            estimado = sum(historico) / len(historico)
            variacao_valor = valor - estimado
            variacao_pct = round(100 * variacao_valor / estimado, 1) if estimado else None
        else:
            estimado = None
            variacao_valor = None
            variacao_pct = None
        serie.append({
            "period": period,
            "realizado": round(valor, 2),
            "orcamento_estimado": round(estimado, 2) if estimado is not None else None,
            "variacao_valor": round(variacao_valor, 2) if variacao_valor is not None else None,
            "variacao_pct": variacao_pct,
        })
        historico.append(valor)

    projecao = None
    if pontos:
        projecao = {
            "period": _proximo_period(pontos[-1][0]),
            "valor": round(sum(historico) / len(historico), 2),
        }
    return serie, projecao


def _mes_intervalo(period: str) -> tuple[date, date]:
    ano, mes = map(int, period.split("-"))
    inicio = date(ano, mes, 1)
    fim = date(ano + (1 if mes == 12 else 0), 1 if mes == 12 else mes + 1, 1) - timedelta(days=1)
    return inicio, fim


def _valor_mensal_contrato(contrato: dict) -> float:
    try:
        valor_total = float(contrato["valor_total"])
        dias = float(contrato["validade_dias"])
        if dias <= 0:
            return 0.0
        return valor_total / dias * 30
    except (KeyError, TypeError, ValueError):
        return 0.0


def _contrato_ativo_no_mes(contrato: dict, period: str) -> bool:
    try:
        di = datetime.strptime(contrato["data_inicio"], "%Y-%m-%d").date()
        dias = int(contrato["validade_dias"])
    except (KeyError, TypeError, ValueError):
        return False
    df = di + timedelta(days=dias)
    inicio_mes, fim_mes = _mes_intervalo(period)
    return di <= fim_mes and df >= inicio_mes


def _ajustar_receita_com_contratos(serie: list[dict], projecao_receita: dict | None, contratos_novos: list[dict]):
    """Soma, só no orcamento_estimado (nunca no realizado) da linha
    receita_bruta, o valor mensal aproximado dos contratos novos ativos em
    cada mês. Recalcula a variação depois do ajuste e registra quais
    contratos entraram em cada mês. `serie` é a lista top-level (com
    `period` em cada item e a sub-chave `receita_bruta`), mutada in place."""
    if not contratos_novos:
        return {}

    considerados_por_mes: dict[str, list[dict]] = {}

    def _contratos_valor(period: str):
        ativos = [c for c in contratos_novos if _contrato_ativo_no_mes(c, period)]
        ajuste = sum(_valor_mensal_contrato(c) for c in ativos)
        return ativos, ajuste

    for item in serie:
        period = item["period"]
        receita = item["receita_bruta"]
        if receita.get("orcamento_estimado") is None:
            continue
        ativos, ajuste = _contratos_valor(period)
        if not ativos or not ajuste:
            continue
        novo_estimado = round(receita["orcamento_estimado"] + ajuste, 2)
        receita["orcamento_estimado"] = novo_estimado
        receita["ajuste_contratos_novos"] = round(ajuste, 2)
        receita["variacao_valor"] = round(receita["realizado"] - novo_estimado, 2)
        receita["variacao_pct"] = round(100 * receita["variacao_valor"] / novo_estimado, 1) if novo_estimado else None
        considerados_por_mes[period] = [
            {
                "nome": c.get("nome"),
                "valor_total": c.get("valor_total"),
                "data_inicio": c.get("data_inicio"),
                "validade_dias": c.get("validade_dias"),
                "valor_mensal_aproximado": round(_valor_mensal_contrato(c), 2),
            }
            for c in ativos
        ]

    if projecao_receita:
        ativos = [c for c in contratos_novos if _contrato_ativo_no_mes(c, projecao_receita["period"])]
        ajuste = sum(_valor_mensal_contrato(c) for c in ativos)
        if ajuste:
            projecao_receita["valor"] = round(projecao_receita["valor"] + ajuste, 2)
            projecao_receita["ajuste_contratos_novos"] = round(ajuste, 2)
            considerados_por_mes[projecao_receita["period"]] = [
                {
                    "nome": c.get("nome"),
                    "valor_total": c.get("valor_total"),
                    "data_inicio": c.get("data_inicio"),
                    "validade_dias": c.get("validade_dias"),
                    "valor_mensal_aproximado": round(_valor_mensal_contrato(c), 2),
                }
                for c in ativos
            ]

    return considerados_por_mes


def normalize_orcamento(
    meses: list[dict],
    contas_detalhadas: list[dict] | None = None,
    contratos_novos: list[dict] | None = None,
) -> dict:
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

    # Ajuste de contratos novos — só entra na linha receita_bruta, só no estimado.
    receita_projecao = (
        {"period": projecao_proximo_mes["period"], "valor": projecao_proximo_mes["receita_bruta"]}
        if projecao_proximo_mes else None
    )
    contratos_considerados_por_mes = _ajustar_receita_com_contratos(serie, receita_projecao, contratos_novos or [])
    if projecao_proximo_mes and receita_projecao and "ajuste_contratos_novos" in receita_projecao:
        projecao_proximo_mes["receita_bruta"] = receita_projecao["valor"]
        projecao_proximo_mes["receita_bruta_ajuste_contratos_novos"] = receita_projecao["ajuste_contratos_novos"]

    # Detalhamento conta a conta (ex: Despesas Gerais aberta em ~37 contas).
    agrupado: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for linha in contas_detalhadas or []:
        categoria = (linha.get("categoria") or "despesas_gerais").strip()
        conta = (linha.get("conta_nome") or "").strip()
        period = (linha.get("period") or "").strip()
        valor = float(linha.get("valor") or 0)
        if conta and period:
            agrupado[categoria][conta][period] = agrupado[categoria][conta].get(period, 0.0) + valor

    detalhamento_contas: dict[str, dict] = {}
    for categoria, contas in agrupado.items():
        detalhamento_contas[categoria] = {}
        for conta, valores in contas.items():
            pontos = sorted(valores.items(), key=lambda kv: kv[0])
            serie_conta, projecao_conta = _projetar(pontos)
            detalhamento_contas[categoria][conta] = {
                "serie": serie_conta,
                "projecao_proximo_mes": projecao_conta,
                "categoria_manutencao": "manutenç" in conta.lower() or "manuten" in conta.lower(),
            }

    return {
        "serie_mensal": serie,
        "projecao_proximo_mes": projecao_proximo_mes,
        "detalhamento_contas": detalhamento_contas,
        "contratos_novos_considerados": contratos_considerados_por_mes,
        "metodo": "media_acumulada",
        "aviso": (
            "Orçamento ESTIMADO, não é meta oficial da diretoria — não existe hoje uma "
            "planilha de orçamento formal da empresa (confirmado em busca no Google "
            "Drive, 13/09/2026, por título e por conteúdo). Cada mês/conta é estimado "
            "pela média acumulada dos meses reais ANTERIORES (nunca usa o próprio mês "
            "pra se estimar). O primeiro mês da série nunca tem estimativa, por falta "
            "de histórico anterior. Quando há contrato novo ativo, seu valor mensal "
            "aproximado (valor total ÷ dias de validade × 30 — distribuição uniforme, "
            "não é dado exato) é somado só na receita ESTIMADA, nunca no realizado."
        ),
    }
