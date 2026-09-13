"""Normalizador Técnico-Operacional — volume de OS (Roteiros de Serviços).

Fonte validada: Tecnico-Operacional/01. ROTEIROS DIÁRIOS/<ano>/Roteiros de
Serviços <ano>.xlsx, aba "ROTEIROS". Colunas confirmadas em exploração real:
DATA, OS, CLIENTE, ENDEREÇO, MUNICIPIO, SERVIÇO, VALOR, VEÍCULO, MOTORISTA,
AJUDANTE, STATUS, DEVOLUÇÃO, OBSERVAÇÃO.

Nem toda linha tem número de OS (serviço recorrente tipo "diária" às vezes não
gera OS) — por isso o total de linhas e o total de OS numeradas são reportados
separadamente, sem forçar os dois a serem iguais.
"""
from collections import defaultdict


def normalize_operacional(linhas: list[dict]) -> dict:
    total_linhas = len(linhas)
    com_os = 0
    por_status = defaultdict(int)
    por_servico = defaultdict(lambda: {"quantidade": 0, "valor_total": 0.0})
    por_dia = defaultdict(int)
    faturamento_total = 0.0

    for linha in linhas:
        if (linha.get("os") or "").strip():
            com_os += 1

        status = (linha.get("status") or "Sem status").strip()
        por_status[status] += 1

        servico = (linha.get("servico") or "Não informado").strip()
        valor = linha.get("valor") or 0
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            valor = 0.0
        por_servico[servico]["quantidade"] += 1
        por_servico[servico]["valor_total"] += valor
        faturamento_total += valor

        data = (linha.get("data") or "").strip()
        if data:
            dia = data[:10]  # aceita "AAAA-MM-DD" ou já cortado
            por_dia[dia] += 1

    taxa_realizado = None
    if por_status:
        realizados = sum(v for k, v in por_status.items() if k.strip().lower() == "realizado")
        total_com_status = sum(por_status.values())
        taxa_realizado = round(100 * realizados / total_com_status, 1) if total_com_status else None

    return {
        "total_linhas": total_linhas,
        "total_os_numeradas": com_os,
        "faturamento_total": round(faturamento_total, 2),
        "taxa_realizado_pct": taxa_realizado,
        "por_status": dict(por_status),
        "por_servico": {
            k: {"quantidade": v["quantidade"], "valor_total": round(v["valor_total"], 2)}
            for k, v in sorted(por_servico.items(), key=lambda kv: -kv[1]["valor_total"])
        },
        "volume_por_dia": dict(sorted(por_dia.items())),
    }
