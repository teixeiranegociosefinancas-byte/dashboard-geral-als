// Cálculo do Orçamento (modelo_dre + ajustes do usuário).
//
// Espelha EXATAMENTE a regra do backend (`_build_modelo_dre` em
// backend/app/normalizers/orcamento.py): sem nenhum ajuste, o resultado daqui
// tem que ser igual ao `resumo_base` que veio do backend (há um teste que
// confere isso). Com ajustes, o valor efetivo de uma célula é o que o usuário
// digitou; senão, o valor base do backend.
//
// Regra de fechamento positivo (pedido do usuário): nos meses projetados, se a
// receita não cobre despesas × (1 + margem) depois dos impostos, a diferença
// vira a linha derivada "Ajuste de receita (meta de venda)":
//   Rb necessária = (despesas × (1 + margem) − receitas não tributáveis) ÷ (1 − alíquota)
//   ajuste        = max(0, Rb necessária − receita bruta já prevista)

export const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function mesCurto(period) {
  return MESES[Number(period.split("-")[1]) - 1];
}

export function parametrosEfetivos(modelo, overrides) {
  return {
    aliquota: overrides?.aliquota_imposto_pct ?? modelo.parametros.aliquota_imposto_pct,
    margem: overrides?.margem_minima_sobre_despesa_pct ?? modelo.parametros.margem_minima_sobre_despesa_pct,
  };
}

export function valorEfetivo(linha, period, ajustes) {
  const a = ajustes?.[linha.id]?.[period];
  return a !== undefined && a !== null ? a : linha.base[period] ?? 0;
}

export function foiAjustada(linha, period, ajustes) {
  const a = ajustes?.[linha.id]?.[period];
  return a !== undefined && a !== null && Math.abs(a - (linha.base[period] ?? 0)) > 0.005;
}

const soma = (arr) => arr.reduce((s, v) => s + v, 0);

export function calcular(modelo, ajustes = {}, overrides = {}) {
  const { aliquota, margem } = parametrosEfetivos(modelo, overrides);
  const periodos = modelo.meses.map((m) => m.period);
  const statusDe = Object.fromEntries(modelo.meses.map((m) => [m.period, m.status]));
  const nReais = modelo.meses.filter((m) => m.status === "real").length;

  const valoresLinha = {}; // id -> {period: valor}
  const grupoTotais = {}; // id -> {period: soma}
  for (const sec of ["receitas", "despesas"]) {
    for (const g of modelo[sec].grupos) {
      grupoTotais[g.id] = {};
      for (const p of periodos) grupoTotais[g.id][p] = 0;
      for (const l of g.linhas) {
        valoresLinha[l.id] = {};
        for (const p of periodos) {
          const v = valorEfetivo(l, p, ajustes);
          valoresLinha[l.id][p] = v;
          grupoTotais[g.id][p] += v;
        }
      }
    }
  }

  const meses = periodos.map((p) => {
    const real = statusDe[p] === "real";
    let recTrib = 0;
    let recNaoTrib = 0;
    for (const g of modelo.receitas.grupos) {
      if (g.tributavel === false) recNaoTrib += grupoTotais[g.id][p];
      else recTrib += grupoTotais[g.id][p];
    }
    const despesas = soma(modelo.despesas.grupos.map((g) => grupoTotais[g.id][p]));
    let ajuste = 0;
    if (!real) {
      const necessaria = (despesas * (1 + margem / 100) - recNaoTrib) / (1 - aliquota / 100);
      ajuste = Math.max(0, necessaria - recTrib);
    }
    const receitaBruta = recTrib + ajuste;
    const impostos = (receitaBruta * aliquota) / 100;
    const receitaTotal = receitaBruta + recNaoTrib;
    const resultado = receitaTotal - impostos - despesas;
    return {
      period: p,
      real,
      recTrib,
      recNaoTrib,
      ajuste,
      receitaBruta,
      receitaTotal,
      impostos,
      despesas,
      saidas: impostos + despesas,
      resultado,
      margemPct: receitaTotal ? (100 * resultado) / receitaTotal : null,
    };
  });

  const ano = {
    receita: soma(meses.map((m) => m.receitaTotal)),
    receitaBruta: soma(meses.map((m) => m.receitaBruta)),
    impostos: soma(meses.map((m) => m.impostos)),
    despesas: soma(meses.map((m) => m.despesas)),
    resultado: soma(meses.map((m) => m.resultado)),
    ajuste: soma(meses.map((m) => m.ajuste)),
  };
  ano.margemPct = ano.receita ? (100 * ano.resultado) / ano.receita : null;
  const reais = meses.filter((m) => m.real);
  const ytd = {
    receita: soma(reais.map((m) => m.receitaTotal)),
    despesas: soma(reais.map((m) => m.despesas)),
    impostos: soma(reais.map((m) => m.impostos)),
    resultado: soma(reais.map((m) => m.resultado)),
  };

  return { aliquota, margem, periodos, statusDe, nReais, valoresLinha, grupoTotais, meses, ano, ytd };
}

