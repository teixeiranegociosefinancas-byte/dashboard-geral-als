"""Normalizador Comercial — faturamento por serviço (DRE) e por vendedor
(relatório de Comissão de OS) e contagem de propostas geradas por vendedor/mês
(proxy, ver aviso abaixo).

Faturamento total e por_servico vêm do DRE (linhas 111-123) — fonte de verdade
já validada. Faturamento por vendedor vem de uma base diferente (Comissão de
OS, por "Data de Fechamento" da OS) — por isso é recebido separadamente em
`vendedor_rows` e NUNCA somado a faturamento_total/por_servico: são
metodologias diferentes (conta contábil x OS individual) e os totais não
batem exatamente entre si (diferença real observada ~5%, esperada).

Não existe hoje um log central confiável de propostas comerciais (confirmado em
exploração real: CODIGOS DE PROPOSTAS.xlsx é só uma numeração sequencial, sem
metadado por proposta). Enquanto isso não muda, "propostas geradas" é estimado
contando os arquivos de proposta dentro da pasta de cada vendedor, por mês —
por isso essa função aceita `propostas_arquivos` como uma lista solta de
{vendedor, data_criacao} vinda da listagem do Drive, não de uma planilha.
"""
from collections import defaultdict


def normalize_comercial(
    faturamento_linhas: list[dict],
    propostas_arquivos: list[dict] | None = None,
    vendedor_rows: list[dict] | None = None,
) -> dict:
    por_servico = defaultdict(float)
    por_vendedor = defaultdict(lambda: {"faturamento": 0.0, "meta": 0.0})
    faturamento_total = 0.0
    meta_total = 0.0

    for linha in faturamento_linhas:
        valor = float(linha.get("faturamento") or 0)
        meta = float(linha.get("meta") or 0)
        servico = (linha.get("servico") or "").strip()
        vendedor = (linha.get("vendedor") or "").strip()

        if servico:
            por_servico[servico] += valor
        if vendedor:
            por_vendedor[vendedor]["faturamento"] += valor
            por_vendedor[vendedor]["meta"] += meta

        faturamento_total += valor
        meta_total += meta

    # Faturamento por vendedor, de uma base separada (Comissão de OS) — não
    # entra em faturamento_total/por_servico, só alimenta a tabela por vendedor.
    if vendedor_rows:
        for linha in vendedor_rows:
            vendedor = (linha.get("vendedor") or "").strip()
            valor = float(linha.get("faturamento") or 0)
            meta = float(linha.get("meta") or 0)
            if vendedor:
                por_vendedor[vendedor]["faturamento"] += valor
                por_vendedor[vendedor]["meta"] += meta

    propostas_por_vendedor_mes = defaultdict(int)
    if propostas_arquivos:
        for p in propostas_arquivos:
            vendedor = (p.get("vendedor") or "Não identificado").strip()
            data = (p.get("data_criacao") or "")[:7]  # AAAA-MM
            if data:
                propostas_por_vendedor_mes[f"{vendedor}|{data}"] += 1

    return {
        "faturamento_total": round(faturamento_total, 2),
        "meta_total": round(meta_total, 2),
        "atingimento_pct": round(100 * faturamento_total / meta_total, 1) if meta_total else None,
        "por_servico": {k: round(v, 2) for k, v in sorted(por_servico.items(), key=lambda kv: -kv[1])},
        "por_vendedor": {
            k: {
                "faturamento": round(v["faturamento"], 2),
                "meta": round(v["meta"], 2),
                "atingimento_pct": round(100 * v["faturamento"] / v["meta"], 1) if v["meta"] else None,
            }
            for k, v in sorted(por_vendedor.items(), key=lambda kv: -kv[1]["faturamento"])
        },
        "propostas_geradas_estimado": {
            chave: qtd for chave, qtd in sorted(propostas_por_vendedor_mes.items())
        },
        "aviso": "propostas_geradas_estimado é uma contagem de arquivos por pasta de vendedor, não um log central — não existe fonte oficial disso ainda.",
    }
