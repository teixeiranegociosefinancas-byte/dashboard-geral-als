// URL base do backend. Pode ser sobrescrita em Vercel (Project Settings >
// Environment Variables) como VITE_API_URL, mas já vem com um valor padrão
// fixo apontando pro backend em produção — assim o painel funciona mesmo se
// a variável de ambiente não estiver configurada nesse deploy específico.
const BASE_URL = import.meta.env.VITE_API_URL || "https://dashboard-geral-backend-v2-silas-teixeira.vercel.app";

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Erro ${res.status} ao buscar ${path}`);
  }
  return res.json();
}

export async function fetchVisaoGeral() {
  return get("/api/kpis/visao-geral");
}

export async function fetchLatest(area) {
  return get(`/api/kpis/${area}/latest`);
}

export async function fetchHistorico(area, limite = 24) {
  return get(`/api/kpis/${area}/historico?limite=${limite}`);
}

// Upload manual — pede a chave de API na hora (nunca fica salva no bundle,
// só em memória da sessão do navegador).
export async function uploadArquivo({ area, period, sheetName, file, apiKey }) {
  const params = new URLSearchParams({ area });
  if (period) params.set("period", period);
  if (sheetName) params.set("sheet_name", sheetName);

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/api/upload?${params.toString()}`, {
    method: "POST",
    headers: { "x-api-key": apiKey },
    body: form,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status} no upload`);
  }
  return data;
}

export function apiConfigured() {
  return Boolean(BASE_URL);
}