// Estatísticas de uma linha: previsto no ano, realizado, a realizar, consumo e
// variação contra o ritmo (previsto × meses fechados ÷ 12).
export function estatLinha(valores, periodos, statusDe) {
  const nReais = periodos.filter((p) => statusDe[p] === "real").length;
  let previsto = 0;
  let realizado = 0;
  for (const p of periodos) {
    const v = valores[p] ?? 0;
    previsto += v;
    if (statusDe[p] === "real") realizado += v;
  }
  const aRealizar = previsto - realizado;
  const ritmoPct = periodos.length ? nReais / periodos.length : 0;
  const esperadoAteAgora = previsto * ritmoPct;
  return {
    previsto,
    realizado,
    aRealizar,
    consumoPct: previsto > 0 ? (100 * realizado) / previsto : null,
    esperadoAteAgora,
    variacao: realizado - esperadoAteAgora,
    variacaoPct: esperadoAteAgora > 0 ? (100 * (realizado - esperadoAteAgora)) / esperadoAteAgora : null,
    ritmoPct: 100 * ritmoPct,
  };
}

// Status de consumo de uma conta de DESPESA contra o ritmo do ano.
// Sempre devolve ícone + rótulo (nunca só cor).
export function statusConsumo(stat) {
  if (stat.previsto <= 0 && stat.realizado > 0) return { chave: "sem", icone: "○", rotulo: "Sem orçamento" };
  if (stat.previsto <= 0) return { chave: "zero", icone: "–", rotulo: "Sem movimento" };
  const razao = stat.esperadoAteAgora > 0 ? stat.realizado / stat.esperadoAteAgora : 0;
  if (razao <= 1.05) return { chave: "ok", icone: "✔", rotulo: "No ritmo" };
  if (razao <= 1.25) return { chave: "atencao", icone: "▲", rotulo: "Atenção" };
  return { chave: "acima", icone: "✖", rotulo: "Acima do ritmo" };
}

// "1.234,56" / "1234,56" / "1234.56" / "R$ 1.234" -> número
export function parseValor(texto) {
  if (typeof texto === "number") return texto;
  let s = String(texto ?? "").replace(/[R$\s]/g, "");
  if (!s) return null;
  const neg = s.startsWith("-") || (s.startsWith("(") && s.endsWith(")"));
  s = s.replace(/[-()]/g, "");
  if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  else if ((s.match(/\./g) || []).length > 1) s = s.replace(/\./g, "");
  else if (/^\d{1,3}\.\d{3}$/.test(s)) s = s.replace(".", ""); // "1.234" = mil duzentos e trinta e quatro
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return neg ? -n : n;
}

// Aplica uma edição de célula ao conjunto de ajustes (imutável). Se o valor
// digitado é igual ao base, o ajuste é removido (a célula volta ao original).
export function aplicarEdicao(ajustes, linha, period, valor) {
  const novo = { ...ajustes };
  const base = linha.base[period] ?? 0;
  const atual = { ...(novo[linha.id] || {}) };
  if (valor === null || Math.abs(valor - base) <= 0.005) delete atual[period];
  else atual[period] = Math.round(valor * 100) / 100;
  if (Object.keys(atual).length) novo[linha.id] = atual;
  else delete novo[linha.id];
  return novo;
}

export function contarAjustes(ajustes) {
  return Object.values(ajustes || {}).reduce((n, m) => n + Object.keys(m).length, 0);
}

export function iguais(a, b) {
  return JSON.stringify(ordenar(a)) === JSON.stringify(ordenar(b));
}
function ordenar(o) {
  if (Array.isArray(o)) return o.map(ordenar);
  if (o && typeof o === "object") {
    return Object.fromEntries(Object.keys(o).sort().map((k) => [k, ordenar(o[k])]));
  }
  return o;
}
