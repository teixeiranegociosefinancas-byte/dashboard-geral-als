"""Conexão com o MongoDB Atlas.

Variáveis de ambiente esperadas (configuradas no Render, nunca no código):
- MONGO_URL: string de conexão do MongoDB Atlas
- MONGO_DB_NAME: nome do banco (ex: "dashboard_geral_als")
"""
import os
from pymongo import MongoClient
from pymongo.collection import Collection

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ.get("MONGO_DB_NAME", "dashboard_geral_als")
        _client = MongoClient(mongo_url)
        _db = _client[db_name]
    return _db


def snapshots() -> Collection:
    """Coleção única com o histórico de todos os snapshots de KPI, por área e período.

    Documento:
    {
      area: "comercial" | "frota" | "operacional" | "financeiro" | "rh" | "licitacao",
      period: "2026-08",           # AAAA-MM, mês de referência do dado
      source: "claude" | "upload", # como o dado chegou
      ingested_at: datetime,       # quando foi gravado (não é a data do dado em si)
      data: {...}                  # saída do normalizador da área
    }
    """
    return get_db()["kpi_snapshots"]


def orcamento_ajustes() -> Collection:
    """Histórico (append-only) dos ajustes que o usuário faz no site, na tela de
    Orçamento. Cada salvamento vira um documento novo — nunca sobrescreve, então
    qualquer ajuste errado pode ser recuperado e o Claude consegue ler a versão
    mais recente (ou o histórico) pra saber o que foi mudado.

    Documento:
    {
      created_at: datetime,
      ajustes: { "<id da linha>": { "AAAA-MM": valor, ... }, ... },
      parametros: { margem_minima_sobre_despesa_pct, aliquota_imposto_pct },
      nota: str | None,
      origem: "site"
    }
    """
    return get_db()["orcamento_ajustes"]
