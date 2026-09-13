"""Autenticação simples por chave de API para os endpoints que gravam dado
(ingest e upload). Não é OAuth nem conta de serviço — é uma chave secreta
gerada uma vez (na hora de montar o backend) e guardada só como variável de
ambiente no Render, nunca no código nem no repositório.

O endpoint que serve dado pro painel (GET) não exige chave — o painel em si
já fica atrás de login/URL não pública, então a leitura fica aberta pra
simplificar o frontend.
"""
import os
from fastapi import Header, HTTPException


def require_api_key(x_api_key: str = Header(default="")):
    expected = os.environ.get("INGEST_API_KEY")
    if not expected:
        # nunca deveria acontecer em produção — falha alto e explícito em vez
        # de aceitar qualquer coisa por engano.
        raise HTTPException(status_code=500, detail="INGEST_API_KEY não configurada no servidor")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Chave de API inválida")
