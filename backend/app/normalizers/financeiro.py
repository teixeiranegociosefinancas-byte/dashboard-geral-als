"""Normalizador Financeiro — DRE mensal.

Fonte validada: DRE_FINANCEIRO_MENSAL_2026_ALS_*.xlsx, uma aba por mês
("DRE MM.AAAA"), estrutura de linhas fixa (documentada em memória/projeto):
linha 6 Receita Bruta, linha 9 Impostos, linha 10/11 Receita Líquida,
linha 15 Despesas c/ Pessoal, linha 33 Despesas Gerais, linha 91 Despesas
Bancárias/Tributárias, linha 99 Outras Receitas, linha 154 Contas Novas,
linha 108 Lucro Líquido (valor já apurado na fonte, não recalculado aqui —
uma tentativa anterior de recalcular via soma simples divergiu em até
R$228 mil em alguns meses comparado ao valor oficial da linha 108).

ROI e EBITDA adicionados em 13/09/2026 (pedido do usuário, indicadores pra
due diligence de fundo de investimento). Definições confirmadas com o
usuário via pergunta direta, deliberadamente SEM depender do Balanço
Patrimonial/Balancete (fonte que o usuário sinalizou não ser confiável
nesta rodada — "balanço está meio que inventado pela contabilidade"):

- ROI = Lucro Líquido ÷ Receita Líquida (margem líquida sobre receita já
  líquida de impostos — diferente de `margem_liquida_pct` abaixo, que usa
  Receita BRUTA como base e já existia antes desta mudança).
- EBITDA = Lucro ANTES do Imposto de Renda e de Movimentos com Sócios
  (linha 178 da mesma planilha DRE, seção "RESULTADO — VISÃO EM CAMADAS")
  + Depreciação (linha 88) + Juros (linhas 84+85 — bancários e de mora).
  Usa só campos dessa MESMA planilha DRE interna já validada — nenhum dado
  do Balanço/Balancete entra aqui.

Margem de contribuição / ponto de equilíbrio — adicionados em 18/09/2026
(pedido explícito do usuário, "o que eu pedi foi margem de contribuição
também"). Classificação de custo fixo x variável, decidida conta a conta
(não é heurística genérica — cada conta foi julgada pela natureza real da
despesa, ver `DESPESAS_GERAIS_VARIAVEIS` abaixo):
- 100% FIXO: Despesas com Pessoal, Despesas Bancárias/Tributárias.
- 100% VARIÁVEL: Impostos (proporcional à Receita Bruta faturada), Contas
  Novas (confirmado pelo usuário 2026-09-18 — "tratar como custo variável").
- Despesas Gerais: dividida conta a conta entre as 38 contas do razão
  (mesma fonte usada no Orçamento, `contas_detalhadas`) — combustível,
  locação/manutenção de veículos, mão de obra PJ de campo, insumo químico,
  descarte, pedágio etc. escalam com o volume de serviço (variável);
  aluguel, assessoria, sistemas, seguros, utilidades etc. são estrutura
  administrativa que não muda com o volume (fixo).
Achado real (Jan-Jul/2026, acumulado): custo variável de Despesas Gerais =
R$1.278.408,84 (76,06% do total de R$1.680.758,23), o resto é fixo.
Margem de contribuição = (Receita Bruta − Custo Variável) ÷ Receita Bruta.
Ponto de equilíbrio = Custo Fixo ÷ Margem de Contribuição (%).

IMPORTANTE: o cálculo de margem de contribuição/ponto de equilíbrio só é
feito de forma ACUMULADA (soma de todos os meses recebidos), nunca mês a
mês — achado real: mês a mês o resultado é instável (ex: março/2026 dá
margem de contribuição NEGATIVA por causa de um pico atípico de Contas
Novas de R$333.704,41 naquele mês isolado), o que produziria um "ponto de
equilíbrio" sem sentido (negativo). Acumulado, o resultado é estável — a
mesma lógica já validada pra projeção de Orçamento por média acumulada.
"""

