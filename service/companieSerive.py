import base64
import binascii
import gzip
import re
from typing import Any
from config.db import db
from model.companieModel import companie
from app.erros import ValidationError

DATA_URL_RE = re.compile(r'^data:(?P<mime>[\w/+.-]+);base64,(?P<b64>.+)$')
MAX_IMG_BYTES = 10 * 1024 * 1024  # 10 MB

def _set_image_from_payload(c: companie, data: dict[str, Any]):
    """Aceita 'photo' como dataURL base64 e compacta com gzip."""
    photo = data.get("imagem")
    if not photo:
        return
    m = DATA_URL_RE.match(photo)
    if not m:
        return ValidationError("Formato de foto inválido (esperado data URL).", field="photo")

    try:
        raw = base64.b64decode(m.group('b64'), validate=True)
    except binascii.Error as e:
        raise ValidationError(f"Base64 inválido: {e}", field="photo") from e

    if len(raw) > MAX_IMG_BYTES:
        raise ValidationError(f"Foto excede {MAX_IMG_BYTES//(1024*1024)}MB.", field="photo")

    try:
        c.imagem_bloob = gzip.compress(raw, compresslevel=6)
        if hasattr(c, "imagem_mime"):
            c.imagem_mime = m.group('mime')[:50]
    except Exception as e:
        raise ValidationError("Falha ao comprimir a foto.", field="photo") from e
    
class companieSerive:
    
    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}
        nome  = data.get("nome")
        cnpj = data.get("cnpj")
        endereco = data.get("endereco")
        numero = data.get("numero")
        if not nome:
            err["nome"] = "Campo 'nome' Obrigatório"
        out.update({
            "nome": nome,
            "cnpj": cnpj,
            "endereco": endereco,
            "numero": numero,
        })
        return out, err
    
    @staticmethod
    def create_companie(data: dict) -> companie | dict:
        payload, err = companieSerive.valid_payload(data)
        if err:
            from utils.api_error import api_error
            return api_error(400, "Erro no payload", details=err)
        obj = companie(**payload)
        _set_image_from_payload(obj, data)
        db.session.add(obj)
        db.session.commit()
        return obj
    
    @staticmethod
    def get_companie(id_companie: int) -> companie | dict:
        obj = companie.query.get(id_companie)
        if not obj or obj.deleted:
            from utils.api_error import api_error
            return api_error(404, "Companie não encontrada")
        return obj