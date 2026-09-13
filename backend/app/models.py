from typing import Any, Literal
from pydantic import BaseModel

Area = Literal["comercial", "frota", "operacional", "financeiro"]


class IngestPayload(BaseModel):
    area: Area
    period: str | None = None  # "AAAA-MM", quando fizer sentido pra área
    rows: list[dict[str, Any]] = []
    extra: dict[str, Any] | None = None  # cadastro (frota), propostas_arquivos (comercial), etc.
    notes: str | None = None  # observação livre de quem está enviando (ex: Claude explicando uma ressalva)
    resultado_pronto: dict[str, Any] | None = None  # quando o Claude já rodou o normalizador
    # localmente (ex: dataset grande demais pra mandar linha a linha) e quer gravar o
    # resultado final direto, sem rodar o normalize() de novo no servidor.
