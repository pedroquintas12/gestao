# services/servicoService.py
from typing import Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError

from config.logger import logger
from config.db import db
from utils.api_error import api_error
from model.servicoModel import servico


class servicoService:
    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}

        nome  = (data.get("nome") or "").strip()
        valor = data.get("valor")

        if not nome:
            err["nome"] = "Campo 'nome' Obrigatório"
        if valor is None:
            err["valor"] = "Campo 'valor' Obrigatório"

        out.update({"nome": nome, "valor": valor})
        return out, err

    @staticmethod
    def create_service(data: dict) -> servico | dict:
        try:
            payload, err = servicoService.valid_payload(data)
            if err:
                return api_error(400, "Erro no payload", details=err)

            obj = servico(**payload)
            db.session.add(obj)
            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao criar serviço: %s", e)
            return api_error(400, "Dados inválidos ao criar serviço",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao criar serviço: %s", e)
            return api_error(500, "Falha no banco ao criar serviço", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao criar serviço: %s", e)
            return api_error(500, f"Erro inesperado ao criar serviço: {e}")

    @staticmethod
    def update_service(id_servico: int, data: dict) -> servico | dict:
        try:
            obj = servico.query.get(id_servico)
            if not obj:
                return api_error(404, "Serviço não encontrado")

            # une dados atuais + novos para validar
            merged = {
                "nome": obj.nome,
                "valor": obj.valor,
                **(data or {})
            }
            payload, err = servicoService.valid_payload(merged)
            if err:
                return api_error(400, "Erro no payload", details=err)

            obj.nome  = payload["nome"]
            obj.valor = payload["valor"]
            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao atualizar serviço: %s", e)
            return api_error(400, "Dados inválidos ao atualizar serviço",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao atualizar serviço: %s", e)
            return api_error(500, "Falha no banco ao atualizar serviço", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao atualizar serviço: %s", e)
            return api_error(500, f"Erro ao atualizar serviço: {e}")

    @staticmethod
    def list_services(
        q: Optional[str] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        try:
            query = servico.query.filter_by(deleted=False)

            if q:
                like = f"%{q.strip()}%"
                query = query.filter(servico.nome.ilike(like))

            query = query.order_by(servico.id_servico.desc())
            total = query.count()

            if page and per_page:
                try:
                    page = max(1, int(page))
                    per_page = max(1, min(int(per_page), 100))
                except Exception:
                    page, per_page = 1, 24

                itens = query.offset((page - 1) * per_page).limit(per_page).all()
            else:
                itens = query.all()

            return itens, total

        except SQLAlchemyError as e:
            logger.exception("Erro SQLAlchemy ao listar serviços: %s", e)
            return [], 0
        except Exception as e:
            logger.exception("Erro inesperado ao listar serviços: %s", e)
            return [], 0

    @staticmethod
    def get_service(id_servico: int) -> servico | dict:
        try:
            obj = servico.query.get(id_servico)
            if not obj or obj.deleted:
                return api_error(404, "Serviço não encontrado")
            return obj
        except SQLAlchemyError as e:
            logger.exception("Erro SQLAlchemy ao buscar serviço: %s", e)
            return api_error(500, "Falha no banco ao buscar serviço", details=str(e))
        except Exception as e:
            logger.exception("Erro inesperado ao buscar serviço: %s", e)
            return api_error(500, f"Erro ao buscar serviço: {e}")

    @staticmethod
    def delete_service(id_servico: int) -> dict:
        try:
            obj = servico.query.get(id_servico)
            if not obj:
                return api_error(404, "Serviço não encontrado")

            # soft delete
            obj.deleted = id_servico
            db.session.commit()
            return {"deleted": True}

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao deletar serviço: %s", e)
            return api_error(500, "Falha no banco ao deletar serviço", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao deletar serviço: %s", e)
            return api_error(500, f"Erro ao deletar serviço: {e}")
