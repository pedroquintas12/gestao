from enum import Enum


class BusinessType(Enum):
    LAVAJATO = "lavajato"
    GENERICO = "generico"

    @classmethod
    def from_str(cls, value: str | None) -> "BusinessType":
        if not value:
            return cls.LAVAJATO
        try:
            return cls(value.strip().lower())
        except ValueError:
            return cls.LAVAJATO

    @property
    def label(self) -> str:
        return {
            BusinessType.LAVAJATO: "Lava-jato",
            BusinessType.GENERICO: "Genérico (sem veículos)",
        }[self]
