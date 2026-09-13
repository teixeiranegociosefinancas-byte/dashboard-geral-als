"""Normalizador CAPEX — aquisição de ativo fixo (Imobilizado).

Investigação real feita em 13/09/2026 (Google Drive): o balancete/razão
contábil oficial da ALS (sistema TRACT Contabilidade, assinado digitalmente,
período 01/01/2025-31/12/2025 — o único balancete fechado disponível até
agora) mostra Débito = R$0,00 e Crédito = R$0,00 em TODAS as subcontas de
Imobilizado (Edifícios, Máquinas e Equipamentos, Móveis, Terrenos, Veículos)
durante o ano inteiro. A única movimentação ligada a ativo foi na conta
separada "Participação em Consórcios" (+R$39.231,91 de parcelas pagas —
financiamento pra uma aquisição futura, ainda não capitalizado). Cruzando
com contas_a_pagar.xlsx 2026 (maiores lançamentos e busca por palavra-chave
de ativo), não há nenhum lançamento de compra de ativo fixo — só locação de
caminhões/equipamentos de terceiros (inclusive da Prime, empresa do mesmo
grupo), manutenção, seguro e combustível.

Diferente das outras áreas, aqui NÃO há série mensal recorrente pra
reingerir — é um retrato do período coberto pelo balancete fechado mais
recente. Reingestão só faz sentido quando a contabilidade fechar um novo
balancete (ex: 2026) com movimentação diferente de zero.
"""


def normalize_capex(rows: list[dict]) -> dict:
    """`rows`: lista de dicts {categoria, valor}. Categorias esperadas:
    - "capex_capitalizado": total de Débito lançado nas contas de Imobilizado
      (aquisição de ativo fixo já capitalizada) no período coberto.
    - "consorcio_nao_capitalizado": parcelas pagas em consórcio no período
      (financiamento de uma aquisição futura, ainda não é ativo capitalizado).
    """
    valores = {}
    for r in rows:
        categoria = r.get("categoria")
        if categoria:
            valores[categoria] = round(float(r.get("valor") or 0), 2)

    capex_capitalizado = valores.get("capex_capitalizado", 0.0)
    consorcio_nao_capitalizado = valores.get("consorcio_nao_capitalizado", 0.0)

    return {
        "capex_capitalizado": capex_capitalizado,
        "consorcio_nao_capitalizado": consorcio_nao_capitalizado,
        "aviso": (
            "CAPEX = valor de aquisição de ativo fixo (Imobilizado) capitalizado "
            "contabilmente no período. Fonte: balancete oficial (razão contábil), "
            "único período fechado disponível é 01/01/2025-31/12/2025 — ainda não "
            "existe balancete fechado de 2026 pra atualizar este número. "
            "Ver bloco Explicações para o motivo do valor ser zero."
        ),
    }
