"""Endpoint que o Claude chama quando o usuário pede pra atualizar os dados.

Fluxo: usuário pede no chat -> Claude lê o Google Drive (conexão já existente,
sem conta de serviço) -> Claude extrai as linhas relevantes -> Claude chama
este endpoint com a chave de API -> o mesmo normalizador usado pelo upload
manual roda em cima dos dados -> grava snapshot no MongoDB com timestamp.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..auth import require_api_key
from ..db import snapshots
from ..models import IngestPayload
from ..normalizers import NORMALIZERS

router = APIRouter()


@router.post("/api/ingest", dependencies=[Depends(require_api_key)])
def ingest(payload: IngestPayload):
    normalize = NORMALIZERS[payload.area]

    if payload.area == "frota":
        resultado = normalize(payload.rows, cadastro=(payload.extra or {}).get("cadastro"))
    elif payload.area == "comercial":
        resultado = normalize(payload.rows, propostas_arquivos=(payload.extra or {}).get("propostas_arquivos"))
    elif payload.area == "financeiro":
        resultado = normalize(payload.rows, recebimento=(payload.extra or {}).get("recebimento"))
    else:
        resultado = normalize(payload.rows)

    doc = {
        "area": payload.area,
        "period": payload.period,
        "source": "claude",
        "ingested_at": datetime.now(timezone.utc),
        "notes": payload.notes,
        "data": resultado,
    }
    inserted = snapshots().insert_one(doc)

    return {"ok": True, "id": str(inserted.inserted_id), "area": payload.area, "period": payload.period}
