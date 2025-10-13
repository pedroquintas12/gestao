from enum import Enum, unique


@unique  # garante que não há valores duplicados
class cargos(Enum):
    ADMIN = "adm"
    FUNC = "funcionario"