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

- absenteísmo mensal: fonte real é a rubrica "40 HORAS FALTAS" (horas de
  falta injustificada, deduzidas do salário) do resumo por rubrica de cada
  folha mensal — existe SÓ nas folhas da contabilidade TRACT (formato usado
  Jan-Jun/2026). Investigado mês a mês (29/09/2026, todos os 6 meses lidos
  do zero, cruzados pelo campo interno "Competência:" de cada PDF, não pela
  data de modificação do Drive): só Jun/2026 teve horas de falta reais
  (73,30h, 4 funcionários — Carlos Ivan de Souza Lopes, Enedino Santos da
  Cruz, Josias Marques Barbosa, Vander Ramos dos Santos); Jan-Mai/2026
  tiveram 0h. Jul-Ago/2026 usam o formato novo da contabilidade INOVARE
  ("Extrato Mensal.pdf"), que não tem nenhuma rubrica com nome equivalente
  encontrada no resumo por rubrica dos 2 meses — não dá pra afirmar que é
  "zero faltas" com confiança, pode ser que o sistema novo registre isso sob
  outro nome ainda não identificado. Por isso, meses sem essa fonte
  disponível (Jul/Ago em diante, até reinvestigar) entram como
  `horas_falta=None` → `taxa_absenteismo_pct=None` (indisponível), nunca
  como 0 — 0 é reservado pra mês onde a fonte existe e realmente não teve
  falta (Jan-Mai/2026).
  Fórmula: taxa_absenteismo_pct = horas_falta ÷ (headcount × 220h) × 100,
  onde 220h é a jornada mensal padrão (44h semanais, convenção CLT comum) —
  não existe jornada individual por funcionário nessa fonte, então é uma
  aproximação sobre o headcount do mês, documentada no `aviso`.
"""


def _turnover_pct(demitidos: int, headcount_atual: int, headcount_anterior: int | None) -> float | None:
    if headcount_anterior:
        base = (headcount_atual + headcount_anterior) / 2
    else:
        base = headcount_atual
    if not base:
        return None
    return round(100 * demitidos / base, 1)


JORNADA_MENSAL_HORAS = 220.0  # 44h semanais, convenção CLT comum — sem jornada individual na fonte


def _absenteismo_pct(horas_falta: float | None, headcount: int) -> float | None:
    """None = fonte indisponível nesse mês (não é o mesmo que 0 faltas)."""
    if horas_falta is None:
        return None
    horas_previstas = headcount * JORNADA_MENSAL_HORAS
    if not horas_previstas:
        return None
    return round(100 * horas_falta / horas_previstas, 2)


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
    situações como férias/doença que saem do "Trabalhando"), horas_falta
    (float ou None — horas da rubrica "40 HORAS FALTAS" daquele mês; None
    quando a fonte não existe nesse formato de folha, ex. INOVARE Jul/Ago —
    NÃO usar 0 nesse caso, 0 é reservado pra "fonte existe e não teve
    falta").

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
        horas_falta = m.get("horas_falta")
        horas_falta = float(horas_falta) if horas_falta is not None else None
        serie.append({
            "period": m.get("period"),
            "headcount": headcount,
            "admissoes": admissoes,
            "demitidos": demitidos,
            "taxa_demissao_pct": _turnover_pct(demitidos, headcount, headcount_anterior),
            "salario_medio": round(float(m.get("salario_medio") or 0), 2) if m.get("salario_medio") is not None else None,
            "funcionarios_contados_salario": m.get("funcionarios_contados"),
            "horas_falta": round(horas_falta, 2) if horas_falta is not None else None,
            "taxa_absenteismo_pct": _absenteismo_pct(horas_falta, headcount),
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

    # último mês com fonte de absenteísmo disponível (nem sempre é o último mês da série)
    absenteismo_atual = None
    for m in reversed(serie):
        if m["taxa_absenteismo_pct"] is not None:
            absenteismo_atual = m
            break

    return {
        "serie_mensal": serie,
        "headcount_atual": ultimo["headcount"] if ultimo else None,
        "salario_medio_atual": ultimo["salario_medio"] if ultimo else None,
        "taxa_demissao_atual_pct": ultimo["taxa_demissao_pct"] if ultimo else None,
        "taxa_absenteismo_atual_pct": absenteismo_atual["taxa_absenteismo_pct"] if absenteismo_atual else None,
        "taxa_absenteismo_atual_period": absenteismo_atual["period"] if absenteismo_atual else None,
        "aso": aso_resultado,
        "aviso": (
            "Salário médio calculado pelo campo isolado 'Salário:' de cada funcionário "
            "(salário-base contratual, não Proventos÷headcount — evita distorção por "
            "rescisão). Sócios/diretores (pró-labore) sempre excluídos do headcount e do "
            "salário médio. Andreia dos Santos Cerqueira (horista, campo Salário: é valor "
            "da hora) excluída do cálculo do salário médio por decisão do usuário. Taxa de "
            "demissão é calculada aqui (demitidos ÷ headcount médio do mês) — não vem de "
            "fonte pronta. ASO vem da planilha de controle própria do usuário, não dos "
            "PDFs soltos do Drive (a maioria eram formulário em branco, sem exame real). "
            "Taxa de absenteísmo = horas da rubrica 'HORAS FALTAS' ÷ (headcount × 220h) — "
            "fonte só existe nas folhas em formato TRACT (Jan-Jun/2026); meses em formato "
            "INOVARE (Jul/2026 em diante) entram como indisponível (None), não como zero, "
            "porque não foi encontrada rubrica equivalente nesse formato ainda."
        ),
    }
