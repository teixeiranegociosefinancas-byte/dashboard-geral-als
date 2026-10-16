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



# ---------------------------------------------------------------------------
# MODELO DRE EDITÁVEL (Orçamento v2 — pedido do usuário, 11/10/2026)
#
# Estrutura "conta × mês" no formato do DRE mensal: RECEITAS de um lado,
# DESPESAS do outro, 12 meses do ano. Meses até `ultimo_mes_real` são fato
# (DRE); os seguintes são PROJETADOS e editáveis no site (os ajustes do
# usuário ficam numa coleção à parte, `orcamento_ajustes`, e o frontend aplica
# por cima do `base` daqui — este módulo só gera o valor base de cada célula).
#
# Identidade conferida contra o DRE V18_2 nos 7 meses reais (jan-jul/2026):
#   Lucro = Receita bruta − Impostos(16,33% da RB, regra do usuário p/ 2026)
#           − Pessoal − Gerais − Bancárias/tributárias − "contas novas"
#           + Outras receitas − Consórcio
# Por isso as "contas novas" (aluguel de caminhões, adiantamentos a
# fornecedores, movimentos com sócios...) entram no modelo como linhas — sem
# elas o lucro projetado ficaria muito acima do real.
#
# REGRAS DE PROJEÇÃO (valor base; tudo editável pelo usuário):
# - Linha de despesa: média de TODOS os meses reais da própria linha
#   (inclui meses zerados). Exceções: (a) `projetar=False` → 0 (movimentos
#   com sócios, conta 476 e empréstimos, por regra já decidida pelo usuário
#   no DRE; continua editável); (b) "13º salário": Nov e Dez = 50% da média
#   mensal de Salários cada (1ª e 2ª parcela) — SEM encargos sobre o 13º.
# - Clientes privados recorrentes (fonte: Roteiros de Serviços, OS
#   realizadas): meses com dado do Roteiro usam o valor do Roteiro; meses
#   sem dado usam a média dos últimos 6 meses com dado. Recorrente =
#   faturou em ≥ 8 dos 9 meses medidos E média ≥ R$3.000/mês, e não é órgão
#   público (contrato público é faturado fora do Roteiro).
# - "Demais receitas": real = Receita Bruta − soma dos clientes recorrentes;
#   projetado = média dos meses reais desse resíduo + valor mensal dos
#   contratos novos ativos no mês (mesma regra já validada em 13/09).
# - Impostos = alíquota única × receita bruta total do mês.
# - REGRA DE FECHAMENTO POSITIVO: se a receita base não cobre
#   Despesas × (1 + margem mínima) após impostos, uma linha derivada "Ajuste
#   de receita" completa a diferença: R* = D × (1+m) ÷ (1−t). É a receita
#   que a área comercial precisa buscar além da base recorrente.
# ---------------------------------------------------------------------------

MESES_ANO = [f"{m:02d}" for m in range(1, 13)]


