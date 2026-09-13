"""Normalizador de Frota — combustível (km/litro e valor gasto).

A planilha de origem (Planilha de Abastecimentos <ano>.xlsx, aba "Lançamentos")
tem a coluna "Km Percorridos" quebrada (#REF!) — confirmado em exploração real
do arquivo em 23/08/2026. Os dados brutos de odômetro e litros continuam
íntegros, então este normalizador ignora qualquer coluna calculada de km que
vier do arquivo e recalcula tudo a partir do odômetro bruto, exatamente como
foi validado manualmente (veículo OVB-0494: 19.141 km / 6.555 L = 2,92 km/L).

"Valor Total" (Litros × Valor Litro) NÃO está quebrada — reconferido em
13/09/2026 direto na planilha (`Planilha de Abastecimentos 2026.xlsx`,
recarregada com `data_only=True`): fórmula simples, sem erro, 653 linhas,
soma R$446.114,19 no ano, preço médio implícito R$6,83/L — plausível pra
diesel em 2026. Mesmo assim este normalizador recalcula `valor_total` em
Python a partir de `litros` × `valor_litro` brutos (mesmo princípio de nunca
confiar em coluna calculada do arquivo original sem recompor).

Entrada esperada (`lancamentos`): lista de dicts, um por abastecimento, com
pelo menos: placa, data (ISO "AAAA-MM-DD"), litros (float), odometro (float),
valor_litro (float, R$/L — opcional, quando ausente o abastecimento não entra
no valor_gasto, só no litros/km).
Linhas sem placa/data/odometro válidos são descartadas silenciosamente, mas o
total de linhas descartadas é reportado em `descartadas` para não esconder erro.
"""
from collections import defaultdict
from datetime import datetime


def _parse_data(valor):
    if isinstance(valor, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(valor, fmt)
            except ValueError:
                continue
        return None
    if hasattr(valor, "year"):
        return valor
    return None


def normalize_frota(lancamentos: list[dict], cadastro: list[dict] | None = None) -> dict:
    por_placa = defaultdict(list)
    descartadas = 0

    for linha in lancamentos:
        placa = (linha.get("placa") or "").strip().upper()
        data = _parse_data(linha.get("data"))
        litros = linha.get("litros")
        odometro = linha.get("odometro")
        if not placa or data is None or litros in (None, "") or odometro in (None, ""):
            descartadas += 1
            continue
        try:
            litros = float(litros)
            odometro = float(odometro)
        except (TypeError, ValueError):
            descartadas += 1
            continue
        valor_litro = linha.get("valor_litro")
        try:
            valor_litro = float(valor_litro) if valor_litro not in (None, "") else None
        except (TypeError, ValueError):
            valor_litro = None
        valor_total_lancamento = litros * valor_litro if valor_litro is not None else None
        por_placa[placa].append({
            "data": data, "litros": litros, "odometro": odometro,
            "valor_litro": valor_litro, "valor_total": valor_total_lancamento,
        })

    modelos = {}
    if cadastro:
        for c in cadastro:
            placa = (c.get("placa") or "").strip().upper()
            if placa:
                modelos[placa] = {
                    "modelo": c.get("modelo"),
                    "capacidade_m3": c.get("capacidade_m3"),
                }

    resultado_por_veiculo = []
    total_litros = 0.0
    total_km = 0.0
    total_valor_gasto = 0.0

    # Acima disso o salto entre dois abastecimentos consecutivos é reportado
    # como suspeito (mas não descartado) — ainda entra na conta de km/L, só
    # fica visível pra alguém conferir se não foi erro de digitação do
    # odômetro. Descartar sem avisar esconderia o problema em vez de mostrar.
    SALTO_SUSPEITO_KM = 3000

    for placa, lancs in por_placa.items():
        lancs.sort(key=lambda x: x["data"])
        km_percorrido = 0.0
        litros_no_periodo_com_km = 0.0
        saltos_suspeitos = []
        odometro_invalido = 0

        for anterior, atual in zip(lancs, lancs[1:]):
            delta_km = atual["odometro"] - anterior["odometro"]
            if delta_km <= 0:
                # odômetro andou pra trás ou ficou igual — sempre inválido,
                # nunca silenciosamente ignorado do total de descartes.
                odometro_invalido += 1
                continue
            km_percorrido += delta_km
            litros_no_periodo_com_km += atual["litros"]
            if delta_km > SALTO_SUSPEITO_KM:
                saltos_suspeitos.append({
                    "de": anterior["data"].strftime("%Y-%m-%d"),
                    "para": atual["data"].strftime("%Y-%m-%d"),
                    "km": round(delta_km, 1),
                })

        litros_total = sum(l["litros"] for l in lancs)
        km_por_litro = round(km_percorrido / litros_no_periodo_com_km, 2) if litros_no_periodo_com_km else None

        valores = [l["valor_total"] for l in lancs if l["valor_total"] is not None]
        valor_gasto_total = sum(valores) if valores else None
        preco_medio_litro = (
            round(valor_gasto_total / litros_total, 3) if valor_gasto_total and litros_total else None
        )
        r_por_km = (
            round(valor_gasto_total / km_percorrido, 3) if valor_gasto_total and km_percorrido else None
        )

        resultado_por_veiculo.append({
            "placa": placa,
            "modelo": modelos.get(placa, {}).get("modelo"),
            "abastecimentos": len(lancs),
            "litros_total": round(litros_total, 1),
            "km_percorrido_estimado": round(km_percorrido, 1),
            "km_por_litro": km_por_litro,
            "valor_gasto_total": round(valor_gasto_total, 2) if valor_gasto_total is not None else None,
            "preco_medio_litro": preco_medio_litro,
            "custo_por_km": r_por_km,
            "odometro_invalido_ignorado": odometro_invalido,
            "saltos_suspeitos": saltos_suspeitos,
            "primeiro_registro": lancs[0]["data"].strftime("%Y-%m-%d"),
            "ultimo_registro": lancs[-1]["data"].strftime("%Y-%m-%d"),
        })
        total_litros += litros_total
        total_km += km_percorrido
        if valor_gasto_total is not None:
            total_valor_gasto += valor_gasto_total

    resultado_por_veiculo.sort(key=lambda v: v["placa"])

    return {
        "veiculos": resultado_por_veiculo,
        "total_veiculos": len(resultado_por_veiculo),
        "total_litros": round(total_litros, 1),
        "km_por_litro_frota": round(total_km / total_litros, 2) if total_litros else None,
        "valor_gasto_total": round(total_valor_gasto, 2) if total_valor_gasto else None,
        "preco_medio_litro_frota": round(total_valor_gasto / total_litros, 3) if total_valor_gasto and total_litros else None,
        "linhas_descartadas": descartadas,
        "aviso": "km/litro recalculado a partir do odômetro bruto (coluna de fórmula Km Percorridos do arquivo original tem #REF!). Valor gasto = litros × valor_litro brutos, recalculado em Python (a coluna Valor Total do arquivo em si não está quebrada, mas por princípio não confiamos em fórmula do arquivo sem recompor).",
    }
