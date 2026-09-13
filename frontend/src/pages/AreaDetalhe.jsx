import { useEffect, useState } from "react";
import { fetchLatest } from "../api.js";
import { areaLabel } from "../areas.js";
import { fmtMoeda, fmtNumero, fmtPct, fmtData } from "../format.js";

function DetalheComercial({ d }) {
  const servicos = Object.entries(d.por_servico || {});
  const vendedores = Object.entries(d.por_vendedor || {});
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">Faturamento total</div>
          <div className="card-value cyan">{fmtMoeda(d.faturamento_total)}</div>
        </div>
        <div className="card">
          <div className="card-label">Meta total</div>
          <div className="card-value cyan">{fmtMoeda(d.meta_total)}</div>
        </div>
        <div className="card">
          <div className="card-label">Atingimento</div>
          <div className="card-value cyan">{d.atingimento_pct !== null ? fmtPct(d.atingimento_pct) : "—"}</div>
        </div>
      </div>

      <div className="section-title">
        Faturamento por serviço
        {d.periodo_servico && <span style={{ fontWeight: 400, fontSize: "0.85em", opacity: 0.7 }}> · período: {d.periodo_servico}</span>}
      </div>
      <table>
        <thead>
          <tr><th>Serviço</th><th>Faturamento</th></tr>
        </thead>
        <tbody>
          {servicos.map(([nome, valor]) => (
            <tr key={nome}><td>{nome}</td><td>{fmtMoeda(valor)}</td></tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">
        Faturamento por vendedor
        {d.periodo_vendedor && <span style={{ fontWeight: 400, fontSize: "0.85em", opacity: 0.7 }}> · período: {d.periodo_vendedor}</span>}
      </div>
      <table>
        <thead>
          <tr>
            <th>Vendedor</th><th>Faturamento total</th><th>Status</th>
            <th>Mês ref.</th><th>Faturamento no mês</th><th>Falta p/ próxima faixa</th>
          </tr>
        </thead>
        <tbody>
          {vendedores.map(([nome, v]) => {
            const pm = v.progresso_meta;
            const statusLabel = {
              nao_recebe_comissao: "não recebe comissão",
              ex_vendedor: "ex-vendedor(a)",
              ativo: "—",
            }[v.status || "ativo"];
            return (
              <tr key={nome}>
                <td>{nome}</td>
                <td>{fmtMoeda(v.faturamento)}</td>
                <td>{statusLabel === "—" ? "—" : <span className="badge">{statusLabel}</span>}</td>
                <td>{pm ? pm.mes_referencia : "—"}</td>
                <td>{pm ? fmtMoeda(pm.faturamento_mes) : "—"}</td>
                <td>
                  {!pm
                    ? "—"
                    : pm.proxima_faixa_limite === null
                    ? "Faixa máxima (80 mil+)"
                    : `${fmtMoeda(pm.falta_valor)} (${fmtPct(pm.falta_pct)}) p/ ${fmtMoeda(pm.proxima_faixa_limite)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="page-subtitle" style={{ marginTop: "0.5rem" }}>
        Faixas de referência: até 20 mil, 20-50 mil, 50-80 mil, 80 mil+ (por mês). Alex Santos, Silas Teixeira e
        Licitações não participam da comissão por faixa.
      </p>
    </>
  );
}

function DetalheFrota({ d }) {
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">Km/litro da frota</div>
          <div className="card-value amber">{d.km_por_litro_frota !== null ? `${fmtNumero(d.km_por_litro_frota, 2)} km/L` : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">Total de litros</div>
          <div className="card-value amber">{fmtNumero(d.total_litros, 0)} L</div>
        </div>
        <div className="card">
          <div className="card-label">Veículos</div>
          <div className="card-value amber">{fmtNumero(d.total_veiculos)}</div>
        </div>
        <div className="card">
          <div className="card-label">Valor gasto (combustível)</div>
          <div className="card-value amber">{d.valor_gasto_total !== null && d.valor_gasto_total !== undefined ? fmtMoeda(d.valor_gasto_total) : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">Preço médio por litro</div>
          <div className="card-value amber">{d.preco_medio_litro_frota !== null && d.preco_medio_litro_frota !== undefined ? `R$ ${fmtNumero(d.preco_medio_litro_frota, 3)}` : "—"}</div>
        </div>
      </div>

      <div className="section-title">Por veículo</div>
      <table>
        <thead>
          <tr>
            <th>Placa</th><th>Modelo</th><th>Km/L</th><th>Km percorrido</th><th>Litros</th>
            <th>Valor gasto</th><th>R$/km</th><th>Abastecimentos</th><th>Saltos suspeitos</th>
          </tr>
        </thead>
        <tbody>
          {d.veiculos.map((v) => (
            <tr key={v.placa}>
              <td>{v.placa}</td>
              <td>{v.modelo || "—"}</td>
              <td>{v.km_por_litro !== null ? fmtNumero(v.km_por_litro, 2) : "—"}</td>
              <td>{fmtNumero(v.km_percorrido_estimado)}</td>
              <td>{fmtNumero(v.litros_total)}</td>
              <td>{v.valor_gasto_total !== null && v.valor_gasto_total !== undefined ? fmtMoeda(v.valor_gasto_total) : "—"}</td>
              <td>{v.custo_por_km !== null && v.custo_por_km !== undefined ? `R$ ${fmtNumero(v.custo_por_km, 2)}` : "—"}</td>
              <td>{v.abastecimentos}</td>
              <td>{v.saltos_suspeitos.length > 0 ? <span className="badge warn">{v.saltos_suspeitos.length} suspeito(s)</span> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function DetalheOperacional({ d }) {
  const status = Object.entries(d.por_status || {});
  const servicos = Object.entries(d.por_servico || {});
  const veiculos = Object.entries(d.por_veiculo || {});
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">Total de linhas</div>
          <div className="card-value emerald">{fmtNumero(d.total_linhas)}</div>
        </div>
        <div className="card">
          <div className="card-label">OS numeradas</div>
          <div className="card-value emerald">{fmtNumero(d.total_os_numeradas)}</div>
        </div>
        <div className="card">
          <div className="card-label">Faturamento</div>
          <div className="card-value emerald">{fmtMoeda(d.faturamento_total)}</div>
        </div>
        <div className="card">
          <div className="card-label">Taxa de realizado</div>
          <div className="card-value emerald">{d.taxa_realizado_pct !== null ? fmtPct(d.taxa_realizado_pct) : "—"}</div>
        </div>
      </div>

      <div className="section-title">Por status</div>
      <table>
        <thead><tr><th>Status</th><th>Quantidade</th></tr></thead>
        <tbody>
          {status.map(([nome, qtd]) => (
            <tr key={nome}><td>{nome}</td><td>{fmtNumero(qtd)}</td></tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">Por serviço</div>
      <table>
        <thead><tr><th>Serviço</th><th>Quantidade</th><th>Valor total</th></tr></thead>
        <tbody>
          {servicos.map(([nome, v]) => (
            <tr key={nome}><td>{nome}</td><td>{fmtNumero(v.quantidade)}</td><td>{fmtMoeda(v.valor_total)}</td></tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">Faturamento por caminhão</div>
      <table>
        <thead><tr><th>Veículo</th><th>OS</th><th>Faturamento</th></tr></thead>
        <tbody>
          {veiculos.map(([placa, v]) => (
            <tr key={placa}><td>{placa}</td><td>{fmtNumero(v.quantidade)}</td><td>{fmtMoeda(v.valor_total)}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function DetalheFinanceiro({ d }) {
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">Receita acumulada</div>
          <div className="card-value purple">{fmtMoeda(d.receita_acumulada)}</div>
        </div>
        <div className="card">
          <div className="card-label">Lucro acumulado</div>
          <div className={`card-value ${d.lucro_acumulado < 0 ? "red" : "purple"}`}>{fmtMoeda(d.lucro_acumulado)}</div>
        </div>
        <div className="card">
          <div className="card-label">Margem líquida</div>
          <div className="card-value purple">{d.margem_liquida_acumulada_pct !== null ? fmtPct(d.margem_liquida_acumulada_pct) : "—"}</div>
        </div>
        {d.pmr_dias !== undefined && (
          <div className="card">
            <div className="card-label">Prazo médio de recebimento</div>
            <div className="card-value purple">{d.pmr_dias !== null ? `${fmtNumero(d.pmr_dias, 1)} dias` : "—"}</div>
          </div>
        )}
        {d.pmp_dias !== undefined && (
          <div className="card">
            <div className="card-label">Prazo médio de pagamento</div>
            <div className="card-value purple">{d.pmp_dias !== null ? `${fmtNumero(d.pmp_dias, 1)} dias` : "—"}</div>
          </div>
        )}
        {d.inadimplencia_pct !== undefined && (
          <div className="card">
            <div className="card-label">Inadimplência</div>
            <div className="card-value purple">{d.inadimplencia_pct !== null ? fmtPct(d.inadimplencia_pct) : "—"}</div>
          </div>
        )}
      </div>

      <div className="section-title">Série mensal</div>
      <table>
        <thead>
          <tr>
            <th>Mês</th><th>Receita bruta</th><th>Despesas pessoal</th><th>Despesas gerais</th>
            <th>Lucro líquido</th><th>Margem</th>
          </tr>
        </thead>
        <tbody>
          {d.serie_mensal.map((m) => (
            <tr key={m.period}>
              <td>{m.period}</td>
              <td>{fmtMoeda(m.receita_bruta)}</td>
              <td>{fmtMoeda(m.despesas_pessoal)}</td>
              <td>{fmtMoeda(m.despesas_gerais)}</td>
              <td className={m.lucro_liquido < 0 ? "" : ""}>{fmtMoeda(m.lucro_liquido)}</td>
              <td>{m.margem_liquida_pct !== null ? fmtPct(m.margem_liquida_pct) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function DetalheOrcamento({ d }) {
  const serie = d.serie_mensal || [];
  const proximo = d.projecao_proximo_mes;
  return (
    <>
      <div className="grid">
        {proximo && (
          <>
            <div className="card">
              <div className="card-label">Lucro líquido projetado ({proximo.period})</div>
              <div className={`card-value ${proximo.lucro_liquido < 0 ? "red" : "rose"}`}>{fmtMoeda(proximo.lucro_liquido)}</div>
            </div>
            <div className="card">
              <div className="card-label">Receita bruta projetada ({proximo.period})</div>
              <div className="card-value rose">{fmtMoeda(proximo.receita_bruta)}</div>
            </div>
          </>
        )}
      </div>

      <div className="section-title">Lucro líquido — orçamento estimado x realizado</div>
      <table>
        <thead>
          <tr><th>Mês</th><th>Realizado</th><th>Orçamento estimado</th><th>Variação (R$)</th><th>Variação (%)</th></tr>
        </thead>
        <tbody>
          {serie.map((m) => {
            const v = m.lucro_liquido;
            return (
              <tr key={m.period}>
                <td>{m.period}</td>
                <td>{fmtMoeda(v.realizado)}</td>
                <td>{v.orcamento_estimado !== null ? fmtMoeda(v.orcamento_estimado) : "— (sem histórico anterior)"}</td>
                <td>{v.variacao_valor !== null ? fmtMoeda(v.variacao_valor) : "—"}</td>
                <td>{v.variacao_pct !== null ? fmtPct(v.variacao_pct) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="section-title">Receita bruta — orçamento estimado x realizado</div>
      <table>
        <thead>
          <tr><th>Mês</th><th>Realizado</th><th>Orçamento estimado</th><th>Variação (R$)</th><th>Variação (%)</th></tr>
        </thead>
        <tbody>
          {serie.map((m) => {
            const v = m.receita_bruta;
            return (
              <tr key={m.period}>
                <td>{m.period}</td>
                <td>{fmtMoeda(v.realizado)}</td>
                <td>{v.orcamento_estimado !== null ? fmtMoeda(v.orcamento_estimado) : "— (sem histórico anterior)"}</td>
                <td>{v.variacao_valor !== null ? fmtMoeda(v.variacao_valor) : "—"}</td>
                <td>{v.variacao_pct !== null ? fmtPct(v.variacao_pct) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="section-title">Despesas — realizado x estimado</div>
      <table>
        <thead>
          <tr>
            <th>Mês</th>
            <th>Pessoal (realizado)</th><th>Pessoal (estimado)</th>
            <th>Gerais (realizado)</th><th>Gerais (estimado)</th>
            <th>Bancárias (realizado)</th><th>Bancárias (estimado)</th>
          </tr>
        </thead>
        <tbody>
          {serie.map((m) => (
            <tr key={m.period}>
              <td>{m.period}</td>
              <td>{fmtMoeda(m.despesas_pessoal.realizado)}</td>
              <td>{m.despesas_pessoal.orcamento_estimado !== null ? fmtMoeda(m.despesas_pessoal.orcamento_estimado) : "—"}</td>
              <td>{fmtMoeda(m.despesas_gerais.realizado)}</td>
              <td>{m.despesas_gerais.orcamento_estimado !== null ? fmtMoeda(m.despesas_gerais.orcamento_estimado) : "—"}</td>
              <td>{fmtMoeda(m.despesas_bancarias.realizado)}</td>
              <td>{m.despesas_bancarias.orcamento_estimado !== null ? fmtMoeda(m.despesas_bancarias.orcamento_estimado) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="page-subtitle" style={{ marginTop: "0.5rem" }}>
        {d.aviso}
      </p>
    </>
  );
}

const RENDERERS = {
  comercial: DetalheComercial,
  frota: DetalheFrota,
  operacional: DetalheOperacional,
  financeiro: DetalheFinanceiro,
  orcamento: DetalheOrcamento,
};

export default function AreaDetalhe({ area }) {
  const [doc, setDoc] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    setDoc(null);
    setErro(null);
    fetchLatest(area)
      .then(setDoc)
      .catch((e) => setErro(e.message));
  }, [area]);

  const Renderer = RENDERERS[area];

  return (
    <div>
      <h1 className="page-title">{areaLabel(area)}</h1>
      <p className="page-subtitle">
        {doc?.ingested_at ? `Última atualização: ${fmtData(doc.ingested_at)} (${doc.source === "claude" ? "via Claude" : "upload manual"})` : "Nenhum dado ainda"}
        {doc?.period ? ` · período de apuração: ${doc.period}` : ""}
      </p>

      {erro && <div className="aviso">Não consegui buscar os dados do backend ({erro}).</div>}
      {!doc && !erro && <div className="empty-state">Carregando…</div>}

      {doc && !doc.data && (
        <div className="empty-state">
          {doc.message || "Nenhum dado ainda — peça pro Claude atualizar ou envie uma planilha."}
        </div>
      )}

      {doc?.data && (
        <>
          {doc.requires_review && (
            <div className="aviso">Este dado veio de um PDF extraído automaticamente — vale conferir antes de confiar 100%.</div>
          )}
          <Renderer d={doc.data} />
        </>
      )}
    </div>
  );
}