def _slug(texto: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def _periodos_do_ano(primeiro_period: str) -> list[str]:
    ano = primeiro_period.split("-")[0]
    return [f"{ano}-{m}" for m in MESES_ANO]


def _linha_despesa(grupo_id: str, nome: str, valores_reais: dict[str, float], periodos: list[str],
                   reais: list[str], projetar: bool = True, motivo_nao_projetar: str | None = None,
                   extra: dict | None = None) -> dict:
    historico = [float(valores_reais.get(p, 0.0)) for p in reais]
    media = _media(historico)
    base: dict[str, float] = {}
    for p in periodos:
        if p in reais:
            base[p] = round(float(valores_reais.get(p, 0.0)), 2)
        else:
            base[p] = round(media, 2) if projetar else 0.0
    # orçamento estimado (média acumulada dos meses reais ANTERIORES) — só pros meses reais
    estimado: dict[str, float | None] = {}
    acumulado: list[float] = []
    for p in reais:
        estimado[p] = round(_media(acumulado), 2) if acumulado else None
        acumulado.append(float(valores_reais.get(p, 0.0)))
    linha = {
        "id": f"{grupo_id}.{_slug(nome)}",
        "nome": nome,
        "base": base,
        "estimado": estimado,
        "projetar": projetar,
        "categoria_manutencao": "manuten" in nome.lower(),
    }
    if not projetar and motivo_nao_projetar:
        linha["motivo_nao_projetar"] = motivo_nao_projetar
    if extra:
        linha.update(extra)
    return linha


def _classificar_clientes(clientes: list[dict], periodos_medidos: list[str]) -> tuple[list[dict], list[dict]]:
    """clientes: [{nome, publico(bool), valores:{period:valor}}] (valor do Roteiro, OS realizadas).
    Retorna (recorrentes, intermitentes)."""
    recorrentes, intermitentes = [], []
    n = len(periodos_medidos)
    for c in clientes:
        valores = [float(c["valores"].get(p, 0.0)) for p in periodos_medidos]
        ativos = sum(1 for v in valores if v > 0)
        media = _media(valores)
        desvio = (sum((v - media) ** 2 for v in valores) / n) ** 0.5 if n else 0.0
        cv = round(desvio / media, 2) if media else None
        info = {
            "nome": c["nome"],
            "meses_ativos": ativos,
            "meses_medidos": n,
            "media_mensal": round(media, 2),
            "minimo": round(min(valores), 2) if valores else 0,
            "maximo": round(max(valores), 2) if valores else 0,
            "variabilidade_cv": cv,
            "total": round(sum(valores), 2),
        }
        if not c.get("publico") and ativos >= 8 and media >= 3000:
            info["classe"] = "Recorrente"
            info["valores"] = {p: round(float(c["valores"].get(p, 0.0)), 2) for p in periodos_medidos}
            recorrentes.append(info)
        elif ativos >= 5 and media >= 3000:
            info["classe"] = "Intermitente"
            intermitentes.append(info)
    recorrentes.sort(key=lambda x: -x["total"])
    intermitentes.sort(key=lambda x: -x["total"])
    return recorrentes, intermitentes


def _build_modelo_dre(agrupado, contratos_novos: list[dict], inputs: dict) -> dict:
    ultimo_real = inputs["ultimo_mes_real"]
    rb_real: dict[str, float] = {k: float(v) for k, v in inputs["receita_bruta_real"].items()}
    reais = sorted(rb_real.keys())
    periodos = _periodos_do_ano(reais[0])
    projetados = [p for p in periodos if p > ultimo_real]
    aliquota = float(inputs.get("aliquota_imposto_pct", 16.33))
    margem = float(inputs.get("margem_minima_sobre_despesa_pct", 20.0))
    meta_mensal = inputs.get("meta_mensal")

    meses = [{"period": p, "status": "real" if p <= ultimo_real else "projetado"} for p in periodos]

    # ---------------- DESPESAS ----------------
    grupos_desp = []

    def _add_grupo(gid: str, nome: str, linhas: list[dict]):
        grupos_desp.append({"id": gid, "nome": nome, "linhas": linhas})

    # Pessoal e Gerais (vêm de contas_detalhadas, já agrupado por categoria)
    media_salarios = None
    for gid, categoria, nome in [("desp_pessoal", "Despesas com Pessoal", "Despesas com pessoal"),
                                 ("desp_gerais", "Despesas Gerais", "Despesas gerais")]:
        contas = agrupado.get(categoria, {})
        linhas = []
        for conta, valores in contas.items():
            linha = _linha_despesa(gid, conta, valores, periodos, reais)
            if conta.strip().lower() in ("salários", "salarios"):
                media_salarios = _media([float(valores.get(p, 0.0)) for p in reais])
            linhas.append(linha)
        _add_grupo(gid, nome, linhas)
    # 13º salário: 2 parcelas (Nov/Dez) = 50% da média de salários cada
    if media_salarios:
        for g in grupos_desp:
            for linha in g["linhas"]:
                if linha["nome"].strip().lower().startswith("13"):
                    ano = periodos[0].split("-")[0]
                    for p in periodos:
                        if p not in reais:
                            linha["base"][p] = round(media_salarios * 0.5, 2) if p in (f"{ano}-11", f"{ano}-12") else 0.0
                    linha["nota"] = ("Nov e Dez = 50% da média mensal de Salários cada (1ª e 2ª parcela). "
                                     "Não inclui encargos (INSS/FGTS) sobre o 13º.")

    # Extras (bancárias/tributárias, contas novas, consórcio) — chegam como linhas {categoria, conta_nome, period, valor, projetar, motivo}
    extras: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"valores": {}, "projetar": True, "motivo": None}))
    for r in inputs.get("contas_extra", []):
        cat = r["categoria"]
        reg = extras[cat][r["conta_nome"]]
        reg["valores"][r["period"]] = reg["valores"].get(r["period"], 0.0) + float(r["valor"])
        if r.get("projetar") is False:
            reg["projetar"] = False
            reg["motivo"] = r.get("motivo")
    for gid, categoria, nome in [("desp_bancarias", "Despesas Bancárias e Tributárias", "Despesas bancárias e tributárias"),
                                 ("desp_contas_novas", "Contas novas e movimentos com sócios", "Contas novas e movimentos com sócios")]:
        linhas = []
        for conta, reg in extras.get(categoria, {}).items():
            linhas.append(_linha_despesa(gid, conta, reg["valores"], periodos, reais,
                                         projetar=reg["projetar"], motivo_nao_projetar=reg["motivo"]))
        if linhas:
            _add_grupo(gid, nome, linhas)

    # ---------------- RECEITAS ----------------
    grupos_rec = []
    clientes = inputs.get("clientes", [])
    periodos_medidos = sorted({p for c in clientes for p in c["valores"].keys()})
    recorrentes, intermitentes = _classificar_clientes(clientes, periodos_medidos)

    linhas_cli = []
    soma_cli_real = {p: 0.0 for p in reais}
    for c in recorrentes:
        vals = c["valores"]
        ultimos6 = [vals[p] for p in periodos_medidos[-6:]]
        media6 = _media(ultimos6)
        base = {}
        origem = {}
        for p in periodos:
            if p in vals:
                base[p] = vals[p]
                origem[p] = "roteiro"
            else:
                base[p] = round(media6, 2)
                origem[p] = "regra"
        for p in reais:
            soma_cli_real[p] += vals.get(p, 0.0)
        linhas_cli.append({
            "id": f"rec_clientes.{_slug(c['nome'])}",
            "nome": c["nome"],
            "base": base,
            "origem": origem,
            "estimado": {},
            "recorrencia": {k: c[k] for k in ("classe", "meses_ativos", "meses_medidos", "media_mensal",
                                              "minimo", "maximo", "variabilidade_cv", "total")},
            "nota": "Fonte: Roteiros de Serviços 2026 (OS realizadas). Meses sem dado: média dos últimos 6 meses.",
        })
    grupos_rec.append({"id": "rec_clientes", "nome": "Clientes privados recorrentes", "linhas": linhas_cli})

    # Demais receitas
    demais_real = {p: round(rb_real[p] - soma_cli_real[p], 2) for p in reais}
    media_demais = _media([demais_real[p] for p in reais])
    base_demais = {}
    contratos_por_mes = {}
    for p in periodos:
        if p in reais:
            base_demais[p] = demais_real[p]
        else:
            ativos = [c for c in (contratos_novos or []) if _contrato_ativo_no_mes(c, p)]
            ajuste = sum(_valor_mensal_contrato(c) for c in ativos)
            base_demais[p] = round(media_demais + ajuste, 2)
            if ativos:
                contratos_por_mes[p] = [c.get("nome") for c in ativos]
    acum, est_demais = [], {}
    for p in reais:
        est_demais[p] = round(_media(acum), 2) if acum else None
        acum.append(demais_real[p])
    grupos_rec.append({"id": "rec_demais", "nome": "Demais receitas", "linhas": [{
        "id": "rec_demais.contratos_publicos_avulsos",
        "nome": "Contratos públicos, avulsos e clientes intermitentes",
        "base": base_demais,
        "estimado": est_demais,
        "contratos_novos_por_mes": contratos_por_mes,
        "nota": ("Real = Receita Bruta do DRE − clientes recorrentes acima. Projetado = média dos meses reais "
                 "+ valor mensal aproximado dos contratos novos ativos (valor total ÷ validade × 30)."),
    }]})

    outras = inputs.get("outras_receitas_real", {})
    if any(abs(float(v)) > 0 for v in outras.values()):
        base_out = {p: round(float(outras.get(p, 0.0)), 2) if p in reais else 0.0 for p in periodos}
        grupos_rec.append({"id": "rec_outras", "nome": "Outras receitas (financeiras / pontuais)", "tributavel": False, "linhas": [{
            "id": "rec_outras.outras_receitas", "nome": "Outras receitas", "base": base_out, "estimado": {},
            "projetar": False, "motivo_nao_projetar": "pontual / rendimento financeiro — não projetado",
        }]})

    # ---------------- RESUMO COM BASE (sem ajustes do usuário) ----------------
    def _soma_grupos(grupos, p, so_tributavel=None):
        return sum(l["base"][p] for g in grupos
                   if so_tributavel is None or g.get("tributavel", True) == so_tributavel
                   for l in g["linhas"])

    por_mes = []
    for p in periodos:
        rec_trib = _soma_grupos(grupos_rec, p, True)    # receita bruta (tributável)
        rec_nao_trib = _soma_grupos(grupos_rec, p, False)  # financeiras / pontuais (sem imposto)
        desp = _soma_grupos(grupos_desp, p)
        ajuste = 0.0
        if p in projetados:
            # Rb tal que Rb − t·Rb + outras − desp = margem·desp
            necessaria = (desp * (1 + margem / 100) - rec_nao_trib) / (1 - aliquota / 100)
            ajuste = max(0.0, necessaria - rec_trib)
        receita_bruta = rec_trib + ajuste
        impostos = receita_bruta * aliquota / 100
        por_mes.append({
            "period": p,
            "status": "real" if p <= ultimo_real else "projetado",
            "receita_base": round(rec_trib + rec_nao_trib, 2),
            "ajuste_receita": round(ajuste, 2),
            "receita_total": round(receita_bruta + rec_nao_trib, 2),
            "impostos": round(impostos, 2),
            "despesas": round(desp, 2),
            "resultado": round(receita_bruta + rec_nao_trib - impostos - desp, 2),
        })

    return {
        "ano": periodos[0].split("-")[0],
        "meses": meses,
        "ultimo_mes_real": ultimo_real,
        "parametros": {
            "aliquota_imposto_pct": aliquota,
            "margem_minima_sobre_despesa_pct": margem,
            "meta_mensal_comercial": meta_mensal,
        },
        "receitas": {"grupos": grupos_rec},
        "despesas": {"grupos": grupos_desp},
        "recorrencia": {
            "recorrentes": [{k: v for k, v in c.items() if k != "valores"} for c in recorrentes],
            "intermitentes": intermitentes,
            "criterio": ("Recorrente = faturou em ≥ 8 dos meses medidos e média ≥ R$3.000/mês, excluídos órgãos "
                         "públicos (faturados fora do Roteiro). Intermitente = ≥ 5 meses com média ≥ R$3.000."),
            "periodos_medidos": periodos_medidos,
            "fonte": inputs.get("fonte_clientes"),
        },
        "resumo_base": {
            "por_mes": por_mes,
            "receita_ano": round(sum(m["receita_total"] for m in por_mes), 2),
            "despesas_ano": round(sum(m["despesas"] for m in por_mes), 2),
            "impostos_ano": round(sum(m["impostos"] for m in por_mes), 2),
            "resultado_ano": round(sum(m["resultado"] for m in por_mes), 2),
            "ajuste_receita_total": round(sum(m["ajuste_receita"] for m in por_mes), 2),
        },
        "metodologia": [
            "Meses até o último fechado do DRE são fato; os seguintes são projeção editável.",
            "Despesa projetada = média dos meses reais da própria conta (13º salário: Nov/Dez = 50% da média de salários cada, sem encargos).",
            "Movimentos com sócios, conta 476 (impostos diversos) e empréstimos entram no realizado mas não são projetados (regra do DRE do usuário) — editáveis.",
            "Impostos = alíquota única sobre a receita bruta (16,33% — regra do DRE 2026); 'Outras receitas' (financeiras/pontuais) não pagam imposto.",
            "Receita projetada = clientes recorrentes (Roteiro) + demais receitas (média + contratos novos) + ajuste.",
            "Ajuste de receita: se a receita não cobre despesas × (1 + margem mínima) após impostos, a diferença é adicionada como meta de venda.",
        ],
    }


