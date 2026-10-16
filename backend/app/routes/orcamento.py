"""Ajustes editáveis do Orçamento (tela do site → banco → Claude).

O usuário edita células do orçamento direto no site. Cada "Salvar" grava um
documento novo em `orcamento_ajustes` (histórico append-only, nunca sobrescreve)
com SÓ os valores que ele mudou em relação ao valor base gerado pelo
normalizador. O frontend aplica esses ajustes por cima do `modelo_dre` do último
snapshot; o Claude lê o mesmo endpoint pra saber o que foi ajustado.

Segurança: a leitura é aberta (igual aos demais KPIs). A gravação aceita um PIN
opcional — se a variável de ambiente ORCAMENTO_EDIT_PIN existir no servidor, o
header `x-edit-pin` precisa bater; se não existir, a gravação fica aberta (só
esse escopo restrito: números de orçamento, nunca os snapshots de KPI, que
continuam exigindo INGEST_API_KEY). Validação rígida do formato pra não
aceitar lixo nem payload gigante.
"""
import hmac
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..db import orcamento_ajustes

router = APIRouter()

_PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_LINE_ID = re.compile(r"^[a-z0-9_.]{1,120}$")
MAX_LINHAS = 400
MAX_VALOR = 1_000_000_000  # trava de sanidade: R$ 1 bilhão por célula


class AjustesPayload(BaseModel):
    ajustes: dict[str, dict[str, float]] = Field(default_factory=dict)
    parametros: dict[str, float] = Field(default_factory=dict)
    nota: str | None = Field(default=None, max_length=500)


def _serialize(doc: dict | None) -> dict:
    if not doc:
        return {"ajustes": {}, "parametros": {}, "nota": None, "created_at": None, "id": None}
    return {
        "id": str(doc["_id"]),
        "created_at": doc["created_at"].isoformat(),
        "ajustes": doc.get("ajustes", {}),
        "parametros": doc.get("parametros", {}),
        "nota": doc.get("nota"),
    }


def _validar(payload: AjustesPayload) -> None:
    if len(payload.ajustes) > MAX_LINHAS:
        raise HTTPException(status_code=422, detail="ajustes demais em uma única gravação")
    for line_id, meses in payload.ajustes.items():
        if not _LINE_ID.match(line_id):
            raise HTTPException(status_code=422, detail=f"id de linha inválido: {line_id[:40]}")
        if len(meses) > 12:
            raise HTTPException(status_code=422, detail=f"meses demais na linha {line_id}")
        for period, valor in meses.items():
            if not _PERIOD.match(period):
                raise HTTPException(status_code=422, detail=f"mês inválido: {period[:20]}")
            if abs(valor) > MAX_VALOR or valor != valor:  # != trata NaN
                raise HTTPException(status_code=422, detail=f"valor fora do limite em {line_id} {period}")
    permitidos = {"margem_minima_sobre_despesa_pct", "aliquota_imposto_pct"}
    for k, v in payload.parametros.items():
        if k not in permitidos:
            raise HTTPException(status_code=422, detail=f"parâmetro desconhecido: {k[:40]}")
        if not (0 <= v <= 100):
            raise HTTPException(status_code=422, detail=f"parâmetro {k} precisa estar entre 0 e 100")


def _checar_pin(pin: str) -> None:
    esperado = os.environ.get("ORCAMENTO_EDIT_PIN")
    if esperado and not hmac.compare_digest(pin.encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail="PIN de edição inválido")


@router.get("/api/orcamento/ajustes/latest")
def latest_ajustes() -> dict[str, Any]:
    doc = orcamento_ajustes().find_one({}, sort=[("created_at", -1)])
    resposta = _serialize(doc)
    resposta["exige_pin"] = bool(os.environ.get("ORCAMENTO_EDIT_PIN"))
    return resposta


@router.get("/api/orcamento/ajustes/historico")
def historico_ajustes(limite: int = 20) -> list[dict[str, Any]]:
    limite = max(1, min(limite, 100))
    docs = orcamento_ajustes().find({}).sort("created_at", -1).limit(limite)
    return [_serialize(d) for d in docs]


@router.post("/api/orcamento/ajustes")
def salvar_ajustes(payload: AjustesPayload, x_edit_pin: str = Header(default="")) -> dict[str, Any]:
    _checar_pin(x_edit_pin)
    _validar(payload)
    doc = {
        "created_at": datetime.now(timezone.utc),
        "ajustes": payload.ajustes,
        "parametros": payload.parametros,
        "nota": payload.nota,
        "origem": "site",
    }
    inserted = orcamento_ajustes().insert_one(doc)
    return {"ok": True, "id": str(inserted.inserted_id), "created_at": doc["created_at"].isoformat()}
