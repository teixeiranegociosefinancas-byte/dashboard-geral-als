from .frota import normalize_frota
from .operacional import normalize_operacional
from .comercial import normalize_comercial
from .financeiro import normalize_financeiro

NORMALIZERS = {
    "frota": normalize_frota,
    "operacional": normalize_operacional,
    "comercial": normalize_comercial,
    "financeiro": normalize_financeiro,
}
