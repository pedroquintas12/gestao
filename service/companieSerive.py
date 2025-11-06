import base64
import binascii
import gzip
import re
from typing import Any

from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError

from config.db import db
from config.logger import get_logger
from utils.api_error import api_error
from model.companieModel import companie
from app.erros import ValidationError

DATA_URL_RE = re.compile(r'^data:(?P<mime>[\w/+.-]+);base64,(?P<b64>.+)$')
MAX_IMG_BYTES = 10 * 1024 * 1024  # 10 MB

logger = get_logger(__name__)

def _set_image_from_payload(c: companie, data: dict[str, Any]):
    """Aceita 'imagem' como dataURL base64 e compacta com gzip."""
    photo = data.get("imagem")
    if not photo:
        return

    m = DATA_URL_RE.match(photo)
    if not m:
        logger.warning("Formato de foto inválido (esperado data URL).")
        raise ValidationError("Formato de foto inválido (esperado data URL).", field="photo")

    try:
        raw = base64.b64decode(m.group('b64'), validate=True)
    except binascii.Error as e:
        logger.exception("Base64 inválido ao decodificar imagem: %s", e)
        raise ValidationError(f"Base64 inválido: {e}", field="photo") from e

    if len(raw) > MAX_IMG_BYTES:
        logger.warning("Imagem excede limite de %s bytes (%.2f MB).", MAX_IMG_BYTES, MAX_IMG_BYTES / (1024 * 1024))
        raise ValidationError(f"Foto excede {MAX_IMG_BYTES // (1024 * 1024)}MB.", field="photo")

    try:
        c.imagem_bloob = gzip.compress(raw, compresslevel=6)
        if hasattr(c, "imagem_mime"):
            c.imagem_mime = m.group('mime')[:50]
    except Exception as e:
        logger.exception("Falha ao comprimir a foto com gzip: %s", e)
        raise ValidationError("Falha ao comprimir a foto.", field="photo") from e


class companieSerive:  # mantém o nome original para não quebrar imports

    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}

        nome     = (data.get("nome") or "").strip()
        cnpj     = (data.get("cnpj") or "").strip()
        endereco = (data.get("endereco") or "").strip()
        numero   = data.get("numero")

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
        try:
            payload, err = companieSerive.valid_payload(data)
            if err:
                return api_error(400, "Erro no payload", details=err)

            obj = companie(**payload)

            try:
                _set_image_from_payload(obj, data)
            except ValidationError as ve:
                logger.exception("Validação da imagem falhou na criação da empresa: %s", ve)
                return api_error(400, "Imagem inválida", details={"photo": str(ve)})

            db.session.add(obj)
            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao criar empresa: %s", e)
            return api_error(400, "Dados inválidos ao criar empresa",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao criar empresa: %s", e)
            return api_error(500, "Falha no banco ao criar empresa", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao criar empresa: %s", e)
            return api_error(500, f"Erro inesperado ao criar empresa: {e}")

    @staticmethod
    def update_companie(id_companie: int, data: dict) -> companie | dict:
        """
        Atualiza campos básicos e, se enviado:
          - 'imagem' (dataURL base64) => atualiza a imagem
          - 'remove_imagem' = True    => remove a imagem
        """
        try:
            obj = companie.query.get(id_companie)
            if not obj or getattr(obj, "deleted", False):
                return api_error(404, "Companie não encontrada")

            # merge dos dados atuais + novos (parcial/patch-friendly)
            merged = {
                "nome": obj.nome,
                "cnpj": getattr(obj, "cnpj", ""),
                "endereco": getattr(obj, "endereco", ""),
                "numero": getattr(obj, "numero", None),
                **(data or {})
            }

            payload, err = companieSerive.valid_payload(merged)
            if err:
                return api_error(400, "Erro no payload", details=err)

            # aplica campos básicos
            obj.nome     = payload["nome"]
            obj.cnpj     = payload.get("cnpj")
            obj.endereco = payload.get("endereco")
            obj.numero   = payload.get("numero")

            # imagem: remover ou atualizar somente se enviado algo relacionado
            if data.get("remove_imagem") is True:
                obj.imagem_bloob = None
                if hasattr(obj, "imagem_mime"):
                    obj.imagem_mime = None
            elif "imagem" in data:
                try:
                    _set_image_from_payload(obj, data)
                except ValidationError as ve:
                    logger.exception("Validação da imagem falhou ao atualizar empresa (id=%s): %s", id_companie, ve)
                    return api_error(400, "Imagem inválida", details={"photo": str(ve)})

            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao atualizar empresa (id=%s): %s", id_companie, e)
            return api_error(400, "Dados inválidos ao atualizar empresa",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao atualizar empresa (id=%s): %s", id_companie, e)
            return api_error(500, "Falha no banco ao atualizar empresa", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao atualizar empresa (id=%s): %s", id_companie, e)
            return api_error(500, f"Erro ao atualizar empresa: {e}")

    @staticmethod
    def get_companie(id_companie: int) -> companie | dict:
        try:
            obj = companie.query.get(id_companie)
            if not obj or getattr(obj, "deleted", False):
                return api_error(404, "Companie não encontrada")
            return obj
        except SQLAlchemyError as e:
            logger.exception("Erro SQLAlchemy ao buscar empresa (id=%s): %s", id_companie, e)
            return api_error(500, "Falha no banco ao buscar empresa", details=str(e))
        except Exception as e:
            logger.exception("Erro inesperado ao buscar empresa (id=%s): %s", id_companie, e)
            return api_error(500, f"Erro ao buscar empresa: {e}")
