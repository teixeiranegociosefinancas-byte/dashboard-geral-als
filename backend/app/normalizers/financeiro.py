"""Normalizador Financeiro — DRE mensal.

Fonte validada: DRE_FINANCEIRO_MENSAL_2026_ALS_*.xlsx, uma aba por mês
("DRE MM.AAAA"), estrutura de linhas fixa (documentada em memória/projeto):
linha 6 Receita Bruta, linha 9 Impostos, linha 10/11 Receita Líquida,
linha 15 Despesas c/ Pessoal, linha 33 Despesas Gerais, linha 91 Despesas
Bancárias/Tributárias, linha 99 Outras Receitas, linha 154 Contas Novas,
linha 108 Lucro Líquido (valor já apurado na fonte, não recalculado aqui —
uma tentativa anterior de recalcular via soma simples divergiu em até
R$228 mil em alguns meses comparado ao valor oficial da linha 108).
"""


def normalize_financeiro(meses: list[dict], recebimento: dict | None = None) -> dict:
    """`meses`: lista de dicts, um por mês, com as chaves:
    period ("AAAA-MM"), receita_bruta, impostos, receita_liquida,
    despesas_pessoal, despesas_gerais, despesas_bancarias, outras_receitas,
    contas_novas, lucro_liquido.

    `recebimento`: dict opcional com indicadores de prazo/recebimento,
    calculados fora da série mensal do DRE (fonte: exportações de Contas a
    Receber / Contas a Pagar do ERP). Chaves esperadas: pmr_dias, pmp_dias,
    inadimplencia_pct, e opcionalmente periodo/aviso/detalhes — repassado
    quase verbatim pro payload final, só some se vier None.
    """
    serie = []
    receita_acumulada = 0.0
    lucro_acumulado = 0.0

    for m in sorted(meses, key=lambda x: x.get("period", "")):
        receita = float(m.get("receita_bruta") or 0)
        lucro = float(m.get("lucro_liquido") or 0)
        margem = round(100 * lucro / receita, 1) if receita else None

        serie.append({
            "period": m.get("period"),
            "receita_bruta": round(receita, 2),
            "impostos": round(float(m.get("impostos") or 0), 2),
            "receita_liquida": round(float(m.get("receita_liquida") or 0), 2),
            "despesas_pessoal": round(float(m.get("despesas_pessoal") or 0), 2),
            "despesas_gerais": round(float(m.get("despesas_gerais") or 0), 2),
            "despesas_bancarias": round(float(m.get("despesas_bancarias") or 0), 2),
            "outras_receitas": round(float(m.get("outras_receitas") or 0), 2),
            "contas_novas": round(float(m.get("contas_novas") or 0), 2),
            "lucro_liquido": round(lucro, 2),
            "margem_liquida_pct": margem,
        })
        receita_acumulada += receita
        lucro_acumulado += lucro

    resultado = {
        "serie_mensal": serie,
        "receita_acumulada": round(receita_acumulada, 2),
        "lucro_acumulado": round(lucro_acumulado, 2),
        "margem_liquida_acumulada_pct": round(100 * lucro_acumulado / receita_acumulada, 1) if receita_acumulada else None,
        "aviso": "lucro_liquido vem direto da linha 108 da fonte oficial, não é recalculado por soma — evita divergência já observada de até R$228 mil/mês entre soma simples e valor apurado.",
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
