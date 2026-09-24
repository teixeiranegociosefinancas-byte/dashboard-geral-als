import { useEffect, useState } from "react";
import { fetchLatest } from "../api.js";
import { areaLabel } from "../areas.js";
import { fmtMoeda, fmtNumero, fmtPct, fmtData, fmtDataSimples } from "../format.js";

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
        {d.meta_mensal !== null && d.meta_mensal !== undefined && (
          <div className="card">
            <div className="card-label">Meta mensal</div>
            <div className="card-value cyan">{fmtMoeda(d.meta_mensal)}</div>
          </div>
        )}
        <div className="card">
          <div className="card-label">Meta total (por serviço)</div>
          <div className="card-value cyan">{fmtMoeda(d.meta_total)}</div>
        </div>
        <div className="card">
          <div className="card-label">Atingimento (meta por serviço)</div>
          <div className="card-value cyan">{d.atingimento_pct !== null ? fmtPct(d.atingimento_pct) : "—"}</div>
        </div>
      </div>
      {d.meta_mensal_base && (
        <p className="page-subtitle" style={{ marginTop: "-0.5rem", marginBottom: "0.75rem" }}>{d.meta_mensal_base}</p>
      )}
      {d.outros_nao_categorizado !== null && d.outros_nao_categorizado !== undefined && (
        <div className="aviso" style={{ marginBottom: "1rem" }}>
          Faturamento reconciliado com a Receita Bruta oficial do Financeiro ({fmtMoeda(d.receita_bruta_oficial)}):
          {" "}"Outros/Não categorizado" = {fmtMoeda(d.outros_nao_categorizado)}. {d.motivo_outros_nao_categorizado}
        </div>
      )}

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
        {d.periodo_apuracao_inicio && d.periodo_apuracao_fim && (
          <div className="card">
            <div className="card-label">Período de apuração</div>
            <div className="card-value amber" style={{ fontSize: "1.3rem" }}>
              {fmtDataSimples(d.periodo_apuracao_inicio)} – {fmtDataSimples(d.periodo_apuracao_fim)}
            </div>
          </div>
        )}
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
        <div className="card">
          <div className="card-label">ROI (Lucro Líquido ÷ Receita Líquida)</div>
          <div className="card-value purple">{d.roi_pct_acumulado !== null ? fmtPct(d.roi_pct_acumulado) : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">EBITDA acumulado</div>
          <div className="card-value purple">{d.ebitda_acumulado !== null && d.ebitda_acumulado !== undefined ? fmtMoeda(d.ebitda_acumulado) : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">EBITDA / Receita líquida</div>
          <div className="card-value purple">
            {d.ebitda_pct_receita_liquida_acumulado !== null && d.ebitda_pct_receita_liquida_acumulado !== undefined
              ? fmtPct(d.ebitda_pct_receita_liquida_acumulado)
              : "—"}
          </div>
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

      {d.margem_contribuicao_pct !== null && d.margem_contribuicao_pct !== undefined && (
        <>
          <div className="section-title">Margem de contribuição / ponto de equilíbrio</div>
          <div className="grid">
            <div className="card">
              <div className="card-label">Margem de contribuição</div>
              <div className="card-value purple">{fmtPct(d.margem_contribuicao_pct)}</div>
            </div>
            <div className="card">
              <div className="card-label">Custo fixo acumulado</div>
              <div className="card-value purple">{fmtMoeda(d.custo_fixo_acumulado)}</div>
            </div>
            <div className="card">
              <div className="card-label">Custo variável acumulado</div>
              <div className="card-value purple">{fmtMoeda(d.custo_variavel_acumulado)}</div>
            </div>
            <div className="card">
              <div className="card-label">Ponto de equilíbrio (médio mensal)</div>
              <div className="card-value purple">{fmtMoeda(d.ponto_equilibrio_mensal_medio)}</div>
            </div>
            {d.maior_despesa_mensal_total !== null && d.maior_despesa_mensal_total !== undefined && (
              <div className="card">
                <div className="card-label">Maior despesa mensal (pior mês real{d.maior_despesa_mensal_period ? `, ${d.maior_despesa_mensal_period}` : ""})</div>
                <div className="card-value purple">{fmtMoeda(d.maior_despesa_mensal_total)}</div>
              </div>
            )}
          </div>
          {d.aviso_cvp && <p className="page-subtitle" style={{ marginTop: "-0.5rem", marginBottom: "1rem" }}>{d.aviso_cvp}</p>}
        </>
      )}

      <div className="section-title">Série mensal</div>
      <table>
        <thead>
          <tr>
            <th>Mês</th><th>Receita bruta</th><th>Despesas pessoal</th><th>Despesas gerais</th>
            <th>Lucro líquido</th><th>Margem</th><th>ROI</th><th>EBITDA</th><th>EBITDA / Receita líq.</th>
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
              <td>{m.roi_pct !== null && m.roi_pct !== undefined ? fmtPct(m.roi_pct) : "—"}</td>
              <td>{m.ebitda !== null && m.ebitda !== undefined ? fmtMoeda(m.ebitda) : "—"}</td>
              <td>{m.ebitda_pct_receita_liquida !== null && m.ebitda_pct_receita_liquida !== undefined ? fmtPct(m.ebitda_pct_receita_liquida) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {d.aviso_roi_ebitda && (
        <p className="page-subtitle" style={{ marginTop: "0.5rem" }}>{d.aviso_roi_ebitda}</p>
      )}
    </>
  );
}

function DetalheOpex({ d }) {
  const serie = d.serie_mensal || [];
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">OPEX (mês mais recente)</div>
          <div className="card-value teal">{fmtMoeda(d.opex_total_atual)}</div>
        </div>
        <div className="card">
          <div className="card-label">OPEX / Receita líquida (mês mais recente)</div>
          <div className="card-value teal">{d.opex_pct_receita_atual !== null ? fmtPct(d.opex_pct_receita_atual) : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">OPEX / Receita líquida (média do período)</div>
          <div className="card-value teal">{d.opex_pct_receita_media !== null ? fmtPct(d.opex_pct_receita_media) : "—"}</div>
        </div>
      </div>

      <div className="section-title">OPEX real x receita — mês a mês</div>
      <table>
        <thead>
          <tr>
            <th>Mês</th>
            <th>Pessoal</th><th>Gerais</th><th>Bancárias</th><th>OPEX total</th>
            <th>Receita líquida</th><th>OPEX / Receita líquida</th><th>OPEX / Receita bruta</th>
          </tr>
        </thead>
        <tbody>
          {serie.map((m) => (
            <tr key={m.period}>
              <td>{m.period}</td>
              <td>{fmtMoeda(m.despesas_pessoal)}</td>
              <td>{fmtMoeda(m.despesas_gerais)}</td>
              <td>{fmtMoeda(m.despesas_bancarias)}</td>
              <td>{fmtMoeda(m.opex_total)}</td>
              <td>{fmtMoeda(m.receita_liquida)}</td>
              <td>{m.opex_pct_receita_liquida !== null ? fmtPct(m.opex_pct_receita_liquida) : "—"}</td>
              <td>{m.opex_pct_receita_bruta !== null ? fmtPct(m.opex_pct_receita_bruta) : "—"}</td>
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

      {d.cenario_20pct_sobre_ponto_equilibrio && (
        <>
          <div className="section-title">Cenário — +20% sobre o ponto de equilíbrio seguro</div>
          <div className="grid">
            <div className="card">
              <div className="card-label">Ponto de equilíbrio seguro usado</div>
              <div className="card-value rose">{fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.ponto_equilibrio_seguro_usado)}</div>
            </div>
            <div className="card">
              <div className="card-label">Receita projetada</div>
              <div className="card-value rose">{fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.receita_projetada)}</div>
            </div>
            <div className="card">
              <div className="card-label">Lucro projetado</div>
              <div className="card-value rose">{fmtMoeda(d.cenario_20pct_sobre_ponto_equilibrio.lucro_projetado)}</div>
            </div>
            <div className="card">
              <div className="card-label">Margem líquida projetada</div>
              <div className="card-value rose">
                {d.cenario_20pct_sobre_ponto_equilibrio.margem_liquida_projetada_pct !== null
                  ? fmtPct(d.cenario_20pct_sobre_ponto_equilibrio.margem_liquida_projetada_pct)
                  : "—"}
              </div>
            </div>
          </div>
          {d.cenario_20pct_sobre_ponto_equilibrio.ponto_equilibrio_seguro_baseado_no_mes && (
            <p className="page-subtitle" style={{ marginTop: "-0.5rem", marginBottom: "0.75rem" }}>
              Referência: {d.cenario_20pct_sobre_ponto_equilibrio.ponto_equilibrio_seguro_baseado_no_mes}
            </p>
          )}
          {d.cenario_20pct_sobre_ponto_equilibrio.aviso && (
            <p className="page-subtitle" style={{ marginTop: 0, marginBottom: "1rem" }}>
              {d.cenario_20pct_sobre_ponto_equilibrio.aviso}
            </p>
          )}
        </>
      )}

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
          <tr><th>Mês</th><th>Realizado</th><th>Orçamento estimado</th><th>Ajuste por contrato novo</th><th>Variação (R$)</th><th>Variação (%)</th></tr>
        </thead>
        <tbody>
          {serie.map((m) => {
            const v = m.receita_bruta;
            return (
              <tr key={m.period}>
                <td>{m.period}</td>
                <td>{fmtMoeda(v.realizado)}</td>
                <td>{v.orcamento_estimado !== null ? fmtMoeda(v.orcamento_estimado) : "— (sem histórico anterior)"}</td>
                <td>{v.ajuste_contratos_novos ? `+ ${fmtMoeda(v.ajuste_contratos_novos)}` : "—"}</td>
                <td>{v.variacao_valor !== null ? fmtMoeda(v.variacao_valor) : "—"}</td>
                <td>{v.variacao_pct !== null ? fmtPct(v.variacao_pct) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {Object.keys(d.contratos_novos_considerados || {}).length > 0 && (
        <>
          <div className="section-title">Contratos novos considerados no ajuste</div>
          <table>
            <thead>
              <tr><th>Mês</th><th>Contrato</th><th>Valor total</th><th>Início</th><th>Validade (dias)</th><th>Valor mensal aproximado</th></tr>
            </thead>
            <tbody>
              {Object.entries(d.contratos_novos_considerados).flatMap(([mes, contratos]) =>
                contratos.map((c) => (
                  <tr key={`${mes}-${c.nome}`}>
                    <td>{mes}</td>
                    <td>{c.nome}</td>
                    <td>{fmtMoeda(c.valor_total)}</td>
                    <td>{c.data_inicio}</td>
                    <td>{fmtNumero(c.validade_dias)}</td>
                    <td>{fmtMoeda(c.valor_mensal_aproximado)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          <p className="page-subtitle" style={{ marginTop: "0.25rem" }}>
            Valor mensal aproximado = valor total ÷ dias de validade × 30 (distribuição uniforme ao longo do contrato) — não é um valor exato de recebimento mensal.
          </p>
        </>
      )}

      {(() => {
        // detalhamento_contas vem chaveado pelo texto exato da categoria (ex:
        // "Despesas Gerais", "Despesas com Pessoal") — iterar por todas as
        // categorias presentes, não só uma fixa, pra funcionar com qualquer
        // categoria nova que o Claude adicionar no futuro.
        const categorias = d.detalhamento_contas || {};
        return Object.entries(categorias).map(([categoria, contas]) => {
          const manutencaoEntries = Object.entries(contas).filter(([, c]) => c.categoria_manutencao);
          const outrasEntries = Object.entries(contas).filter(([, c]) => !c.categoria_manutencao);
          return (
            <div key={categoria}>
              {manutencaoEntries.length > 0 && (
                <>
                  <div className="section-title">{categoria} — manutenção — orçamento estimado x realizado (por conta)</div>
                  <table>
                    <thead>
                      <tr><th>Conta</th><th>Mês</th><th>Realizado</th><th>Orçamento estimado</th><th>Variação (%)</th></tr>
                    </thead>
                    <tbody>
                      {manutencaoEntries.flatMap(([conta, c]) =>
                        c.serie.map((m) => (
                          <tr key={`${conta}-${m.period}`}>
                            <td>{conta}</td>
                            <td>{m.period}</td>
                            <td>{fmtMoeda(m.realizado)}</td>
                            <td>{m.orcamento_estimado !== null ? fmtMoeda(m.orcamento_estimado) : "—"}</td>
                            <td>{m.variacao_pct !== null ? fmtPct(m.variacao_pct) : "—"}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </>
              )}

              {outrasEntries.length > 0 && (
                <>
                  <div className="section-title">{categoria} — detalhamento por conta (mês mais recente)</div>
                  <table>
                    <thead>
                      <tr><th>Conta</th><th>Mês</th><th>Realizado</th><th>Orçamento estimado</th><th>Variação (%)</th><th>Projeção próx. mês</th></tr>
                    </thead>
                    <tbody>
                      {outrasEntries.map(([conta, c]) => {
                        const ultimo = c.serie[c.serie.length - 1];
                        return (
                          <tr key={conta}>
                            <td>{conta}</td>
                            <td>{ultimo.period}</td>
                            <td>{fmtMoeda(ultimo.realizado)}</td>
                            <td>{ultimo.orcamento_estimado !== null ? fmtMoeda(ultimo.orcamento_estimado) : "—"}</td>
                            <td>{ultimo.variacao_pct !== null ? fmtPct(ultimo.variacao_pct) : "—"}</td>
                            <td>{c.projecao_proximo_mes ? fmtMoeda(c.projecao_proximo_mes.valor) : "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          );
        });
      })()}

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

      <details className="explicacoes">
        <summary>Explicações</summary>

        <div className="explicacoes-item">
          <h4>Por que o combustível variou tanto em 2026 (e por que não usamos o IPCA pra prever)</h4>
          <p>
            <strong>Fatos:</strong> o preço médio pago por litro pela frota da ALS saltou de R$5,89 (fixo em janeiro
            e fevereiro) para uma faixa de R$7,15 a R$7,76 em março-abril, inclusive dentro do mesmo veículo. Isso bate
            com um evento real e documentado: segundo a ANP, o Diesel S10 subiu 16,23% no Brasil em março de 2026
            (de R$6,10 para R$7,09/litro), por causa do conflito no Oriente Médio iniciado em 28/02/2026, que disparou
            a cotação internacional do petróleo — o Brasil importa 25% a 30% do diesel que consome, então o preço
            interno segue o mercado externo.
          </p>
          <p>
            <strong>Análise:</strong> esse é um choque de mercado de commodity (geopolítico), não inflação normal ao
            consumidor — por isso o IPCA não serve pra explicar nem prever esse tipo de oscilação, e não foi usado
            como base do orçamento estimado. A média acumulada usada aqui já absorve esse tipo de pico com o tempo,
            por ser uma média de vários meses reais, incluindo os de alta.
          </p>
        </div>

        <div className="explicacoes-item">
          <h4>Por que o salário teve reajuste em janeiro (e por que também não é o IPCA)</h4>
          <p>
            <strong>Fatos:</strong> a ALS está sob duas convenções coletivas (CCT) do mesmo sindicato patronal
            (SEAC/BA): uma com o SINTRACAP (motoristas, ajudantes, carregadores — o pessoal de caminhão) e outra com
            o SINDILIMP (asseio, conservação, controle de pragas — o pessoal de desinsetização). As duas têm o mesmo
            texto de reajuste: data-base sempre 1º de janeiro, com 7,23% em 01/01/2025 e 8,50% em 01/01/2026 (faixa
            de piso da ALS, até R$4.999,99). O IPCA acumulado oficial (IBGE) foi de 4,83% em 2024 e 4,26% em 2025.
          </p>
          <p>
            <strong>Análise:</strong> o reajuste é negociado direto entre sindicatos, sem nenhuma fórmula ligada a
            IPCA/INPC, e ficou bem acima da inflação nos dois anos (quase o dobro em 2026) — é ganho real negociado,
            não correção de inflação. O reajuste de janeiro/2026 já está embutido nos dados reais usados aqui; não há
            novo reajuste dentro do período que o orçamento projeta hoje (o próximo é só em 01/01/2027, e esse
            percentual ainda não existe).
          </p>
        </div>
      </details>

      <p className="page-subtitle" style={{ marginTop: "0.5rem" }}>
        {d.aviso}
      </p>
    </>
  );
}

function DetalheCapex({ d }) {
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">CAPEX — aquisição de ativo fixo capitalizada</div>
          <div className="card-value orange">{fmtMoeda(d.capex_capitalizado)}</div>
        </div>
        <div className="card">
          <div className="card-label">Participação em consórcios (não capitalizado)</div>
          <div className="card-value orange">{fmtMoeda(d.consorcio_nao_capitalizado)}</div>
        </div>
      </div>

      <details className="explicacoes">
        <summary>Explicações</summary>

        <div className="explicacoes-item">
          <h4>Por que o CAPEX está zerado</h4>
          <p>
            <strong>Fatos:</strong> no balancete oficial da ALS (sistema TRACT Contabilidade, assinado digitalmente,
            período 01/01/2025 a 31/12/2025 — o único balancete fechado disponível até agora), a conta Imobilizado e
            todas as suas subcontas (Edifícios, Máquinas e Equipamentos, Móveis, Terrenos, Veículos) tiveram Débito e
            Crédito iguais a R$0,00 o ano inteiro — nenhuma aquisição de ativo fixo foi lançada contabilmente. A única
            movimentação ligada a ativo foi R$39.231,91 em "Participação em Consórcios" (parcelas pagas de um
            consórcio — financiamento pra uma aquisição futura, ainda não é ativo capitalizado). Cruzando com as
            contas a pagar de 2026 (busca por veículo/caminhão/equipamento/compra/aquisição, mais os 25 maiores
            lançamentos do ano), não apareceu nenhuma compra de ativo fixo — os maiores valores são empréstimo de
            sócio, combustível, salário e <strong>locação</strong> de caminhão/sugador/banheiro químico, inclusive da
            Prime (empresa do mesmo grupo).
          </p>
          <p>
            <strong>Análise:</strong> os dois fatos acima convergem: não é falta de dado, é um resultado real — a ALS
            não capitalizou nenhuma aquisição de ativo fixo no período coberto. O jeito que a empresa expande
            capacidade operacional é alugando caminhões e equipamentos de terceiros, não comprando — coerente com o
            quadro já visto no Balanço 2025 (patrimônio líquido quase zerado, endividamento alto, pouca folga de
            caixa pra investimento de capital). Ainda não existe um balancete fechado de 2026 pra confirmar se esse
            padrão continua neste ano — este número será atualizado assim que a contabilidade fechar um novo
            balancete. Este campo não foi reautorizado/repopulado nesta rodada (só recriado na tela) — continua
            usando o mesmo balancete de 2025 até que o usuário autorize uma nova leitura do Balancete/Balanço.
          </p>
        </div>
      </details>

      <p className="page-subtitle" style={{ marginTop: "0.5rem" }}>{d.aviso}</p>
    </>
  );
}

function DetalheRh({ d }) {
  const serie = d.serie_mensal || [];
  const aso = d.aso;
  const statusLabel = { OK: "OK", VENCIDO: "vencido", SEM_ASO_VALIDO: "sem ASO válido" };
  return (
    <>
      <div className="grid">
        <div className="card">
          <div className="card-label">Headcount atual</div>
          <div className="card-value indigo">{fmtNumero(d.headcount_atual)}</div>
        </div>
        <div className="card">
          <div className="card-label">Salário médio atual</div>
          <div className="card-value indigo">{d.salario_medio_atual !== null ? fmtMoeda(d.salario_medio_atual) : "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">Taxa de demissão (mês atual)</div>
          <div className="card-value indigo">{d.taxa_demissao_atual_pct !== null ? fmtPct(d.taxa_demissao_atual_pct) : "—"}</div>
        </div>
        {aso && (
          <div className="card">
            <div className="card-label">ASO em dia</div>
            <div className="card-value indigo">{aso.ok}/{aso.total_funcionarios}</div>
          </div>
        )}
      </div>

      <div className="section-title">Headcount, admissões, demitidos e turnover</div>
      <table>
        <thead>
          <tr><th>Mês</th><th>Headcount</th><th>Admissões</th><th>Demitidos</th><th>Taxa de demissão</th></tr>
        </thead>
        <tbody>
          {serie.map((m) => (
            <tr key={m.period}>
              <td>{m.period}</td>
              <td>{fmtNumero(m.headcount)}</td>
              <td>{fmtNumero(m.admissoes)}</td>
              <td>{fmtNumero(m.demitidos)}</td>
              <td>{m.taxa_demissao_pct !== null ? fmtPct(m.taxa_demissao_pct) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">Salário médio mensal</div>
      <table>
        <thead>
          <tr><th>Mês</th><th>Salário médio</th><th>Funcionários considerados</th></tr>
        </thead>
        <tbody>
          {serie.map((m) => (
            <tr key={m.period}>
              <td>{m.period}</td>
              <td>{m.salario_medio !== null ? fmtMoeda(m.salario_medio) : "—"}</td>
              <td>{fmtNumero(m.funcionarios_contados_salario)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {aso && (
        <>
          <div className="section-title">ASO — status por funcionário</div>
          <table>
            <thead>
              <tr><th>Funcionário</th><th>Situação</th><th>Data do exame</th><th>Vencimento</th><th>Status</th><th>Observação</th></tr>
            </thead>
            <tbody>
              {aso.detalhe.map((f) => (
                <tr key={f.nome}>
                  <td>{f.nome}</td>
                  <td>{f.situacao || "—"}</td>
                  <td>{f.data_exame || "—"}</td>
                  <td>{f.vencimento || "—"}</td>
                  <td>
                    <span className={`badge ${f.status === "OK" ? "ok" : "warn"}`}>
                      {statusLabel[f.status] || f.status}
                    </span>
                  </td>
                  <td>{f.observacao || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

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
  rh: DetalheRh,
  opex: DetalheOpex,
  capex: DetalheCapex,
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
