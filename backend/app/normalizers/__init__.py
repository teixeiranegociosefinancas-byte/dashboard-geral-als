from .frota import normalize_frota
from .operacional import normalize_operacional
from .comercial import normalize_comercial
from .financeiro import normalize_financeiro
from .orcamento import normalize_orcamento
from .rh import normalize_rh
from .opex import normalize_opex
from .capex import normalize_capex

NORMALIZERS = {
    "frota": normalize_frota,
    "operacional": normalize_operacional,
    "comercial": normalize_comercial,
    "financeiro": normalize_financeiro,
    "orcamento": normalize_orcamento,
    "rh": normalize_rh,
    "opex": normalize_opex,
    # capex existia no menu do site mas não aqui — a tela dava "Erro 404" (corrigido 01/11/2026)
    "capex": normalize_capex,
}
