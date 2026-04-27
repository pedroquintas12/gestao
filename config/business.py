"""
Configuração de ramo de negócio e módulos opcionais.

Cada ramo (BusinessType) ativa um conjunto default de módulos opcionais. Cada
módulo opcional pode ainda ser **forçado** ativo/inativo via variável de
ambiente (ver MODULE_ENV_FLAGS) — útil para módulos transversais como
`estoque`, que faz sentido em qualquer ramo mas o usuário pode não querer.

Precedência:
    1. Override em runtime via `set_current_type` (testes).
    2. Variável de ambiente em MODULE_ENV_FLAGS, se setada.
    3. Mapa OPTIONAL_MODULES_BY_TYPE para o ramo atual.
"""
from __future__ import annotations

import os
from typing import Optional

from enums.business import BusinessType

OPTIONAL_MODULES_BY_TYPE: dict[BusinessType, frozenset[str]] = {
    BusinessType.LAVAJATO: frozenset({"veiculo", "estoque"}),
    BusinessType.GENERICO: frozenset({"estoque"}),
}

# Módulos opcionais com flag dedicada no .env. A flag, se presente, tem
# precedência sobre o default do ramo — permite ligar/desligar o módulo sem
# trocar o ramo.
MODULE_ENV_FLAGS: dict[str, str] = {
    "estoque": "ENABLE_ESTOQUE",
}

ALL_OPTIONAL_MODULES: frozenset[str] = frozenset().union(*OPTIONAL_MODULES_BY_TYPE.values())

_TRUTHY = {"1", "true", "t", "yes", "y", "on"}
_FALSY = {"0", "false", "f", "no", "n", "off"}

_override: Optional[BusinessType] = None
_module_overrides: dict[str, bool] = {}


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


def set_module_override(module: str, enabled: bool | None) -> None:
    """Liga/desliga um módulo em runtime (testes). Passe None para limpar."""
    if enabled is None:
        _module_overrides.pop(module, None)
    else:
        _module_overrides[module] = bool(enabled)


def _env_flag(module: str) -> bool | None:
    flag = MODULE_ENV_FLAGS.get(module)
    if flag is None:
        return None
    raw = os.getenv(flag)
    if raw is None:
        return None
    raw = raw.strip().lower()
    if raw in _TRUTHY:
        return True
    if raw in _FALSY:
        return False
    return None


def is_module_enabled(module: str) -> bool:
    """Core sempre; opcionais respeitam override > env > mapa por ramo."""
    if module not in ALL_OPTIONAL_MODULES:
        return True

    if module in _module_overrides:
        return _module_overrides[module]

    env = _env_flag(module)
    if env is not None:
        return env

    return module in OPTIONAL_MODULES_BY_TYPE.get(current_type(), frozenset())


def enabled_optional_modules() -> frozenset[str]:
    return frozenset(m for m in ALL_OPTIONAL_MODULES if is_module_enabled(m))
