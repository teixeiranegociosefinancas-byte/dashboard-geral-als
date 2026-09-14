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
"""


def normalize_financeiro(meses: list[dict], recebimento: dict | None = None) -> dict:
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
    """
    serie = []
    receita_acumulada = 0.0
    receita_liquida_acumulada = 0.0
    lucro_acumulado = 0.0
    ebitda_acumulado = 0.0
    tem_ebitda = False

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
        "aviso": "lucro_liquido vem direto da linha 108 da fonte oficial, não é recalculado por soma — evita divergência já observada de até R$228 mil/mês entre soma simples e valor apurado.",
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
