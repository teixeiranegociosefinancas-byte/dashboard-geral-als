import { useEffect, useState } from "react";
import { fetchVisaoGeral } from "../api.js";
import KpiCard from "../components/KpiCard.jsx";
import { fmtMoeda, fmtNumero, fmtPct, fmtData } from "../format.js";

function CardsComercial({ doc, onClick }) {
  const d = doc?.data;
  return (
    <>
      <KpiCard
        label="Faturamento (Comercial)"
        value={d ? fmtMoeda(d.faturamento_total) : "sem dados"}
        color="cyan"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar ou envie uma planilha"}
        onClick={onClick}
      />
      <KpiCard
        label="Atingimento da meta"
        value={d && d.atingimento_pct !== null ? fmtPct(d.atingimento_pct) : "—"}
        color="cyan"
        onClick={onClick}
      />
    </>
  );
}

function CardsFrota({ doc, onClick }) {
  const d = doc?.data;
  return (
    <>
      <KpiCard
        label="Km/litro da frota"
        value={d && d.km_por_litro_frota !== null ? `${fmtNumero(d.km_por_litro_frota, 2)} km/L` : "sem dados"}
        color="amber"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar ou envie uma planilha"}
        onClick={onClick}
      />
      <KpiCard
        label="Veículos monitorados"
        value={d ? fmtNumero(d.total_veiculos) : "—"}
        color="amber"
        onClick={onClick}
      />
    </>
  );
}

function CardsOperacional({ doc, onClick }) {
  const d = doc?.data;
  return (
    <>
      <KpiCard
        label="Ordens de serviço"
        value={d ? fmtNumero(d.total_os_numeradas) : "sem dados"}
        color="emerald"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar ou envie uma planilha"}
        onClick={onClick}
      />
      <KpiCard
        label="Taxa de realizado"
        value={d && d.taxa_realizado_pct !== null ? fmtPct(d.taxa_realizado_pct) : "—"}
        color="emerald"
        onClick={onClick}
      />
    </>
  );
}

function CardsFinanceiro({ doc, onClick }) {
  const d = doc?.data;
  const lucroNegativo = d && d.lucro_acumulado !== null && d.lucro_acumulado < 0;
  return (
    <>
      <KpiCard
        label="Receita acumulada"
        value={d ? fmtMoeda(d.receita_acumulada) : "sem dados"}
        color="purple"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar ou envie uma planilha"}
        onClick={onClick}
      />
      <KpiCard
        label="Lucro acumulado"
        value={d ? fmtMoeda(d.lucro_acumulado) : "—"}
        color={lucroNegativo ? "red" : "purple"}
        onClick={onClick}
      />
    </>
  );
}

function CardsOrcamento({ doc, onClick }) {
  const d = doc?.data;
  const proximo = d?.projecao_proximo_mes;
  const lucroNegativo = proximo && proximo.lucro_liquido !== null && proximo.lucro_liquido < 0;
  return (
    <>
      <KpiCard
        label="Lucro líquido projetado (próx. mês)"
        value={proximo ? fmtMoeda(proximo.lucro_liquido) : "sem dados"}
        color={lucroNegativo ? "red" : "rose"}
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)} — estimativa, não é meta da diretoria` : "peça pro Claude atualizar"}
        onClick={onClick}
      />
      <KpiCard
        label="Receita bruta projetada (próx. mês)"
        value={proximo ? fmtMoeda(proximo.receita_bruta) : "—"}
        color="rose"
        onClick={onClick}
      />
    </>
  );
}

function CardsRh({ doc, onClick }) {
  const d = doc?.data;
  return (
    <>
      <KpiCard
        label="Headcount atual"
        value={d ? fmtNumero(d.headcount_atual) : "sem dados"}
        color="indigo"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar"}
        onClick={onClick}
      />
      <KpiCard
        label="ASO em dia"
        value={d?.aso ? `${d.aso.ok}/${d.aso.total_funcionarios}` : "—"}
        color="indigo"
        onClick={onClick}
      />
    </>
  );
}

function CardsOpex({ doc, onClick }) {
  const d = doc?.data;
  return (
    <>
      <KpiCard
        label="OPEX (mês mais recente)"
        value={d ? fmtMoeda(d.opex_total_atual) : "sem dados"}
        color="teal"
        meta={doc ? `Atualizado em ${fmtData(doc.ingested_at)}` : "peça pro Claude atualizar"}
        onClick={onClick}
      />
      <KpiCard
        label="OPEX / Receita líquida"
        value={d && d.opex_pct_receita_atual !== null ? fmtPct(d.opex_pct_receita_atual) : "—"}
        color="teal"
        onClick={onClick}
      />
    </>
  );
}

export default function VisaoGeral({ onNavigate }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    fetchVisaoGeral()
      .then(setDados)
      .catch((e) => setErro(e.message));
  }, []);

  return (
    <div>
      <h1 className="page-title">Visão Geral</h1>
      <p className="page-subtitle">Panorama consolidado — Comercial, Frota, Operacional, Financeiro, Orçamento, RH/DP e OPEX</p>

      {erro && (
        <div className="aviso">
          Não consegui buscar os dados do backend ({erro}). Confira se o painel está configurado com a URL
          certa do backend (VITE_API_URL) e se o backend está acessível.
        </div>
      )}

      {!dados && !erro && <div className="empty-state">Carregando…</div>}

      {dados && (
        <div className="grid">
          <CardsComercial doc={dados.comercial} onClick={() => onNavigate("comercial")} />
          <CardsFrota doc={dados.frota} onClick={() => onNavigate("frota")} />
          <CardsOperacional doc={dados.operacional} onClick={() => onNavigate("operacional")} />
          <CardsFinanceiro doc={dados.financeiro} onClick={() => onNavigate("financeiro")} />
          <CardsOrcamento doc={dados.orcamento} onClick={() => onNavigate("orcamento")} />
          <CardsRh doc={dados.rh} onClick={() => onNavigate("rh")} />
          <CardsOpex doc={dados.opex} onClick={() => onNavigate("opex")} />
        </div>
      )}
    </div>
  );
}
