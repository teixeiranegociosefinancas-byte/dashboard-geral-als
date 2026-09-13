"""Mapeamento de nomes de coluna (como aparecem nas planilhas reais da empresa,
com acento/maiúscula variando) para as chaves que os normalizadores esperam.

Cada área tem seu próprio dicionário porque a mesma palavra pode significar
coisas diferentes em pastas diferentes (ex: "Valor" em Comercial é faturamento,
em Frota seria custo de combustível).
"""

FROTA = {
    "placa": "placa",
    "data": "data",
    "litros": "litros",
    "odômetro": "odometro",
    "odometro": "odometro",
    "km": "odometro",
}

OPERACIONAL = {
    "data": "data",
    "os": "os",
    "cliente": "cliente",
    "endereço": "endereco",
    "municipio": "municipio",
    "município": "municipio",
    "serviço": "servico",
    "servico": "servico",
    "valor": "valor",
    "veículo": "veiculo",
    "veiculo": "veiculo",
    "motorista": "motorista",
    "status": "status",
}

COMERCIAL = {
    "serviço": "servico",
    "servico": "servico",
    "vendedor": "vendedor",
    "faturamento": "faturamento",
    "meta": "meta",
}

FINANCEIRO = {
    "período": "period",
    "periodo": "period",
    "mês": "period",
    "mes": "period",
    "receita bruta": "receita_bruta",
    "impostos": "impostos",
    "receita líquida": "receita_liquida",
    "receita liquida": "receita_liquida",
    "despesas c/ pessoal": "despesas_pessoal",
    "despesas com pessoal": "despesas_pessoal",
    "despesas gerais": "despesas_gerais",
    "despesas bancárias/tributárias": "despesas_bancarias",
    "despesas bancarias": "despesas_bancarias",
    "outras receitas": "outras_receitas",
    "contas novas": "contas_novas",
    "lucro líquido": "lucro_liquido",
    "lucro liquido": "lucro_liquido",
}

BY_AREA = {
    "frota": FROTA,
    "operacional": OPERACIONAL,
    "comercial": COMERCIAL,
    "financeiro": FINANCEIRO,
}


def normalize_headers(headers: list[str], area: str) -> list[str]:
    alias_map = BY_AREA.get(area, {})
    result = []
    for h in headers:
        key = (h or "").strip().lower()
        result.append(alias_map.get(key, key))
    return result