# Ver docstring do módulo — classificação decidida conta a conta em
# 2026-09-18, a partir das 38 contas reais de Despesas Gerais do razão.
DESPESAS_GERAIS_VARIAVEIS = {
    "Combustivel",                                              # combustível de frota — escala com km/OS rodada
    "Locação de veiculos",                                      # reforço de frota por demanda de volume
    "Manutenção de veículos",                                   # desgaste por uso operacional
    "Prestação de serviço PJ",                                  # mão de obra de campo terceirizada (PJ)
    "Tickets de Descartes",                                     # descarte pago por volume de resíduo coletado
    "Locação de caminhão de fossa /hidrojato",                  # caminhão extra alugado por pico de demanda
    "Pedágio",                                                  # mais viagens = mais pedágio
    "Frete e carreto",                                          # transporte por demanda
    "Material Químico",                                         # insumo consumido por serviço executado
    "Locação de equipamentos (container)",                      # equipamento alugado por contrato/obra
    "Manutenção de máquina e equipamento",                      # desgaste por uso operacional
    "multas de trânsito",                                       # mais rodagem = mais risco de multa
    "Locação de banheiros quimicos",                            # unidade alugada por contrato
    "Controle e tratamento de efluentes de qualquer natureza",  # tratamento proporcional ao volume coletado
    "Analise de agua",                                          # análise por serviço executado
    "Pneus",                                                    # desgaste por km rodado
}

# Fallback usado quando o detalhamento conta a conta de Despesas Gerais não é
# enviado nesta chamada: percentual variável real, apurado uma vez contra as
# 38 contas do razão (Jan-Jul/2026) — ver docstring do módulo.
DESPESAS_GERAIS_PCT_VARIAVEL_FALLBACK = 1_278_408.84 / 1_680_758.23


