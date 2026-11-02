"""Normalizador Fluxo de Caixa — projeção mensal por médias do DRE.

Estimativa (competência, não vencimento de contas a pagar/receber):
- Entradas = receita bruta projetada menos impostos sobre a receita (16,33%, alíquota única da diretoria).
- Saídas = custo mensal médio (receita líquida + outras receitas − lucro, do DRE) + 13º + retirada de lucros.
- Saldo inicial = soma do último saldo de cada banco nos extratos (OFX/PDF).
"""

ALIQUOTA_IMPOSTO = 0.1633


def normalize_fluxo(rows: list[dict]) -> dict:
    """`rows`: uma linha com {"saldo_inicial": x, "saldo_inicial_data": "..."} (opcional)
    e uma linha por mês projetado {mes, receita_bruta, custos, decimo_terceiro, retirada}."""
    saldo_inicial = 0.0
    saldo_data = None
    meses_in = []
    for r in rows:
        if r.get("saldo_inicial") is not None:
            saldo_inicial = float(r["saldo_inicial"])
            saldo_data = r.get("saldo_inicial_data")
        if r.get("mes"):
            meses_in.append(r)

    saldo = saldo_inicial
    serie = []
    for r in meses_in:
        bruta = float(r.get("receita_bruta") or 0)
        impostos = round(bruta * ALIQUOTA_IMPOSTO, 2)
        entradas = round(bruta - impostos, 2)
        saidas = round(
            float(r.get("custos") or 0) + float(r.get("decimo_terceiro") or 0) + float(r.get("retirada") or 0), 2
        )
        fluxo = round(entradas - saidas, 2)
        saldo_inicio = saldo
        saldo = round(saldo + fluxo, 2)
        serie.append({
            "period": r["mes"],
            "saldo_inicial": round(saldo_inicio, 2),
            "receita_bruta": round(bruta, 2),
            "impostos": impostos,
            "entradas_liquidas": entradas,
            "custos": round(float(r.get("custos") or 0), 2),
            "decimo_terceiro": round(float(r.get("decimo_terceiro") or 0), 2),
            "retirada": round(float(r.get("retirada") or 0), 2),
            "saidas_total": saidas,
            "fluxo_liquido": fluxo,
            "saldo_final": saldo,
        })

    return {
        "saldo_inicial": round(saldo_inicial, 2),
        "saldo_inicial_data": saldo_data,
        "saldo_final": saldo,
        "fluxo_total": round(saldo - saldo_inicial, 2),
        "menor_saldo": min((m["saldo_final"] for m in serie), default=saldo_inicial),
        "serie_mensal": serie,
        "aviso": (
            "Projeção por médias do DRE (competência), não por vencimento de contas a pagar/receber. "
            "Receita e custo = média de mar–ago/2026 (DRE V24); imposto 16,33% sobre a receita bruta; "
            "13º em nov/dez = 50% do salário médio por mês. Saldo inicial = último extrato de cada banco "
            "(datas entre 15/10 e 19/10/2026), a confirmar. Confiança: MÉDIA."
        ),
    }
