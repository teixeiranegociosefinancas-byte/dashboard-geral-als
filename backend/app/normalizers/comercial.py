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

Faixas de comissão (confirmado pelo usuário 2026-09-13): as faixas de
faturamento mensal são 20k / 50k / 80k — usadas aqui só como referência de
"falta quanto pra próxima faixa" (progresso_meta), NÃO para calcular valor de
comissão em R$ (a coluna "Comissao" da planilha fonte é digitada à mão e
está com divergências confirmadas pelo usuário, ex: Silas aparece com 3,5%
lá mas o usuário confirmou que ele não recebe comissão). Alex Santos, Silas
Teixeira e Licitações foram confirmados pelo usuário como vendedores que NÃO
recebem comissão (Alex é o maior vendedor mas tem outro regime), por isso
ficam fora do progresso_meta. O mês de referência usado é o mês mais recente
com faturamento no `vendedor_mensal_rows` de cada vendedor — pode ser um mês
ainda em andamento, isso fica explícito no campo `mes_referencia` devolvido.
"""
import re
from collections import defaultdict


def _nome_vendedor(bruto: str) -> str:
    """Normaliza nome de vendedor: remove prefixo numérico tipo "4- " quando
    presente, pra casar com a convenção já usada em produção (por_vendedor
    hoje é chaveado sem o prefixo, ex: "ALEX SANTOS", não "4- ALEX SANTOS")."""
    return re.sub(r"^\d+-\s*", "", (bruto or "").strip()).strip()


# Não recebem comissão por faixa (outro regime de remuneração) — confirmado
# pelo usuário 2026-09-13.
NAO_RECEBE_COMISSAO = {"ALEX SANTOS", "SILAS TEIXEIRA", "LICITACOES"}

# Saíram do time comercial — não são mais vendedores ativos, então "falta pra
# próxima faixa" não se aplica (o histórico de faturamento continua contando
# no total, só não entra no progresso_meta). Confirmado pelo usuário 2026-09-13.
EX_VENDEDORES = {"CLARISSA CERBINO", "ERICA VIVIANE DOS SANTOS", "EVA TÂMARA"}

NAO_PARTICIPA_COMISSAO = NAO_RECEBE_COMISSAO | EX_VENDEDORES

FAIXAS_META = [20_000.0, 50_000.0, 80_000.0]


def _progresso_meta(faturamento_mes: float) -> dict:
    for limite in FAIXAS_META:
        if faturamento_mes < limite:
            return {
                "proxima_faixa_limite": limite,
                "falta_valor": round(limite - faturamento_mes, 2),
                "falta_pct": round(100 * (limite - faturamento_mes) / limite, 1),
            }
    return {"proxima_faixa_limite": None, "falta_valor": 0.0, "falta_pct": 0.0}


def normalize_comercial(
    faturamento_linhas: list[dict],
    propostas_arquivos: list[dict] | None = None,
    vendedor_rows: list[dict] | None = None,
    vendedor_mensal_rows: list[dict] | None = None,
) -> dict:
    por_servico = defaultdict(float)
    por_vendedor = defaultdict(lambda: {"faturamento": 0.0, "meta": 0.0})
    faturamento_total = 0.0
    meta_total = 0.0

    for linha in faturamento_linhas:
        valor = float(linha.get("faturamento") or 0)
        meta = float(linha.get("meta") or 0)
        servico = (linha.get("servico") or "").strip()
        vendedor = _nome_vendedor(linha.get("vendedor"))

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
            vendedor = _nome_vendedor(linha.get("vendedor"))
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

    # Progresso de meta por faixa (20k/50k/80k), a partir do mês mais recente
    # com faturamento de cada vendedor — não confundir com faturamento_total.
    por_mes_vendedor: dict[str, dict[str, float]] = defaultdict(dict)
    if vendedor_mensal_rows:
        for linha in vendedor_mensal_rows:
            vendedor = _nome_vendedor(linha.get("vendedor"))
            mes = (linha.get("mes") or "").strip()  # "MM/AAAA"
            valor = float(linha.get("faturamento") or 0)
            if vendedor and mes:
                por_mes_vendedor[vendedor][mes] = valor

    def _ordenar_mes(mes: str):
        mm, aaaa = mes.split("/")
        return (int(aaaa), int(mm))

    progresso_meta_por_vendedor: dict[str, dict | None] = {}
    for vendedor, meses in por_mes_vendedor.items():
        if vendedor in NAO_PARTICIPA_COMISSAO:
            continue
        mes_recente = max(meses, key=_ordenar_mes)
        faturamento_mes = meses[mes_recente]
        progresso_meta_por_vendedor[vendedor] = {
            "mes_referencia": mes_recente,
            "faturamento_mes": round(faturamento_mes, 2),
            **_progresso_meta(faturamento_mes),
        }

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
                "status": (
                    "nao_recebe_comissao" if k in NAO_RECEBE_COMISSAO
                    else "ex_vendedor" if k in EX_VENDEDORES
                    else "ativo"
                ),
                "progresso_meta": progresso_meta_por_vendedor.get(k),
            }
            for k, v in sorted(por_vendedor.items(), key=lambda kv: -kv[1]["faturamento"])
        },
        "propostas_geradas_estimado": {
            chave: qtd for chave, qtd in sorted(propostas_por_vendedor_mes.items())
        },
        "aviso": "propostas_geradas_estimado é uma contagem de arquivos por pasta de vendedor, não um log central — não existe fonte oficial disso ainda.",
    }