def normalize_financeiro(
    meses: list[dict],
    recebimento: dict | None = None,
    despesas_gerais_contas: list[dict] | None = None,
) -> dict:
    """`meses`: lista de dicts, um por mês, com as chaves:
    period ("AAAA-MM"), receita_bruta, impostos, receita_liquida,
    despesas_pessoal, despesas_gerais, despesas_bancarias, outras_receitas,
    contas_novas, lucro_liquido, e opcionalmente lucro_antes_ir_e_socios,
    depreciacao, juros (pra EBITDA — se ausentes, EBITDA fica None nesse mês).

    `recebimento`: dict opcional com indicadores de prazo/recebimento,
    calculados fora da série mensal do DRE (fonte: exportações de Contas a
    Receber / Contas a Pagar do ERP). Chaves esperadas: pmr_dias, pmp_dias,
    inadimplencia_pct, e opcionalmente periodo/aviso/detalhes — repassado
    quase verbatim pro payload final, só some se vier None.

    `despesas_gerais_contas`: lista opcional de dicts {conta_nome, valor}
    (mesma granularidade usada no Orçamento, `contas_detalhadas`, já
    acumulada no período) — usada pra dividir Despesas Gerais em fixo x
    variável conta a conta (ver DESPESAS_GERAIS_VARIAVEIS). Se não vier,
    usa o fallback DESPESAS_GERAIS_PCT_VARIAVEL_FALLBACK sobre o total de
    despesas_gerais acumulado.
    """
    serie = []
    receita_acumulada = 0.0
    receita_liquida_acumulada = 0.0
    lucro_acumulado = 0.0
    ebitda_acumulado = 0.0
    tem_ebitda = False
    impostos_acumulado = 0.0
    despesas_pessoal_acumulado = 0.0
    despesas_gerais_acumulado = 0.0
    despesas_bancarias_acumulado = 0.0
    contas_novas_acumulado = 0.0
    maior_despesa_mensal_total = None
    maior_despesa_mensal_period = None

    for m in sorted(meses, key=lambda x: x.get("period", "")):
        receita = float(m.get("receita_bruta") or 0)
        receita_liquida = float(m.get("receita_liquida") or 0)
        lucro = float(m.get("lucro_liquido") or 0)
        margem = round(100 * lucro / receita, 1) if receita else None
        roi_pct = round(100 * lucro / receita_liquida, 1) if receita_liquida else None

        lucro_antes_ir_e_socios = m.get("lucro_antes_ir_e_socios")
        ebitda = None
        ebitda_pct_receita_liquida = None
        if lucro_antes_ir_e_socios is not None:
            depreciacao = float(m.get("depreciacao") or 0)
            juros = float(m.get("juros") or 0)
            ebitda = round(float(lucro_antes_ir_e_socios) + depreciacao + juros, 2)
            ebitda_pct_receita_liquida = round(100 * ebitda / receita_liquida, 1) if receita_liquida else None
            ebitda_acumulado += ebitda
            tem_ebitda = True

        serie.append({
            "period": m.get("period"),
            "receita_bruta": round(receita, 2),
            "impostos": round(float(m.get("impostos") or 0), 2),
            "receita_liquida": round(receita_liquida, 2),
            "despesas_pessoal": round(float(m.get("despesas_pessoal") or 0), 2),
            "despesas_gerais": round(float(m.get("despesas_gerais") or 0), 2),
            "despesas_bancarias": round(float(m.get("despesas_bancarias") or 0), 2),
            "outras_receitas": round(float(m.get("outras_receitas") or 0), 2),
            "contas_novas": round(float(m.get("contas_novas") or 0), 2),
            "lucro_liquido": round(lucro, 2),
            "margem_liquida_pct": margem,
            "roi_pct": roi_pct,
            "ebitda": ebitda,
            "ebitda_pct_receita_liquida": ebitda_pct_receita_liquida,
        })
        receita_acumulada += receita
        receita_liquida_acumulada += receita_liquida
        lucro_acumulado += lucro
        impostos_acumulado += float(m.get("impostos") or 0)
        despesas_pessoal_acumulado += float(m.get("despesas_pessoal") or 0)
        despesas_gerais_acumulado += float(m.get("despesas_gerais") or 0)
        despesas_bancarias_acumulado += float(m.get("despesas_bancarias") or 0)
        contas_novas_acumulado += float(m.get("contas_novas") or 0)

        # Maior mês de despesa TOTAL real (pessoal+gerais+bancárias+impostos+
        # contas novas) — usado como piso "seguro" pro cenário de meta do
        # Orçamento (ver normalizers/orcamento.py): diferente do ponto de
        # equilíbrio médio (que usa custo MÉDIO), este é o pior mês REAL já
        # observado, então uma meta de receita acima dele garante lucro
        # positivo em QUALQUER mês do histórico, não só na média.
        despesa_total_mes = (
            float(m.get("despesas_pessoal") or 0)
            + float(m.get("despesas_gerais") or 0)
            + float(m.get("despesas_bancarias") or 0)
            + float(m.get("impostos") or 0)
            + float(m.get("contas_novas") or 0)
        )
        if maior_despesa_mensal_total is None or despesa_total_mes > maior_despesa_mensal_total:
            maior_despesa_mensal_total = despesa_total_mes
            maior_despesa_mensal_period = m.get("period")

    # Margem de contribuição / ponto de equilíbrio — só acumulado, nunca mês a
    # mês (ver docstring do módulo pro motivo real: instabilidade em meses
    # isolados com pico de Contas Novas).
    if despesas_gerais_contas:
        dg_variavel_acumulado = sum(
            float(c.get("valor") or 0) for c in despesas_gerais_contas
            if c.get("conta_nome") in DESPESAS_GERAIS_VARIAVEIS
        )
    else:
        dg_variavel_acumulado = despesas_gerais_acumulado * DESPESAS_GERAIS_PCT_VARIAVEL_FALLBACK
    dg_fixo_acumulado = despesas_gerais_acumulado - dg_variavel_acumulado

    custo_variavel_acumulado = impostos_acumulado + contas_novas_acumulado + dg_variavel_acumulado
    custo_fixo_acumulado = despesas_pessoal_acumulado + despesas_bancarias_acumulado + dg_fixo_acumulado

    margem_contribuicao_valor_acumulada = receita_acumulada - custo_variavel_acumulado
    margem_contribuicao_pct = (
        round(100 * margem_contribuicao_valor_acumulada / receita_acumulada, 1) if receita_acumulada else None
    )
    ponto_equilibrio_receita_acumulada = (
        round(custo_fixo_acumulado / (margem_contribuicao_pct / 100), 2)
        if margem_contribuicao_pct else None
    )
    n_meses = len(serie)
    ponto_equilibrio_mensal_medio = (
        round(ponto_equilibrio_receita_acumulada / n_meses, 2)
        if ponto_equilibrio_receita_acumulada is not None and n_meses else None
    )

    resultado = {
        "serie_mensal": serie,
        "receita_acumulada": round(receita_acumulada, 2),
        "lucro_acumulado": round(lucro_acumulado, 2),
        "margem_liquida_acumulada_pct": round(100 * lucro_acumulado / receita_acumulada, 1) if receita_acumulada else None,
        "roi_pct_acumulado": round(100 * lucro_acumulado / receita_liquida_acumulada, 1) if receita_liquida_acumulada else None,
        "ebitda_acumulado": round(ebitda_acumulado, 2) if tem_ebitda else None,
        "ebitda_pct_receita_liquida_acumulado": (
            round(100 * ebitda_acumulado / receita_liquida_acumulada, 1)
            if tem_ebitda and receita_liquida_acumulada else None
        ),
        "custo_fixo_acumulado": round(custo_fixo_acumulado, 2),
        "custo_variavel_acumulado": round(custo_variavel_acumulado, 2),
        "margem_contribuicao_valor_acumulada": round(margem_contribuicao_valor_acumulada, 2),
        "margem_contribuicao_pct": margem_contribuicao_pct,
        "ponto_equilibrio_receita_acumulada": ponto_equilibrio_receita_acumulada,
        "ponto_equilibrio_mensal_medio": ponto_equilibrio_mensal_medio,
        "maior_despesa_mensal_total": (
            round(maior_despesa_mensal_total, 2) if maior_despesa_mensal_total is not None else None
        ),
        "maior_despesa_mensal_period": maior_despesa_mensal_period,
        "aviso": "lucro_liquido vem direto da linha 108 da fonte oficial, não é recalculado por soma — evita divergência já observada de até R$228 mil/mês entre soma simples e valor apurado.",
        "aviso_cvp": (
            "Margem de contribuição = (Receita Bruta − Custo Variável) ÷ Receita Bruta, "
            "calculada só no acumulado do período (não mês a mês — instável em meses com "
            "pico de Contas Novas, ver aviso completo na documentação do módulo). Custo "
            "fixo = Despesas com Pessoal + Despesas Bancárias + parte fixa de Despesas "
            "Gerais (conta a conta). Custo variável = Impostos + Contas Novas + parte "
            "variável de Despesas Gerais (conta a conta). Ponto de equilíbrio = Custo "
            "Fixo ÷ Margem de Contribuição (%)."
        ),
        "aviso_roi_ebitda": (
            "ROI = Lucro Líquido ÷ Receita Líquida. EBITDA = Lucro antes do Imposto de "
            "Renda e de Movimentos com Sócios (linha 178 da DRE) + Depreciação + Juros — "
            "todos campos da mesma planilha DRE interna já validada, sem usar nenhum dado "
            "do Balanço Patrimonial/Balancete."
        ),
    }

    if recebimento:
        resultado["pmr_dias"] = recebimento.get("pmr_dias")
        resultado["pmp_dias"] = recebimento.get("pmp_dias")
        resultado["inadimplencia_pct"] = recebimento.get("inadimplencia_pct")
        if recebimento.get("aviso_recebimento"):
            resultado["aviso_recebimento"] = recebimento["aviso_recebimento"]
        if recebimento.get("periodo_recebimento"):
            resultado["periodo_recebimento"] = recebimento["periodo_recebimento"]

    return resultado