def normalize_orcamento(
    meses: list[dict],
    contas_detalhadas: list[dict] | None = None,
    contratos_novos: list[dict] | None = None,
    ponto_equilibrio_seguro: float | None = None,
    ponto_equilibrio_seguro_period: str | None = None,
    modelo_dre_inputs: dict | None = None,
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

    # Cenário "+20% sobre o ponto de equilíbrio SEGURO" — método redefinido
    # pelo usuário em 21/09/2026 depois de ver que a primeira versão (ponto de
    # equilíbrio pela MÉDIA de custo) dava margem líquida projetada de só
    # 4,5%, longe do "positivo e confortável" que ele queria. Pedido literal:
    # "eu só quero que o ponto de equilibro seja positivo... o maior mês de
    # despesa... você coloca o valor em torno disso". Ou seja: em vez da
    # média (Custo Fixo ÷ Margem de Contribuição%), o ponto de equilíbrio
    # agora usado aqui é o PIOR mês real já observado (maior despesa total
    # mensal do histórico, campo `maior_despesa_mensal_total` calculado em
    # normalizers/financeiro.py) — uma meta de receita 20% acima desse piso
    # garante lucro positivo em QUALQUER mês do histórico, não só na média,
    # porque nenhum mês real teve despesa maior que esse valor.
    cenario_20pct_sobre_ponto_equilibrio = None
    if ponto_equilibrio_seguro:
        receita_projetada = round(ponto_equilibrio_seguro * 1.20, 2)
        lucro_projetado = round(receita_projetada - ponto_equilibrio_seguro, 2)
        margem_liquida_projetada_pct = (
            round(100 * lucro_projetado / receita_projetada, 1) if receita_projetada else None
        )
        cenario_20pct_sobre_ponto_equilibrio = {
            "ponto_equilibrio_seguro_usado": round(ponto_equilibrio_seguro, 2),
            "ponto_equilibrio_seguro_baseado_no_mes": ponto_equilibrio_seguro_period,
            "receita_projetada": receita_projetada,
            "lucro_projetado": lucro_projetado,
            "margem_liquida_projetada_pct": margem_liquida_projetada_pct,
            "aviso": (
                "Ponto de equilíbrio 'seguro' pensado pra garantir lucro positivo mesmo no "
                "mês mais caro do ano (não é a média, é pensado pra cobrir o pior mês) — "
                f"referência: {ponto_equilibrio_seguro_period or 'não informada'}. Receita "
                "projetada = esse valor + 20%. Lucro projetado = receita projetada − o "
                "mesmo ponto de equilíbrio seguro (assume que a despesa não ultrapassa esse "
                "valor de referência)."
            ),
        }

    modelo_dre = None
    if modelo_dre_inputs:
        modelo_dre = _build_modelo_dre(agrupado, contratos_novos or [], modelo_dre_inputs)

    return {
        "serie_mensal": serie,
        "projecao_proximo_mes": projecao_proximo_mes,
        "modelo_dre": modelo_dre,
        "detalhamento_contas": detalhamento_contas,
        "contratos_novos_considerados": contratos_considerados_por_mes,
        "cenario_20pct_sobre_ponto_equilibrio": cenario_20pct_sobre_ponto_equilibrio,
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
