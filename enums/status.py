from enum import Enum, unique


@unique  # garante que não há valores duplicados
class status(Enum):
    ATIVO = "ativo"
    FINALIZADO = "finalizado"
