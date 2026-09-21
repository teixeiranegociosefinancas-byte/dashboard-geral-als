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


MOTIVO_OUTROS = (
    "por_servico soma só as contas de serviço já mapeadas na Comissão de OS/DRE "
    "(10 categorias). A Receita Bruta oficial do DRE inclui outras contas que não "
    "têm mapeamento de serviço linha a linha (ex: conta 557 'Hidrojato' em julho, "
    "ajuste de 'Outras Receitas' em janeiro) — por isso 'Outros/Não categorizado' "
    "existe: é a diferença entre a Receita Bruta oficial e a soma das 10 categorias "
    "conhecidas, pra faturamento_total bater exatamente com o Financeiro. Achado "
    "real 2026-09-18: diferença de R$273.529,95 no acumulado jan-jul/2026, "
    "confirmada linha a linha contra o DRE (não é dado desatualizado)."
)

META_MENSAL_BASE = (
    "R$759.930,39/mês — média do faturamento real dos últimos 3 meses fechados "
    "disponíveis (mai/jun/jul de 2026), proposta pelo Claude com base no "
    "histórico financeiro e aprovada pelo usuário em 2026-09-18."
)


def normalize_comercial(
    faturamento_linhas: list[dict],
    propostas_arquivos: list[dict] | None = None,
    vendedor_rows: list[dict] | None = None,
    vendedor_mensal_rows: list[dict] | None = None,
    periodo_servico: str | None = None,
    periodo_vendedor: str | None = None,
    receita_bruta_oficial: float | None = None,
    meta_mensal: float | None = 759_930.39,
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

    # "Outros/Não categorizado": reconcilia com a Receita Bruta oficial do DRE
    # (ver MOTIVO_OUTROS) — só é aplicado quando o valor oficial é informado.
    diferenca_outros = None
    if receita_bruta_oficial is not None:
        diferenca_outros = round(float(receita_bruta_oficial), 2) - round(faturamento_total, 2)
        if abs(diferenca_outros) > 0.01:
            por_servico["Outros/Não categorizado"] += diferenca_outros
            faturamento_total += diferenca_outros

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
        "meta_mensal": round(meta_mensal, 2) if meta_mensal is not None else None,
        "meta_mensal_base": META_MENSAL_BASE if meta_mensal is not None else None,
        "receita_bruta_oficial": round(float(receita_bruta_oficial), 2) if receita_bruta_oficial is not None else None,
        "outros_nao_categorizado": round(diferenca_outros, 2) if diferenca_outros is not None else None,
        "motivo_outros_nao_categorizado": MOTIVO_OUTROS if diferenca_outros is not None else None,
        "periodo_servico": periodo_servico,
        "periodo_vendedor": periodo_vendedor,
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
