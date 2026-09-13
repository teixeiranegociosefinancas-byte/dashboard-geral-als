"""Normalizador OPEX — despesas operacionais reais (Pessoal + Gerais +
Bancárias) x receita, mês a mês.

Escolha de escopo (13/09/2026, confirmada pelo usuário via pergunta direta):
dentre as opções possíveis (total x receita, ranking de contas, evolução por
categoria, comparação com Orçamento), o usuário pediu especificamente
"Total de despesas operacionais x receita" — visão de eficiência
operacional simples, não o detalhamento conta a conta (que já existe,
parcialmente, dentro da área Orçamento).

Reaproveita a MESMA estrutura de entrada do `normalize_financeiro` (nenhuma
fonte nova precisou ser investigada — os dados já estavam ingeridos):
period, receita_bruta, receita_liquida, despesas_pessoal, despesas_gerais,
despesas_bancarias.

Diferença deliberada frente à área Orçamento: aqui só entram números REAIS
(realizado), sem projeção/estimativa nenhuma — é uma leitura de eficiência
operacional histórica, não uma previsão.
"""


def normalize_opex(meses: list[dict]) -> dict:
    """`meses`: lista de dicts, um por mês, com as chaves period ("AAAA-MM"),
    receita_bruta, receita_liquida, despesas_pessoal, despesas_gerais,
    despesas_bancarias (mesmas chaves já usadas em Financeiro/Orçamento).
    """
    serie = []
    percentuais_liquida = []

    for m in sorted(meses, key=lambda x: x.get("period", "")):
        despesas_pessoal = round(float(m.get("despesas_pessoal") or 0), 2)
        despesas_gerais = round(float(m.get("despesas_gerais") or 0), 2)
        despesas_bancarias = round(float(m.get("despesas_bancarias") or 0), 2)
        receita_bruta = float(m.get("receita_bruta") or 0)
        receita_liquida = float(m.get("receita_liquida") or 0)

        opex_total = round(despesas_pessoal + despesas_gerais + despesas_bancarias, 2)
        opex_pct_receita_liquida = round(100 * opex_total / receita_liquida, 1) if receita_liquida else None
        opex_pct_receita_bruta = round(100 * opex_total / receita_bruta, 1) if receita_bruta else None

        if opex_pct_receita_liquida is not None:
            percentuais_liquida.append(opex_pct_receita_liquida)

        serie.append({
            "period": m.get("period"),
            "despesas_pessoal": despesas_pessoal,
            "despesas_gerais": despesas_gerais,
            "despesas_bancarias": despesas_bancarias,
            "opex_total": opex_total,
            "receita_bruta": round(receita_bruta, 2),
            "receita_liquida": round(receita_liquida, 2),
            "opex_pct_receita_liquida": opex_pct_receita_liquida,
            "opex_pct_receita_bruta": opex_pct_receita_bruta,
        })

    ultimo = serie[-1] if serie else None
    opex_pct_media = round(sum(percentuais_liquida) / len(percentuais_liquida), 1) if percentuais_liquida else None

    return {
        "serie_mensal": serie,
        "opex_total_atual": ultimo["opex_total"] if ultimo else None,
        "opex_pct_receita_atual": ultimo["opex_pct_receita_liquida"] if ultimo else None,
        "opex_pct_receita_media": opex_pct_media,
        "aviso": (
            "OPEX = Despesas com Pessoal + Despesas Gerais + Despesas Bancárias "
            "(mesmas linhas já usadas em Financeiro/Orçamento). O percentual "
            "principal usa a Receita Líquida (após impostos) como base — "
            "também disponível vs. Receita Bruta em cada mês. São valores "
            "REAIS (realizado), sem nenhuma projeção — para a versão "
            "estimado x realizado, ver a área Orçamento."
        ),
    }
