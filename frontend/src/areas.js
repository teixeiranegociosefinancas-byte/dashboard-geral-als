export const AREAS = [
  { key: "comercial", label: "Comercial", color: "cyan" },
  { key: "frota", label: "Frota", color: "amber" },
  { key: "operacional", label: "Operacional", color: "emerald" },
  { key: "financeiro", label: "Financeiro", color: "purple" },
];

export function areaLabel(key) {
  return AREAS.find((a) => a.key === key)?.label || key;
}
