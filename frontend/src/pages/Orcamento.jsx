import { useEffect, useMemo, useState } from "react";
import { fetchAjustesOrcamento, salvarAjustesOrcamento } from "../api.js";
import KpiCard from "../components/KpiCard.jsx";
import { fmtData, fmtMoeda, fmtPct } from "../format.js";
import { ConsumoPorConta, GraficoMensal } from "../orcamento/charts.jsx";
import {
  aplicarEdicao,
  calcular,
  contarAjustes,
  estatLinha,
  foiAjustada,
  iguais,
  mesCurto,
  parseValor,
  valorEfetivo,
} from "../orcamento/model.js";

const num0 = (v) => Math.round(v).toLocaleString("pt-BR");
const num2 = (v) => v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ---------------------------------------------------------------- célula editável
function Celula({ linha, period, ajustes, editavel, onEdit }) {
  const efetivo = valorEfetivo(linha, period, ajustes);
  const ajustada = foiAjustada(linha, period, ajustes);
  const [txt, setTxt] = useState(null);

  if (!editavel) return <span className="orc-ro">{num0(efetivo)}</span>;

  const confirmar = () => {
    if (txt === null) return;
    const v = parseValor(txt);
    setTxt(null);
    if (v !== null) onEdit(linha, period, v);
  };

  return (
    <span className={`orc-cell ${ajustada ? "ajustada" : ""}`}>
      <input
        inputMode="decimal"
        aria-label={`${linha.nome} em ${mesCurto(period)}`}
        value={txt ?? num0(efetivo)}
        onFocus={(e) => {
          setTxt(num2(efetivo));
          e.target.select();
        }}
        onChange={(e) => setTxt(e.target.value)}
        onBlur={confirmar}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") {
            setTxt(null);
            e.currentTarget.blur();
          }
        }}
      />
      {ajustada && (
        <button
          type="button"
          className="orc-reset"
          title={`Voltar ao valor original (${fmtMoeda(linha.base[period] ?? 0)})`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onEdit(linha, period, linha.base[period] ?? 0)}
        >
          ↺
        </button>
      )}
    </span>
  );
}

// campo de percentual com texto local (deixa digitar "16,3" sem o React reescrever)
function ParamInput({ valor, onChange }) {
  const [txt, setTxt] = useState(null);
  return (
    <input
      inputMode="decimal"
      value={txt ?? String(valor).replace(".", ",")}
      onFocus={(e) => e.target.select()}
      onChange={(e) => {
        setTxt(e.target.value);
        onChange(e.target.value);
      }}
      onBlur={() => setTxt(null)}
    />
  );
}

