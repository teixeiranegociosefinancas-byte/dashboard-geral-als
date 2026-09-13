import { useState } from "react";
import Nav from "./components/Nav.jsx";
import VisaoGeral from "./pages/VisaoGeral.jsx";
import AreaDetalhe from "./pages/AreaDetalhe.jsx";
import Upload from "./pages/Upload.jsx";
import { apiConfigured } from "./api.js";

export default function App() {
  const [view, setView] = useState("geral");

  return (
    <div className="app">
      <Nav view={view} onChange={setView} />
      <main className="main">
        {!apiConfigured() && (
          <div className="aviso">
            O painel ainda não está configurado com a URL do backend (variável VITE_API_URL no Vercel).
          </div>
        )}
        {view === "geral" && <VisaoGeral onNavigate={setView} />}
        {["comercial", "frota", "operacional", "financeiro"].includes(view) && <AreaDetalhe area={view} />}
        {view === "upload" && <Upload />}
      </main>
    </div>
  );
}
