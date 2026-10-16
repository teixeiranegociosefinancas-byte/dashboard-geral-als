import { useEffect, useMemo, useRef, useState } from "react";
import { fmtMoeda, fmtPct } from "../format.js";
import { mesCurto, statusConsumo } from "./model.js";

// Paleta validada (dataviz skill, modo escuro, superfície #16223b): receita
// #3987e5 × despesa #d95926 — ΔE 31,8 visão normal / 26,8 protanopia, contraste ≥ 3:1.
export const COR_RECEITA = "#3987e5";
export const COR_DESPESA = "#d95926";

function useLargura(ref, padrao = 720) {
  const [w, setW] = useState(padrao);
  useEffect(() => {
    if (!ref.current) return undefined;
    const ro = new ResizeObserver((entries) => {
      const nova = Math.floor(entries[0].contentRect.width);
      if (nova > 0) setW(nova);
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

const mil = (v) => {
  const abs = Math.abs(v);
  const s = abs >= 1_000_000 ? `${(abs / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi` : `${Math.round(abs / 1000)} mil`;
  return `${v < 0 ? "−" : ""}R$ ${s}`;
};

function escalaEixo(min, max, alvo = 5) {
  const faixa = Math.max(max - min, 1);
  const bruto = faixa / alvo;
  const pot = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((f) => f * pot).find((p) => p >= bruto) || pot * 10;
  const lo = Math.floor(min / passo) * passo;
  const hi = Math.ceil(max / passo) * passo;
  const ticks = [];
  for (let v = lo; v <= hi + 1e-6; v += passo) ticks.push(Math.round(v));
  return { lo, hi, ticks };
}

// Receita × (despesas + impostos) por mês, com o resultado em linha e a meta
// mensal tracejada. Meses projetados = listrados. Um eixo só (R$).
export function GraficoMensal({ meses, meta, mesAtivo, onSelecionar }) {
  const caixa = useRef(null);
  const largura = useLargura(caixa);
  const [hover, setHover] = useState(null);
  const [tabela, setTabela] = useState(false);

  const alt = 320;
  const mg = { t: 16, r: 16, b: 30, l: 64 };
  const iw = Math.max(largura - mg.l - mg.r, 200);
  const ih = alt - mg.t - mg.b;

  const { lo, hi, ticks } = useMemo(() => {
    const valores = meses.flatMap((m) => [m.receitaTotal, m.saidas, m.resultado, meta || 0, 0]);
    return escalaEixo(Math.min(...valores), Math.max(...valores));
  }, [meses, meta]);

  const y = (v) => mg.t + ih - ((v - lo) / (hi - lo)) * ih;
  const passoX = iw / meses.length;
  const largBarra = Math.max(Math.min(passoX * 0.28, 18), 6);
  const cx = (i) => mg.l + passoX * i + passoX / 2;

  const pontosResultado = meses.map((m, i) => `${cx(i)},${y(m.resultado)}`).join(" ");
  const tip = hover !== null ? meses[hover] : null;

  return (
    <div className="orc-chart-card">
      <div className="orc-chart-head">
        <div>
          <div className="orc-chart-title">Receita, despesas e resultado por mês</div>
          <div className="orc-chart-sub">Despesas incluem impostos. Colunas listradas = projeção (editável).</div>
        </div>
        <button type="button" className="btn secondary orc-mini-btn" onClick={() => setTabela((t) => !t)}>
          {tabela ? "Ver gráfico" : "Ver como tabela"}
        </button>
      </div>

      <div className="orc-legend" aria-label="Legenda">
        <span><i className="orc-sw" style={{ background: COR_RECEITA }} /> Receita</span>
        <span><i className="orc-sw" style={{ background: COR_DESPESA }} /> Despesas + impostos</span>
        <span><i className="orc-sw orc-sw-line" /> Resultado</span>
        {meta ? <span><i className="orc-sw orc-sw-dash" /> Meta mensal {mil(meta)}</span> : null}
      </div>

      {tabela ? (
        <div className="orc-table-wrap">
          <table className="orc-table">
            <thead>
              <tr>
                <th>Mês</th><th>Situação</th><th>Receita</th><th>Desp. + impostos</th><th>Resultado</th><th>Margem</th>
              </tr>
            </thead>
            <tbody>
              {meses.map((m) => (
                <tr key={m.period}>
                  <td>{mesCurto(m.period)}</td>
                  <td>{m.real ? "Real" : "Projetado"}</td>
                  <td>{fmtMoeda(m.receitaTotal)}</td>
                  <td>{fmtMoeda(m.saidas)}</td>
                  <td className={m.resultado < 0 ? "neg" : ""}>{fmtMoeda(m.resultado)}</td>
                  <td>{m.margemPct === null ? "—" : fmtPct(m.margemPct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="orc-chart-box" ref={caixa}>
          <svg width={largura} height={alt} role="img" aria-label="Receita, despesas e resultado mensais do orçamento 2026">
            <defs>
              <pattern id="orc-hatch-r" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" fill={COR_RECEITA} fillOpacity="0.28" />
                <rect width="2.5" height="6" fill={COR_RECEITA} />
              </pattern>
              <pattern id="orc-hatch-d" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" fill={COR_DESPESA} fillOpacity="0.28" />
                <rect width="2.5" height="6" fill={COR_DESPESA} />
              </pattern>
            </defs>

            {ticks.map((t) => (
              <g key={t}>
                <line x1={mg.l} x2={mg.l + iw} y1={y(t)} y2={y(t)} className={t === 0 ? "orc-axis0" : "orc-grid"} />
                <text x={mg.l - 8} y={y(t) + 4} textAnchor="end" className="orc-tick">{mil(t)}</text>
              </g>
            ))}

            {meta ? (
              <line x1={mg.l} x2={mg.l + iw} y1={y(meta)} y2={y(meta)} className="orc-meta" />
            ) : null}

            {meses.map((m, i) => {
              const x0 = cx(i);
              const ativo = mesAtivo === m.period || hover === i;
              const barra = (v, x, cor, id) => {
                const topo = Math.min(y(v), y(0));
                const h = Math.abs(y(v) - y(0));
                if (h < 0.5) return null;
                const r = Math.min(4, h / 2, largBarra / 2);
                const neg = v < 0;
                // cantos arredondados só na ponta de dados, ancorada na linha-base
                const d = neg
                  ? `M${x},${topo} h${largBarra} v${h - r} a${r},${r} 0 0 1 ${-r},${r} h${-(largBarra - 2 * r)} a${r},${r} 0 0 1 ${-r},${-r} z`
                  : `M${x},${topo + h} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${largBarra - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`;
                return <path d={d} fill={m.real ? cor : `url(#${id})`} opacity={ativo || (hover === null && !mesAtivo) ? 1 : 0.55} />;
              };
              return (
                <g key={m.period}>
                  {ativo ? <rect x={mg.l + passoX * i} y={mg.t} width={passoX} height={ih} className="orc-hl" /> : null}
                  {barra(m.receitaTotal, x0 - largBarra - 1, COR_RECEITA, "orc-hatch-r")}
                  {barra(m.saidas, x0 + 1, COR_DESPESA, "orc-hatch-d")}
                  <text x={x0} y={alt - 10} textAnchor="middle" className={`orc-tick ${mesAtivo === m.period ? "orc-tick-ativo" : ""}`}>
                    {mesCurto(m.period)}
                  </text>
                </g>
              );
            })}

            <polyline points={pontosResultado} className="orc-line" fill="none" />
            {meses.map((m, i) => (
              <circle key={m.period} cx={cx(i)} cy={y(m.resultado)} r={4} className={`orc-dot ${m.resultado < 0 ? "orc-dot-neg" : ""}`} />
            ))}

            {meses.map((m, i) => (
              <rect
                key={`hit-${m.period}`}
                x={mg.l + passoX * i}
                y={mg.t}
                width={passoX}
                height={ih + mg.b}
                fill="transparent"
                style={{ cursor: onSelecionar ? "pointer" : "default" }}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onClick={() => onSelecionar && onSelecionar(m.period)}
              />
            ))}
          </svg>

          {tip ? (
            <div className="orc-tooltip" style={{ left: Math.min(Math.max(cx(hover) + 12, 8), largura - 230), top: 12 }}>
              <div className="orc-tip-title">
                {mesCurto(tip.period)}/{tip.period.slice(0, 4)} · {tip.real ? "Real" : "Projetado"}
              </div>
              <div className="orc-tip-row"><span><i className="orc-sw" style={{ background: COR_RECEITA }} /> Receita</span><b>{fmtMoeda(tip.receitaTotal)}</b></div>
              {tip.ajuste > 0 ? (
                <div className="orc-tip-row orc-tip-sub"><span>inclui ajuste p/ fechar positivo</span><b>{fmtMoeda(tip.ajuste)}</b></div>
              ) : null}
              <div className="orc-tip-row"><span>Impostos</span><b>{fmtMoeda(tip.impostos)}</b></div>
              <div className="orc-tip-row"><span><i className="orc-sw" style={{ background: COR_DESPESA }} /> Despesas</span><b>{fmtMoeda(tip.despesas)}</b></div>
              <div className="orc-tip-row orc-tip-total"><span>Resultado</span><b className={tip.resultado < 0 ? "neg" : "pos"}>{tip.resultado < 0 ? "▼ " : "▲ "}{fmtMoeda(tip.resultado)}</b></div>
              {meta ? <div className="orc-tip-row orc-tip-sub"><span>Receita vs meta</span><b>{tip.receitaTotal >= meta ? "+" : "−"}{fmtMoeda(Math.abs(tip.receitaTotal - meta))}</b></div> : null}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

// Contas contábeis: quanto já foi realizado e quanto ainda está previsto até
// dezembro (barra empilhada, mesma escala para todas), com a oscilação mensal
// da conta (porque as contas variam bastante) e alerta só quando o realizado
// foge do ritmo do orçamento.
function oscilacao(reais) {
  const v = reais.filter((x) => x !== undefined);
  const media = v.reduce((s, x) => s + x, 0) / (v.length || 1);
  if (v.length < 2 || media <= 0) return { chave: "n/a", icone: "–", rotulo: "Sem histórico", cv: null };
  const dp = Math.sqrt(v.reduce((s, x) => s + (x - media) ** 2, 0) / v.length);
  const cv = dp / media;
  if (cv <= 0.25) return { chave: "est", icone: "=", rotulo: "Estável", cv };
  if (cv <= 0.6) return { chave: "var", icone: "≈", rotulo: "Variável", cv };
  return { chave: "mvar", icone: "↯", rotulo: "Muito variável", cv };
}

export function ConsumoPorConta({ itens, ritmoPct, grupos, limiteInicial = 10 }) {
  const [grupo, setGrupo] = useState("todos");
  const [todos, setTodos] = useState(false);
  const lista = itens
    .filter((i) => grupo === "todos" || i.grupoId === grupo)
    .filter((i) => i.stat.previsto > 0 || i.stat.realizado > 0)
    .sort((a, b) => Math.max(b.stat.previsto, b.stat.realizado) - Math.max(a.stat.previsto, a.stat.realizado));
  const visiveis = todos ? lista : lista.slice(0, limiteInicial);
  const escala = Math.max(1, ...visiveis.map((i) => Math.max(i.stat.previsto, i.stat.realizado)));

  return (
    <div className="orc-chart-card">
      <div className="orc-chart-head">
        <div>
          <div className="orc-chart-title">Despesas por conta contábil</div>
          <div className="orc-chart-sub">
            Sólido = já realizado · listrado = ainda previsto até dezembro. O alerta de ritmo só aparece quando o realizado foge do
            orçado (esperado hoje: {fmtPct(ritmoPct)} do ano).
          </div>
        </div>
      </div>

      <div className="orc-chips" aria-label="Filtrar por grupo de contas">
        <button type="button" className={`orc-chip ${grupo === "todos" ? "on" : ""}`} onClick={() => setGrupo("todos")}>Todas</button>
        {grupos.map((g) => (
          <button key={g.id} type="button" className={`orc-chip ${grupo === g.id ? "on" : ""}`} onClick={() => setGrupo(g.id)}>
            {g.nome}
          </button>
        ))}
      </div>

      <div className="orc-bars">
        {visiveis.map((i) => {
          const st = statusConsumo(i.stat);
          const osc = oscilacao(i.reais || []);
          const wReal = (100 * i.stat.realizado) / escala;
          const wResto = (100 * Math.max(i.stat.aRealizar, 0)) / escala;
          const alerta = st.chave === "atencao" || st.chave === "acima" || st.chave === "sem";
          return (
            <div
              key={i.id}
              className="orc-bar-row"
              title={`${i.nome}\nPrevisto no ano: ${fmtMoeda(i.stat.previsto)}\nRealizado: ${fmtMoeda(i.stat.realizado)}\nA realizar: ${fmtMoeda(i.stat.aRealizar)}${osc.cv !== null ? `\nOscilação mensal (CV): ${osc.cv.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}` : ""}`}
            >
              <div className="orc-bar-name">{i.nome}</div>
              <div className="orc-bar-track" role="img" aria-label={`${i.nome}: realizado ${fmtMoeda(i.stat.realizado)}, a realizar ${fmtMoeda(i.stat.aRealizar)}`}>
                <div className="orc-bar-fill" style={{ width: `${wReal}%` }} />
                <div className="orc-bar-rest" style={{ left: `${wReal}%`, width: `${wResto}%` }} />
              </div>
              <div className="orc-bar-val">
                {fmtMoeda(i.stat.realizado)} <span className="dim">+ {fmtMoeda(i.stat.aRealizar)} a realizar</span>
                <b> = {fmtMoeda(i.stat.previsto)}</b>
              </div>
              <div className="orc-bar-tags">
                <span className={`orc-osc o-${osc.chave}`}><span aria-hidden="true">{osc.icone}</span> {osc.rotulo}</span>
                {alerta && <span className={`orc-status s-${st.chave}`}><span aria-hidden="true">{st.icone}</span> {st.rotulo}</span>}
              </div>
            </div>
          );
        })}
        {!lista.length && <div className="empty-state">Nenhuma conta nesse grupo.</div>}
      </div>
      {lista.length > limiteInicial && (
        <button type="button" className="orc-mini-btn btn secondary" onClick={() => setTodos((t) => !t)}>
          {todos ? "Mostrar só as maiores" : `Ver todas as ${lista.length} contas`}
        </button>
      )}
    </div>
  );
}