// ---------------------------------------------------------------- aba: mês a mês
function MesAMes({ modelo, calc, ajustes, onEdit, mes, setMes, meta }) {
  const m = calc.meses.find((x) => x.period === mes);
  const editavel = !m.real;
  const [abertos, setAbertos] = useState({});
  const alterna = (id) => setAbertos((a) => ({ ...a, [id]: !a[id] }));

  const bloco = (g, secao) => {
    const aberto = abertos[g.id] ?? (secao === "receitas");
    const linhas = [...g.linhas].sort((a, b) => valorEfetivo(b, mes, ajustes) - valorEfetivo(a, mes, ajustes));
    return (
      <div key={g.id} className="orc-grupo">
        <button type="button" className="orc-grupo-head" onClick={() => alterna(g.id)} aria-expanded={aberto}>
          <span className="orc-chev">{aberto ? "▾" : "▸"}</span>
          <span className="orc-grupo-nome">{g.nome}</span>
          <span className="orc-grupo-n">{g.linhas.length} {g.linhas.length === 1 ? "conta" : "contas"}</span>
          <b>{fmtMoeda(calc.grupoTotais[g.id][mes])}</b>
        </button>
        {aberto && (
          <div className="orc-linhas">
            {linhas.map((l) => {
              const v = valorEfetivo(l, mes, ajustes);
              if (!editavel && Math.abs(v) < 0.005) return null;
              return (
                <div key={l.id} className="orc-linha">
                  <span className="orc-linha-nome" title={l.motivo_nao_projetar || l.nota || l.nome}>
                    {l.nome}
                    {l.projetar === false && !m.real ? <em className="orc-tag">não projetada</em> : null}
                  </span>
                  <Celula linha={l} period={mes} ajustes={ajustes} editavel={editavel} onEdit={onEdit} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const atingeMeta = meta ? m.receitaTotal >= meta : null;

  return (
    <div>
      <div className="orc-chips" role="tablist" aria-label="Escolher o mês">
        {calc.meses.map((x) => (
          <button
            key={x.period}
            type="button"
            className={`orc-chip ${x.period === mes ? "on" : ""} ${x.real ? "" : "proj"}`}
            onClick={() => setMes(x.period)}
          >
            {mesCurto(x.period)}
            <small>{x.real ? "real" : "proj."}</small>
          </button>
        ))}
      </div>

      <div className="orc-dre">
        <section className="orc-col">
          <h3>Receitas <small>(esquerda)</small></h3>
          {modelo.receitas.grupos.map((g) => bloco(g, "receitas"))}
          {m.ajuste > 0 && (
            <div className="orc-ajuste" title="Calculado automaticamente: as despesas do mês (mais a margem mínima e os impostos) passam da receita prevista, então a receita é elevada até o orçamento fechar positivo.">
              <span>▲ Ajuste de receita — meta de venda para fechar positivo</span>
              <b>{fmtMoeda(m.ajuste)}</b>
            </div>
          )}
          <div className="orc-total"><span>Receita total do mês</span><b>{fmtMoeda(m.receitaTotal)}</b></div>
          {meta ? (
            <div className="orc-nota">
              {atingeMeta ? "✔" : "▼"} {atingeMeta ? "Acima" : "Abaixo"} da meta comercial ({fmtMoeda(meta)}) em {fmtMoeda(Math.abs(m.receitaTotal - meta))}
            </div>
          ) : null}
        </section>

        <section className="orc-col">
          <h3>Despesas <small>(direita)</small></h3>
          {modelo.despesas.grupos.map((g) => bloco(g, "despesas"))}
          <div className="orc-linha orc-imposto">
            <span className="orc-linha-nome">Impostos ({String(calc.aliquota).replace(".", ",")}% da receita bruta)</span>
            <span className="orc-ro">{num0(m.impostos)}</span>
          </div>
          <div className="orc-total"><span>Total de saídas (despesas + impostos)</span><b>{fmtMoeda(m.saidas)}</b></div>
        </section>
      </div>

      <div className={`orc-resultado ${m.resultado < 0 ? "neg" : "pos"}`}>
        <span>{m.resultado < 0 ? "▼ Resultado negativo" : "▲ Resultado positivo"} em {mesCurto(m.period)}/{m.period.slice(0, 4)}</span>
        <b>{fmtMoeda(m.resultado)}</b>
        <span className="dim">{m.margemPct === null ? "" : `margem ${fmtPct(m.margemPct)}`}</span>
      </div>
      {!editavel && <div className="orc-nota">Mês fechado no DRE — valores são fato e não podem ser editados aqui.</div>}
    </div>
  );
}

// ---------------------------------------------------------------- aba: grade do ano
function GradeAno({ modelo, calc, ajustes, onEdit }) {
  const [abertos, setAbertos] = useState({});
  const alterna = (id) => setAbertos((a) => ({ ...a, [id]: !a[id] }));
  const cols = calc.periodos;

  const linhaTotal = (rotulo, valores, cls = "", total = true) => (
    <tr className={`orc-tr-total ${cls}`}>
      <th scope="row">{rotulo}</th>
      {cols.map((p) => (
        <td key={p} className={valores[p] < 0 ? "neg" : ""}>{num0(valores[p])}</td>
      ))}
      <td className={`orc-sum ${total ? "" : "dim"}`}>{total ? num0(cols.reduce((s, p) => s + valores[p], 0)) : ""}</td>
    </tr>
  );

  const grupoRows = (g, secao) => {
    const aberto = abertos[g.id];
    const rows = [
      <tr key={g.id} className="orc-tr-grupo" onClick={() => alterna(g.id)}>
        <th scope="row">
          <button type="button" className="orc-grupo-btn" aria-expanded={!!aberto}>
            {aberto ? "▾" : "▸"} {g.nome} <small>({g.linhas.length})</small>
          </button>
        </th>
        {cols.map((p) => <td key={p}>{num0(calc.grupoTotais[g.id][p])}</td>)}
        <td className="orc-sum">{num0(cols.reduce((s, p) => s + calc.grupoTotais[g.id][p], 0))}</td>
      </tr>,
    ];
    if (aberto) {
      const ordenadas = [...g.linhas].sort(
        (a, b) => cols.reduce((s, p) => s + valorEfetivo(b, p, ajustes), 0) - cols.reduce((s, p) => s + valorEfetivo(a, p, ajustes), 0)
      );
      for (const l of ordenadas) {
        const tot = cols.reduce((s, p) => s + valorEfetivo(l, p, ajustes), 0);
        rows.push(
          <tr key={l.id} className="orc-tr-linha">
            <th scope="row" title={l.motivo_nao_projetar || l.nota || l.nome}>{l.nome}</th>
            {cols.map((p) => (
              <td key={p} className={calc.statusDe[p] === "real" ? "" : "proj"}>
                <Celula linha={l} period={p} ajustes={ajustes} editavel={calc.statusDe[p] !== "real"} onEdit={onEdit} />
              </td>
            ))}
            <td className="orc-sum">{num0(tot)}</td>
          </tr>
        );
      }
    }
    return rows;
  };

  const ser = (campo) => Object.fromEntries(calc.meses.map((m) => [m.period, m[campo]]));

  return (
    <div className="orc-grid-wrap">
      <div className="orc-nota">Clique no nome de um grupo para abrir as contas. Células dos meses projetados são editáveis (valores em R$).</div>
      <div className="orc-table-wrap">
        <table className="orc-grade">
          <thead>
            <tr>
              <th>Conta</th>
              {cols.map((p) => (
                <th key={p} className={calc.statusDe[p] === "real" ? "" : "proj"}>
                  {mesCurto(p)}
                  <small>{calc.statusDe[p] === "real" ? "real" : "proj."}</small>
                </th>
              ))}
              <th>Ano</th>
            </tr>
          </thead>
          <tbody>
            <tr className="orc-tr-secao"><th colSpan={cols.length + 2}>RECEITAS</th></tr>
            {modelo.receitas.grupos.flatMap((g) => grupoRows(g, "receitas"))}
            {calc.ano.ajuste > 0 && linhaTotal("▲ Ajuste de receita (meta de venda)", ser("ajuste"), "ajuste")}
            {linhaTotal("Receita total", ser("receitaTotal"))}
            <tr className="orc-tr-secao"><th colSpan={cols.length + 2}>DESPESAS</th></tr>
            {modelo.despesas.grupos.flatMap((g) => grupoRows(g, "despesas"))}
            {linhaTotal(`Impostos (${String(calc.aliquota).replace(".", ",")}%)`, ser("impostos"))}
            {linhaTotal("Total de saídas", ser("saidas"))}
            {linhaTotal("RESULTADO", ser("resultado"), "resultado")}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- aba: detalhamento por conta contábil
function Detalhamento({ modelo, calc, ajustes }) {
  const [abertos, setAbertos] = useState({});
  const [ordem, setOrdem] = useState("valor");

  const tabela = (secao, titulo, ehReceita) => (
    <div className="orc-table-wrap">
      <table className="orc-detalhe">
        <thead>
          <tr>
            <th>{titulo}</th>
            <th>Previsto no ano</th>
            <th>Realizado ({calc.nReais} {calc.nReais === 1 ? "mês" : "meses"})</th>
            <th>A realizar</th>
            <th>{ehReceita ? "Atingido" : "Consumo"}</th>
            <th>Variação vs ritmo</th>
          </tr>
        </thead>
        <tbody>
          {modelo[secao].grupos.map((g) => {
            const linhas = g.linhas.map((l) => ({ l, st: estatLinha(calc.valoresLinha[l.id], calc.periodos, calc.statusDe) }));
            linhas.sort((a, b) => (ordem === "valor" ? Math.max(b.st.previsto, b.st.realizado) - Math.max(a.st.previsto, a.st.realizado) : a.l.nome.localeCompare(b.l.nome, "pt-BR")));
            const tot = estatLinha(calc.grupoTotais[g.id], calc.periodos, calc.statusDe);
            const aberto = abertos[g.id];
            return [
              <tr key={g.id} className="orc-tr-grupo" onClick={() => setAbertos((a) => ({ ...a, [g.id]: !a[g.id] }))}>
                <td><button type="button" className="orc-grupo-btn" aria-expanded={!!aberto}>{aberto ? "▾" : "▸"} {g.nome} <small>({g.linhas.length})</small></button></td>
                <td>{fmtMoeda(tot.previsto)}</td>
                <td>{fmtMoeda(tot.realizado)}</td>
                <td>{fmtMoeda(tot.aRealizar)}</td>
                <td>{tot.consumoPct === null ? "—" : fmtPct(tot.consumoPct)}</td>
                <td><Variacao st={tot} ehReceita={ehReceita} /></td>
              </tr>,
              ...(aberto
                ? linhas
                    .filter(({ st }) => Math.abs(st.previsto) > 0.005 || Math.abs(st.realizado) > 0.005)
                    .map(({ l, st }) => (
                      <tr key={l.id} className="orc-tr-linha">
                        <td title={l.motivo_nao_projetar || l.nota || l.nome}>{l.nome}</td>
                        <td>{fmtMoeda(st.previsto)}</td>
                        <td>{fmtMoeda(st.realizado)}</td>
                        <td>{fmtMoeda(st.aRealizar)}</td>
                        <td>{st.consumoPct === null ? (st.realizado > 0 ? "sem orçamento" : "—") : fmtPct(st.consumoPct)}</td>
                        <td><Variacao st={st} ehReceita={ehReceita} /></td>
                      </tr>
                    ))
                : []),
            ];
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div>
      <div className="orc-nota">
        “Previsto” é o orçamento de 12 meses (meses fechados = fato; demais = projeção/ajustes). “Variação vs ritmo” compara o realizado com
        o previsto proporcional aos meses já fechados ({calc.nReais}/12).{" "}
        <button type="button" className="orc-link" onClick={() => setOrdem(ordem === "valor" ? "nome" : "valor")}>
          Ordenar por {ordem === "valor" ? "nome" : "valor"}
        </button>
      </div>
      {tabela("receitas", "Receitas", true)}
      <div style={{ height: 16 }} />
      {tabela("despesas", "Despesas por conta contábil", false)}
    </div>
  );
}

function Variacao({ st, ehReceita }) {
  if (st.esperadoAteAgora <= 0 && Math.abs(st.realizado) < 0.005) return <span className="dim">—</span>;
  const acima = st.variacao > 0.5;
  const abaixo = st.variacao < -0.5;
  const bom = ehReceita ? acima : abaixo;
  const ruim = ehReceita ? abaixo : acima;
  if (!acima && !abaixo) return <span className="dim">• no ritmo</span>;
  const icone = acima ? "▲" : "▼";
  return (
    <span className={bom ? "pos" : ruim ? "neg" : "dim"}>
      {icone} {fmtMoeda(Math.abs(st.variacao))}
      {st.variacaoPct !== null ? ` (${st.variacao >= 0 ? "+" : "−"}${fmtPct(Math.abs(st.variacaoPct))})` : ""}
    </span>
  );
}

// ---------------------------------------------------------------- aba: clientes fiéis
function Clientes({ modelo }) {
  const rec = modelo.recorrencia;
  const linha = (c) => (
    <tr key={c.nome}>
      <td>{c.nome}</td>
      <td>{c.meses_ativos}/{c.meses_medidos}</td>
      <td>{fmtMoeda(c.media_mensal)}</td>
      <td>{fmtMoeda(c.minimo)} – {fmtMoeda(c.maximo)}</td>
      <td>{c.variabilidade_cv <= 0.25 ? "Estável" : c.variabilidade_cv <= 0.5 ? "Moderada" : "Oscila bastante"} ({c.variabilidade_cv.toLocaleString("pt-BR")})</td>
    </tr>
  );
  return (
    <div>
      <div className="orc-nota">
        {rec.criterio} Fonte: {rec.fonte}
      </div>
      <div className="orc-table-wrap">
        <table className="orc-detalhe">
          <thead>
            <tr><th>Cliente privado fiel (sem contrato formal)</th><th>Meses faturados</th><th>Média/mês</th><th>Faixa</th><th>Estabilidade</th></tr>
          </thead>
          <tbody>{rec.recorrentes.map(linha)}</tbody>
        </table>
      </div>
      {rec.intermitentes.length > 0 && (
        <>
          <div className="section-title">Faturam com frequência, mas de forma intermitente (entram na linha “Demais receitas”)</div>
          <div className="orc-table-wrap">
            <table className="orc-detalhe">
              <thead>
                <tr><th>Cliente</th><th>Meses faturados</th><th>Média/mês</th><th>Faixa</th><th>Estabilidade</th></tr>
              </thead>
              <tbody>{rec.intermitentes.map(linha)}</tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- página
const ABAS = [
  { id: "mes", rotulo: "Mês a mês" },
  { id: "ano", rotulo: "Grade do ano" },
  { id: "conta", rotulo: "Detalhamento por conta" },
  { id: "clientes", rotulo: "Clientes fiéis" },
];

export default function Orcamento({ d }) {
  const modelo = d.modelo_dre;
  const [salvo, setSalvo] = useState({ ajustes: {}, parametros: {}, created_at: null, nota: null });
  const [carregado, setCarregado] = useState(false);
  const [erroLeitura, setErroLeitura] = useState(null);
  const [exigePin, setExigePin] = useState(false);
  const [ajustes, setAjustes] = useState({});
  const [params, setParams] = useState({});
  const [aba, setAba] = useState("mes");
  const proximoProjetado = modelo.meses.find((m) => m.status !== "real")?.period || modelo.meses[0].period;
  const [mes, setMes] = useState(proximoProjetado);
  const [pin, setPin] = useState("");
  const [nota, setNota] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetchAjustesOrcamento()
      .then((r) => {
        setSalvo(r);
        setAjustes(r.ajustes || {});
        setParams(r.parametros || {});
        setExigePin(Boolean(r.exige_pin));
      })
      .catch((e) => setErroLeitura(e.message))
      .finally(() => setCarregado(true));
  }, []);

  const calc = useMemo(() => calcular(modelo, ajustes, params), [modelo, ajustes, params]);
  const calcBase = useMemo(() => calcular(modelo, {}, {}), [modelo]);

  const itensDespesa = useMemo(
    () =>
      modelo.despesas.grupos.flatMap((g) =>
        g.linhas.map((l) => ({
          id: l.id,
          nome: l.nome,
          grupoId: g.id,
          stat: estatLinha(calc.valoresLinha[l.id], calc.periodos, calc.statusDe),
          reais: calc.periodos.filter((p) => calc.statusDe[p] === "real").map((p) => calc.valoresLinha[l.id][p]),
        }))
      ),
    [modelo, calc]
  );

  const sujo = !iguais(ajustes, salvo.ajustes || {}) || !iguais(params, salvo.parametros || {});
  const nAjustes = contarAjustes(ajustes);
  const meta = modelo.parametros.meta_mensal_comercial;

  const aoEditar = (linha, period, valor) => {
    setMsg(null);
    setAjustes((a) => aplicarEdicao(a, linha, period, valor));
  };

  const aoMudarParam = (chave, texto) => {
    setMsg(null);
    const v = parseValor(texto);
    setParams((p) => {
      const novo = { ...p };
      const padrao = modelo.parametros[chave];
      if (v === null || v < 0 || v > 100 || Math.abs(v - padrao) < 1e-9) delete novo[chave];
      else novo[chave] = v;
      return novo;
    });
  };

  const descartar = () => {
    setAjustes(salvo.ajustes || {});
    setParams(salvo.parametros || {});
    setMsg(null);
  };

  const salvar = async () => {
    setSalvando(true);
    setMsg(null);
    try {
      const r = await salvarAjustesOrcamento({ ajustes, parametros: params, nota, pin });
      setSalvo({ ...salvo, ajustes, parametros: params, created_at: r.created_at, nota });
      setNota("");
      setMsg({ tipo: "success", texto: "Salvo. O Claude consegue ler esses ajustes — é só pedir “leia os ajustes do orçamento”." });
    } catch (e) {
      setMsg({ tipo: "error", texto: e.message });
    } finally {
      setSalvando(false);
    }
  };

  const listaAjustes = useMemo(() => {
    const porId = {};
    for (const sec of ["receitas", "despesas"]) for (const g of modelo[sec].grupos) for (const l of g.linhas) porId[l.id] = l;
    const out = [];
    for (const [id, meses] of Object.entries(ajustes)) {
      for (const [p, v] of Object.entries(meses)) {
        const l = porId[id];
        out.push({ chave: `${id}|${p}`, nome: l ? l.nome : id, mes: p, de: l ? l.base[p] ?? 0 : 0, para: v });
      }
    }
    return out;
  }, [ajustes, modelo]);

  const ritmo = calc.nReais / calc.periodos.length;
  const rotuloAno = `${modelo.ano}`;
  const ultimoReal = modelo.ultimo_mes_real ? mesCurto(modelo.ultimo_mes_real) : "";
  const piorMesProj = calc.meses.filter((m) => !m.real).reduce((p, m) => (m.resultado < p.resultado ? m : p), calc.meses.find((m) => !m.real) || calc.meses[0]);
  const todosProjPositivos = calc.meses.filter((m) => !m.real).every((m) => m.resultado > 0);

  return (
    <div className="orc">
      <div className="orc-topline">
        <span className="badge ok">Real até {ultimoReal}/{rotuloAno}</span>
        <span className="badge empty">Projeção {mesCurto(proximoProjetado)}–dez editável</span>
        {salvo.created_at ? (
          <span className="orc-salvo">Último ajuste salvo em {fmtData(salvo.created_at)}</span>
        ) : carregado ? (
          <span className="orc-salvo">Nenhum ajuste salvo ainda — valores originais do modelo</span>
        ) : null}
      </div>

      {erroLeitura && (
        <div className="aviso">Não consegui ler os ajustes salvos ({erroLeitura}). Você pode simular, mas só vai conseguir salvar quando o backend responder.</div>
      )}

      <div className="grid">
        <KpiCard
          label={`Receita prevista ${rotuloAno}`}
          value={fmtMoeda(calc.ano.receita)}
          color="cyan"
          meta={`Real ${mesCurto(modelo.meses[0].period)}–${ultimoReal}: ${fmtMoeda(calc.ytd.receita)}${calc.ano.ajuste > 0 ? ` · inclui ${fmtMoeda(calc.ano.ajuste)} de meta de venda adicional` : ""}`}
        />
        <KpiCard
          label="Despesas + impostos previstos"
          value={fmtMoeda(calc.ano.despesas + calc.ano.impostos)}
          color="amber"
          meta={`Realizado até ${ultimoReal}: ${fmtMoeda(calc.ytd.despesas + calc.ytd.impostos)} (${fmtPct(100 * (calc.ytd.despesas + calc.ytd.impostos) / (calc.ano.despesas + calc.ano.impostos || 1))} do orçamento; ritmo esperado ${fmtPct(100 * ritmo)})`}
        />
        <KpiCard
          label="Resultado previsto no ano"
          value={fmtMoeda(calc.ano.resultado)}
          color={calc.ano.resultado < 0 ? "red" : "emerald"}
          meta={`Margem ${calc.ano.margemPct === null ? "—" : fmtPct(calc.ano.margemPct)} · acumulado real: ${fmtMoeda(calc.ytd.resultado)}`}
        />
        <KpiCard
          label={`Meses projetados fecham positivos`}
          value={todosProjPositivos ? "✔ Sim" : "▼ Não"}
          color={todosProjPositivos ? "emerald" : "red"}
          meta={`Pior mês projetado: ${mesCurto(piorMesProj.period)} com ${fmtMoeda(piorMesProj.resultado)} (margem mínima ${String(calc.margem).replace(".", ",")}% sobre a despesa)`}
        />
      </div>

      <div className="orc-regras">
        <div className="orc-regras-txt">
          <b>Regra de fechamento positivo.</b> Em cada mês projetado, se a receita prevista não cobre as despesas, os impostos e a margem mínima, a receita é elevada
          automaticamente (linha “Ajuste de receita”). Hoje isso soma {fmtMoeda(calc.ano.ajuste)} no ano
          {calcBase.ano.ajuste !== calc.ano.ajuste ? ` (era ${fmtMoeda(calcBase.ano.ajuste)} antes das suas alterações)` : ""}.
        </div>
        <label>
          Margem mínima sobre a despesa (%)
          <ParamInput valor={calc.margem} onChange={(t) => aoMudarParam("margem_minima_sobre_despesa_pct", t)} />
        </label>
        <label>
          Alíquota de impostos (%)
          <ParamInput valor={calc.aliquota} onChange={(t) => aoMudarParam("aliquota_imposto_pct", t)} />
        </label>
      </div>

      <div className="orc-charts">
        <GraficoMensal
          meses={calc.meses}
          meta={meta}
          mesAtivo={aba === "mes" ? mes : null}
          onSelecionar={(p) => {
            setMes(p);
            setAba("mes");
          }}
        />
        <ConsumoPorConta
          itens={itensDespesa}
          ritmoPct={100 * ritmo}
          grupos={modelo.despesas.grupos.map((g) => ({ id: g.id, nome: g.nome }))}
        />
      </div>

      <div className="orc-tabs" role="tablist">
        {ABAS.map((a) => (
          <button key={a.id} type="button" role="tab" aria-selected={aba === a.id} className={`orc-tab ${aba === a.id ? "on" : ""}`} onClick={() => setAba(a.id)}>
            {a.rotulo}
          </button>
        ))}
      </div>

      <div className="orc-painel">
        {aba === "mes" && <MesAMes modelo={modelo} calc={calc} ajustes={ajustes} onEdit={aoEditar} mes={mes} setMes={setMes} meta={meta} />}
        {aba === "ano" && <GradeAno modelo={modelo} calc={calc} ajustes={ajustes} onEdit={aoEditar} />}
        {aba === "conta" && <Detalhamento modelo={modelo} calc={calc} ajustes={ajustes} />}
        {aba === "clientes" && <Clientes modelo={modelo} />}
      </div>

      {d.cenario_20pct_sobre_ponto_equilibrio && (
        <div className="orc-nota orc-ref">
          Referência da diretoria: ponto de equilíbrio seguro de {fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.ponto_equilibrio_seguro_usado)}/mês + 20% ={" "}
          {fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.receita_projetada)} de receita mensal (lucro de referência {fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.lucro_projetado)}).
          O orçamento acima é construído conta a conta; essa referência não é usada nos cálculos.
        </div>
      )}

      <details className="explicacoes">
        <summary>Como o orçamento é construído</summary>
        {modelo.metodologia.map((t, i) => (
          <div className="explicacoes-item" key={i}>
            <p>{t}</p>
          </div>
        ))}
        <div className="explicacoes-item">
          <p>{d.aviso}</p>
        </div>
      </details>

      {(sujo || msg) && (
        <div className="orc-savebar" role="region" aria-label="Salvar alterações do orçamento">
          <div className="orc-savebar-main">
            <div>
              {sujo ? (
                <b>{nAjustes} {nAjustes === 1 ? "célula alterada" : "células alteradas"}{Object.keys(params).length ? ` + ${Object.keys(params).length} regra(s)` : ""} — ainda não salvo</b>
              ) : null}
              {msg && <div className={`status-msg ${msg.tipo}`}>{msg.texto}</div>}
            </div>
            {sujo && (
              <div className="orc-savebar-actions">
                <input className="orc-nota-in" placeholder="Motivo do ajuste (opcional)" maxLength={500} value={nota} onChange={(e) => setNota(e.target.value)} />
                {exigePin && (
                  <input className="orc-pin" type="password" inputMode="numeric" placeholder="PIN de edição" value={pin} onChange={(e) => setPin(e.target.value)} autoComplete="off" />
                )}
                <button type="button" className="btn secondary" onClick={descartar} disabled={salvando}>Descartar</button>
                <button type="button" className="btn" onClick={salvar} disabled={salvando || (exigePin && !pin)}>{salvando ? "Salvando…" : "Salvar ajustes"}</button>
              </div>
            )}
          </div>
          {sujo && listaAjustes.length > 0 && (
            <details className="orc-ajustes-lista">
              <summary>Ver o que mudou</summary>
              <ul>
                {listaAjustes.slice(0, 40).map((a) => (
                  <li key={a.chave}>
                    {a.nome} · {mesCurto(a.mes)}: {fmtMoeda(a.de)} → <b>{fmtMoeda(a.para)}</b>
                  </li>
                ))}
                {listaAjustes.length > 40 && <li>… e mais {listaAjustes.length - 40}</li>}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
