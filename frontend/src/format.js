export function fmtMoeda(v) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

export function fmtNumero(v, casas = 0) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

export function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  return `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function fmtData(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}
