from enum import Enum


class FieldType(Enum):
    TEXTO = "texto"
    NUMERO = "numero"
    DATA = "data"
    BOOLEANO = "booleano"
    SELECT = "select"

    @classmethod
    def from_str(cls, value: str | None) -> "FieldType | None":
        if not value:
            return None
        try:
            return cls(value.strip().lower())
        except ValueError:
            return None
