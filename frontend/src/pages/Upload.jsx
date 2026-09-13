import { useState } from "react";
import { AREAS } from "../areas.js";
import { uploadArquivo } from "../api.js";

export default function Upload() {
  const [area, setArea] = useState(AREAS[0].key);
  const [period, setPeriod] = useState("");
  const [sheetName, setSheetName] = useState("");
  const [file, setFile] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [status, setStatus] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file || !apiKey) {
      setStatus({ type: "error", msg: "Selecione um arquivo e informe a chave de API." });
      return;
    }
    setEnviando(true);
    setStatus(null);
    try {
      const resultado = await uploadArquivo({ area, period: period || undefined, sheetName: sheetName || undefined, file, apiKey });
      setStatus({
        type: "success",
        msg: `Enviado com sucesso — ${resultado.linhas_lidas} linha(s) lida(s).${resultado.requires_review ? " Extração de PDF é automática, vale conferir os números." : ""}`,
      });
      setFile(null);
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Enviar planilha ou PDF</h1>
      <p className="page-subtitle">
        Sobe um arquivo (.xlsx ou .pdf) direto pro painel, sem passar pelo chat — mesmo normalizador de sempre.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>Área</label>
          <select value={area} onChange={(e) => setArea(e.target.value)}>
            {AREAS.map((a) => (
              <option key={a.key} value={a.key}>{a.label}</option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label>Período (opcional, ex: 2026-08)</label>
          <input type="text" value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="AAAA-MM" />
        </div>

        <div className="form-row">
          <label>Nome da aba (opcional, se não for a primeira)</label>
          <input type="text" value={sheetName} onChange={(e) => setSheetName(e.target.value)} />
        </div>

        <div className="form-row">
          <label>Arquivo (.xlsx ou .pdf)</label>
          <input type="file" accept=".xlsx,.xlsm,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>

        <div className="form-row">
          <label>Chave de API</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="cole a chave" />
        </div>

        <button className="btn" type="submit" disabled={enviando}>
          {enviando ? "Enviando…" : "Enviar"}
        </button>

        {status && <div className={`status-msg ${status.type}`}>{status.msg}</div>}
      </form>
    </div>
  );
}
