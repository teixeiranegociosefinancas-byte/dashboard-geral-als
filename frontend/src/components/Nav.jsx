import { AREAS } from "../areas.js";

export default function Nav({ view, onChange }) {
  return (
    <div className="sidebar">
      <div className="brand">
        Dashboard Geral
        <small>ALS Desinsetizadora</small>
      </div>
      <button className={`nav-btn ${view === "geral" ? "active" : ""}`} onClick={() => onChange("geral")}>
        Visão Geral
      </button>
      {AREAS.map((a) => (
        <button
          key={a.key}
          className={`nav-btn ${view === a.key ? "active" : ""}`}
          onClick={() => onChange(a.key)}
        >
          {a.label}
        </button>
      ))}
      <button className={`nav-btn ${view === "upload" ? "active" : ""}`} onClick={() => onChange("upload")}>
        Enviar planilha/PDF
      </button>
    </div>
  );
}
