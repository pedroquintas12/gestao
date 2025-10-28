import base64
import gzip
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from weasyprint import HTML  # precisa estar instalado


def format_money(valor) -> str:
    """
    Formata número como BRL (1.234,56).
    Aceita Decimal, float, int.
    """
    if valor is None:
        valor = 0
    if isinstance(valor, Decimal):
        valor = float(valor)
    s = f"{valor:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def gerar_logo_dataurl(companie_obj) -> Optional[str]:
    """
    Pega imagem_bloob gzip + imagem_mime da empresa e devolve dataURL pronto
    pra <img src="...">.
    Se não tiver imagem, retorna None.
    """
    if not getattr(companie_obj, "imagem_bloob", None):
        return None

    raw = gzip.decompress(companie_obj.imagem_bloob)
    mime = getattr(companie_obj, "imagem_mime", "image/png") or "image/png"
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{b64}"
