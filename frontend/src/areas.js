export const AREAS = [
  { key: "comercial", label: "Comercial", color: "cyan" },
  { key: "frota", label: "Frota", color: "amber" },
  { key: "operacional", label: "Operacional", color: "emerald" },
  { key: "financeiro", label: "Financeiro", color: "purple" },
  { key: "orcamento", label: "Orçamento", color: "rose" },
  { key: "rh", label: "RH / DP", color: "indigo" },
  { key: "opex", label: "OPEX", color: "teal" },
  { key: "capex", label: "CAPEX", color: "orange" },
];

export function areaLabel(key) {
  return AREAS.find((a) => a.key === key)?.label || key;
}
