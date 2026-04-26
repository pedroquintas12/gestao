"""
Configuração de ramo de negócio.

Cada ramo (BusinessType) ativa um conjunto de módulos opcionais. Módulos não
listados aqui são considerados core e ficam sempre ativos (cliente, servico,
venda, caixa, companie, auth, user, funcionario).

A leitura do ramo é feita uma vez por processo a partir do .env (BUSINESS_TYPE).
Para alternar em testes, use `set_current_type` dentro do app_context.
"""
from __future__ import annotations

import os
from typing import Optional

from enums.business import BusinessType

OPTIONAL_MODULES_BY_TYPE: dict[BusinessType, frozenset[str]] = {
    BusinessType.LAVAJATO: frozenset({"veiculo"}),
    BusinessType.GENERICO: frozenset(),
}

ALL_OPTIONAL_MODULES: frozenset[str] = frozenset().union(*OPTIONAL_MODULES_BY_TYPE.values())

_override: Optional[BusinessType] = None


def current_type() -> BusinessType:
    if _override is not None:
        return _override
    return BusinessType.from_str(os.getenv("BUSINESS_TYPE"))


def set_current_type(value: BusinessType | str | None) -> None:
    """Override em runtime — útil para testes. Passe None para limpar."""
    global _override
    if value is None:
        _override = None
    elif isinstance(value, BusinessType):
        _override = value
    else:
        _override = BusinessType.from_str(value)


def is_module_enabled(module: str) -> bool:
    """Retorna True para módulos core ou para módulos opcionais ativos no ramo atual."""
    if module not in ALL_OPTIONAL_MODULES:
        return True
    return module in OPTIONAL_MODULES_BY_TYPE.get(current_type(), frozenset())


def enabled_optional_modules() -> frozenset[str]:
    return OPTIONAL_MODULES_BY_TYPE.get(current_type(), frozenset())
