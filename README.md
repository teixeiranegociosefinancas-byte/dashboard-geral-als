# Dashboard Geral — ALS Desinsetizadora e Serviços Técnicos

Painel executivo unificado (Comercial + Operacional + Financeiro) pra diretoria,
com visão detalhada e resumida na mesma tela.

Arquitetura completa (com diagrama): ver o artefato publicado no projeto
"DASHBOARD GERAL" — `claude/arquitetura-dashboard-geral.md`.

## Como os dados chegam

Duas portas, convergindo no mesmo normalizador antes de qualquer número
chegar ao painel:

1. **Via chat com o Claude** — quando alguém pede pra atualizar, o Claude lê
   as 19 pastas do servidor (Google Drive, sem conta de serviço nem projeto
   novo no Google Cloud) e chama `POST /api/ingest` com os dados extraídos.
2. **Upload manual** — tela no próprio painel pra planilha (.xlsx) ou PDF
   avulso, que chama `POST /api/upload`.

Nenhuma das duas roda em agendamento automático — sempre sob pedido, por
decisão explícita do usuário.

## Estrutura

```
backend/    API em FastAPI + normalizadores + MongoDB Atlas
            api/index.py + vercel.json → entrypoint pro deploy no Vercel
frontend/   painel em React (ainda não iniciado)
```

## Rodando o backend localmente

```
cd backend
pip install -r requirements.txt
cp .env.example .env   # preencher MONGO_URL e gerar um INGEST_API_KEY
uvicorn app.main:app --reload
```

## Deploy

- Backend: Vercel (função Python serverless, plano Hobby/free) — deploy direto
  por arquivo via MCP, sem precisar de repositório Git/GitHub.
- Frontend: Vercel (Hobby, plano free), mesmo esquema.
- Banco: MongoDB Atlas (free tier), banco novo dentro da mesma conta já usada
  pelos outros dois apps da empresa (ver `migracao-apps-emergent`).

Único passo manual do usuário em toda a arquitetura: colar `MONGO_URL`,
`MONGO_DB_NAME` e `INGEST_API_KEY` no painel do Vercel depois do primeiro
deploy do backend (o MCP do Vercel não tem ferramenta pra configurar variável
de ambiente).
