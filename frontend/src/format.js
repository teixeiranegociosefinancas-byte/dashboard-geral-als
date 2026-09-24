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

export function fmtDataSimples(isoData) {
  // Formata uma data "AAAA-MM-DD" (sem hora) como "DD/MM/AAAA" via
  // manipulação de string — evita o bug de fuso horário de `new Date("AAAA-MM-DD")`
  // (interpretada como UTC meia-noite, pode virar o dia anterior no fuso local).
  if (!isoData) return "—";
  const partes = String(isoData).split("-");
  if (partes.length !== 3) return isoData;
  const [ano, mes, dia] = partes;
  return `${dia}/${mes}/${ano}`;
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
