"""Endpoints de leitura pro painel (frontend). Sem chave de API — o painel
não é indexado publicamente, e manter a leitura aberta simplifica o frontend.
Quem grava dado (ingest/upload) continua exigindo a chave.
"""
from fastapi import APIRouter, HTTPException

from ..db import snapshots
from ..normalizers import NORMALIZERS

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    doc["ingested_at"] = doc["ingested_at"].isoformat()
    return doc


@router.get("/api/kpis/{area}/latest")
def latest(area: str):
    if area not in NORMALIZERS:
        raise HTTPException(status_code=404, detail=f"área desconhecida: {area}")
    doc = snapshots().find_one({"area": area}, sort=[("ingested_at", -1)])
    if not doc:
        return {"area": area, "data": None, "message": "nenhum dado ainda — peça pro Claude atualizar ou envie uma planilha"}
    return _serialize(doc)


@router.get("/api/kpis/{area}/historico")
def historico(area: str, limite: int = 24):
    if area not in NORMALIZERS:
        raise HTTPException(status_code=404, detail=f"área desconhecida: {area}")
    docs = list(snapshots().find({"area": area}).sort("ingested_at", -1).limit(limite))
    return [_serialize(d) for d in docs]


@router.get("/api/kpis/visao-geral")
def visao_geral():
    """Um snapshot mais recente por área — o que a tela de Visão Geral consome."""
    resultado = {}
    for area in NORMALIZERS:
        doc = snapshots().find_one({"area": area}, sort=[("ingested_at", -1)])
        resultado[area] = _serialize(doc) if doc else None
    return resultado
