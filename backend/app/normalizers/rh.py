"""Normalizador RH/Departamento Pessoal — headcount, turnover, salário médio, ASO.

Fontes e metodologia validadas por investigação real (13/09/2026, ver docs do
projeto claude.ai "DASHBOARD GERAL" e memória `areas/dashboard-geral-app.md`):

- headcount/admissões/demitidos: seção "Situações" de cada folha de
  pagamento mensal (`Depar.Pessoal - RH/ALS/FOLHA PAGAMENTO/ALS/2026/<MÊS>/`,
  Jan-Ago/2026 — 3 formatos de arquivo diferentes ao longo do ano: arquivo
  único "_3_FOLHA DE PAGAMENTO PARA ANALISE.pdf" em Jan/Abr/Mai/Jun; 3
  arquivos por centro de custo em Fev/Mar; "Extrato Mensal.pdf" (formato
  novo, contabilidade INOVARE) em Jul/Ago). Sócios/diretores (Vínculo:
  Diretor, rubrica PRO-LABORE — ex: Airam Fernandes dos Santos, Alex Souza
  dos Santos) são EXCLUÍDOS do headcount de "funcionários".

- salário médio: campo isolado `Salário:` de cada funcionário (salário-base
  contratual, ANTES de qualquer rubrica de hora extra/rescisão/férias) — não
  é Proventos÷headcount (proxy antiga, distorcida por rescisão grande em
  algum mês). Só entram funcionários com Situação "Trabalhando" no mês.
  Decisão do usuário (13/09/2026): excluir do cálculo a funcionária horista
  Andreia dos Santos Cerqueira (campo Salário: é o valor da HORA, R$7,55,
  não salário mensal — distorce a média pra baixo). O valor dela aparece
  separado no resultado, nunca dentro da média.

- turnover mensal: sem fonte pronta — calculado aqui como
  demitidos ÷ headcount médio do mês (média entre headcount do mês anterior
  e do mês atual; sem mês anterior, usa só o headcount atual).

- ASO (atestado de saúde ocupacional): fonte é a planilha própria do usuário
  `Controle_NR6_NR33_NR35_MOPP_*.xlsx`, aba "ASO - Vencimento", com Status já
  calculado por funcionário (OK / VENCIDO / SEM ASO VÁLIDO) — não os PDFs
  soltos da pasta ASO do Drive (a maioria eram só formulário de
  encaminhamento em branco, sem exame de verdade, achado inicialmente sem
  dado confiável antes do usuário enviar essa planilha).
"""


def _turnover_pct(demitidos: int, headcount_atual: int, headcount_anterior: int | None) -> float | None:
    if headcount_anterior:
        base = (headcount_atual + headcount_anterior) / 2
    else:
        base = headcount_atual
    if not base:
        return None
    return round(100 * demitidos / base, 1)


def normalize_rh(
    meses: list[dict],
    aso_funcionarios: list[dict] | None = None,
) -> dict:
    """`meses`: lista de dicts, um por mês real de folha, com:
    period ("AAAA-MM"), headcount (nº funcionários "Trabalhando", sócios
    excluídos), admissoes (int), demitidos (int), salario_medio (R$, já
    calculado externamente pelo método do campo Salário:, sócios e Andreia
    excluídos), funcionarios_contados (int, denominador usado no salário
    médio — pode diferir de headcount pela exclusão da Andreia e por
    situações como férias/doença que saem do "Trabalhando").

    `aso_funcionarios`: lista de dicts (snapshot, não série mensal) com
    nome, situacao, data_exame, vencimento, status ("OK"|"VENCIDO"|
    "SEM_ASO_VALIDO"), observacao — vem direto da planilha de controle do
    usuário.
    """
    meses_ordenados = sorted(meses, key=lambda x: x.get("period", ""))

    serie = []
    headcount_anterior = None
    for m in meses_ordenados:
        headcount = int(m.get("headcount") or 0)
        admissoes = int(m.get("admissoes") or 0)
        demitidos = int(m.get("demitidos") or 0)
        serie.append({
            "period": m.get("period"),
            "headcount": headcount,
            "admissoes": admissoes,
            "demitidos": demitidos,
            "taxa_demissao_pct": _turnover_pct(demitidos, headcount, headcount_anterior),
            "salario_medio": round(float(m.get("salario_medio") or 0), 2) if m.get("salario_medio") is not None else None,
            "funcionarios_contados_salario": m.get("funcionarios_contados"),
        })
        headcount_anterior = headcount

    aso_resultado = None
    if aso_funcionarios:
        contagem = {"OK": 0, "VENCIDO": 0, "SEM_ASO_VALIDO": 0}
        for f in aso_funcionarios:
            status = (f.get("status") or "").strip().upper().replace(" ", "_")
            if status in contagem:
                contagem[status] += 1
        aso_resultado = {
            "total_funcionarios": len(aso_funcionarios),
            "ok": contagem["OK"],
            "vencido": contagem["VENCIDO"],
            "sem_aso_valido": contagem["SEM_ASO_VALIDO"],
            "detalhe": aso_funcionarios,
        }

    ultimo = serie[-1] if serie else None

    return {
        "serie_mensal": serie,
        "headcount_atual": ultimo["headcount"] if ultimo else None,
        "salario_medio_atual": ultimo["salario_medio"] if ultimo else None,
        "taxa_demissao_atual_pct": ultimo["taxa_demissao_pct"] if ultimo else None,
        "aso": aso_resultado,
        "aviso": (
            "Salário médio calculado pelo campo isolado 'Salário:' de cada funcionário "
            "(salário-base contratual, não Proventos÷headcount — evita distorção por "
            "rescisão). Sócios/diretores (pró-labore) sempre excluídos do headcount e do "
            "salário médio. Andreia dos Santos Cerqueira (horista, campo Salário: é valor "
            "da hora) excluída do cálculo do salário médio por decisão do usuário. Taxa de "
            "demissão é calculada aqui (demitidos ÷ headcount médio do mês) — não vem de "
            "fonte pronta. ASO vem da planilha de controle própria do usuário, não dos "
            "PDFs soltos do Drive (a maioria eram formulário em branco, sem exame real)."
        ),
    }
