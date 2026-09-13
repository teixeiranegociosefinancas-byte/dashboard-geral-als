from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import ingest, kpis, upload

app = FastAPI(title="Dashboard Geral ALS — API")

# CORS liberado pro domínio do painel no Vercel. Em produção, trocar "*" pela
# URL final do frontend assim que estiver publicada.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(upload.router)
app.include_router(kpis.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "dashboard-geral-als-backend"}
