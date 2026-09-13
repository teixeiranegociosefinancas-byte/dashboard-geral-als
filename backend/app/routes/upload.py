"""Endpoint de upload manual — planilha (.xlsx/.xls) ou PDF avulso, direto do
painel, sem passar pelo Claude. Usa o MESMO normalizador do caminho automático
(ver ingest.py), só muda como a linha bruta chega até ele.
"""
import io
from datetime import datetime, timezone

import openpyxl
import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ..auth import require_api_key
from ..column_aliases import normalize_headers
from ..db import snapshots
from ..normalizers import NORMALIZERS

router = APIRouter()


def _parse_xlsx(raw: bytes, area: str, sheet_name: str | None) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.worksheets[0]
    rows_iter = ws.iter_rows(values_only=True)
    headers = normalize_headers([str(h) if h is not None else "" for h in next(rows_iter)], area)

    linhas = []
    for row in rows_iter:
        if all(v is None for v in row):
            continue
        linhas.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return linhas


def _parse_pdf_tables(raw: bytes) -> list[dict]:
    """Extração best-effort de tabela de PDF. Documentos de layout muito
    específico (ex: Extrato Mensal de folha de pagamento) provavelmente
    precisam de um parser dedicado depois — por ora isso devolve o que
    conseguir achar como tabela, pra não bloquear o upload."""
    linhas = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                headers = [str(h or "").strip().lower() for h in table[0]]
                for row in table[1:]:
                    linhas.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return linhas


@router.post("/api/upload", dependencies=[Depends(require_api_key)])
async def upload(
    area: str = Query(..., description="comercial | frota | operacional | financeiro"),
    period: str | None = Query(default=None),
    sheet_name: str | None = Query(default=None, description="nome da aba, se não for a primeira"),
    file: UploadFile = File(...),
):
    if area not in NORMALIZERS:
        raise HTTPException(status_code=400, detail=f"área desconhecida: {area}")

    raw = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith((".xlsx", ".xlsm")):
        linhas = _parse_xlsx(raw, area, sheet_name)
        requires_review = False
    elif filename.endswith(".pdf"):
        linhas = _parse_pdf_tables(raw)
        requires_review = True  # extração de PDF é best-effort, sempre vale conferir
    else:
        raise HTTPException(status_code=400, detail="formato não suportado — envie .xlsx ou .pdf")

    normalize = NORMALIZERS[area]
    resultado = normalize(linhas) if area not in ("frota", "comercial") else normalize(linhas, None)

    doc = {
        "area": area,
        "period": period,
        "source": "upload",
        "ingested_at": datetime.now(timezone.utc),
        "original_filename": file.filename,
        "requires_review": requires_review,
        "data": resultado,
    }
    inserted = snapshots().insert_one(doc)

    return {
        "ok": True,
        "id": str(inserted.inserted_id),
        "linhas_lidas": len(linhas),
        "requires_review": requires_review,
    }
