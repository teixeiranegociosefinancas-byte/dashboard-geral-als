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
        _extra_comercial = payload.extra or {}
        resultado = normalize(
            payload.rows,
            propostas_arquivos=_extra_comercial.get("propostas_arquivos"),
            vendedor_rows=_extra_comercial.get("vendedor_rows"),
            vendedor_mensal_rows=_extra_comercial.get("vendedor_mensal_rows"),
            periodo_servico=_extra_comercial.get("periodo_servico"),
            periodo_vendedor=_extra_comercial.get("periodo_vendedor"),
            receita_bruta_oficial=_extra_comercial.get("receita_bruta_oficial"),
            meta_mensal=_extra_comercial.get("meta_mensal", 759_930.39),
        )
    elif payload.area == "financeiro":
        resultado = normalize(
            payload.rows,
            recebimento=(payload.extra or {}).get("recebimento"),
            despesas_gerais_contas=(payload.extra or {}).get("despesas_gerais_contas"),
        )
    elif payload.area == "orcamento":
        _extra_orcamento = payload.extra or {}
        resultado = normalize(
            payload.rows,
            contas_detalhadas=_extra_orcamento.get("contas_detalhadas"),
            contratos_novos=_extra_orcamento.get("contratos_novos"),
            ponto_equilibrio_seguro=_extra_orcamento.get("ponto_equilibrio_seguro"),
            ponto_equilibrio_seguro_period=_extra_orcamento.get("ponto_equilibrio_seguro_period"),
        )
    elif payload.area == "rh":
        resultado = normalize(payload.rows, aso_funcionarios=(payload.extra or {}).get("aso_funcionarios"))
    else:
        resultado = normalize(payload.rows)
    return resultado
