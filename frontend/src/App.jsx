import { useEffect, useState } from "react";
import Nav from "./components/Nav.jsx";
import VisaoGeral from "./pages/VisaoGeral.jsx";
import AreaDetalhe from "./pages/AreaDetalhe.jsx";
import Upload from "./pages/Upload.jsx";
import { apiConfigured } from "./api.js";
import { AREAS } from "./areas.js";

// Bug corrigido 13/09/2026: a lista de áreas que renderizam AreaDetalhe
// estava fixa aqui (hardcoded) e não incluía "orcamento"/"rh" quando essas
// áreas foram adicionadas em areas.js — clicar nelas trocava o `view` mas
// nada era renderizado (nenhum dos três `if` abaixo batia). Agora deriva de
// AREAS, então uma área nova nunca mais precisa de um segundo lugar pra
// registrar.
const VIEWS_VALIDAS = ["geral", "upload", ...AREAS.map((a) => a.key)];

// Bug corrigido 13/09/2026: o `view` só existia em estado do React (useState),
// sem nenhum vínculo com a URL — ao atualizar a página (F5), o estado sempre
// voltava pro valor inicial "geral", mesmo que o usuário estivesse em RH ou
// Orçamento. Agora o `view` é espelhado no hash da URL (#/rh, #/orcamento
// etc), lido na carga inicial e sincronizado via evento "hashchange" — um
// refresh mantém a página atual, e o botão voltar/avançar do navegador
// também funciona.
function viewFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  return VIEWS_VALIDAS.includes(hash) ? hash : "geral";
}

export default function App() {
  const [view, setView] = useState(viewFromHash);

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function navigate(nextView) {
    if (window.location.hash !== `#/${nextView}`) {
      window.location.hash = `/${nextView}`;
    }
    setView(nextView);
  }

  return (
    <div className="app">
      <Nav view={view} onChange={navigate} />
      <main className="main">
        {!apiConfigured() && (
          <div className="aviso">
            O painel ainda não está configurado com a URL do backend (variável VITE_API_URL no Vercel).
          </div>
        )}
        {view === "geral" && <VisaoGeral onNavigate={navigate} />}
        {AREAS.some((a) => a.key === view) && <AreaDetalhe area={view} />}
        {view === "upload" && <Upload />}
      </main>
    </div>
  );
}
