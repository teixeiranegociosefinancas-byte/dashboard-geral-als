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
    if payload.resultado_pronto is not None:
        # Dataset grande demais pra mandar linha a linha (ex: milhares de OS) —
        # o Claude já rodou o mesmo normalizador localmente e manda o resultado
        # final pronto, sem passar pelas funções normalize_* de novo aqui.
        resultado = payload.resultado_pronto
    else:
        normalize = NORMALIZERS[payload.area]
        resultado = _normalizar(payload, normalize)

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


def _normalizar(payload: IngestPayload, normalize):
    if payload.area == "frota":
        resultado = normalize(payload.rows, cadastro=(payload.extra or {}).get("cadastro"))
    elif payload.area == "comercial":
        resultado = normalize(
            payload.rows,
            propostas_arquivos=(payload.extra or {}).get("propostas_arquivos"),
            vendedor_rows=(payload.extra or {}).get("vendedor_rows"),
            vendedor_mensal_rows=(payload.extra or {}).get("vendedor_mensal_rows"),
        )
    elif payload.area == "financeiro":
        resultado = normalize(payload.rows, recebimento=(payload.extra or {}).get("recebimento"))
    else:
        resultado = normalize(payload.rows)
    return resultado
