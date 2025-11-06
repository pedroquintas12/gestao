from typing import Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError

from config.db import db
from config.logger import logger
from utils.api_error import api_error
from model.clienteModel import cliente


class clienteService:

    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}

        nome   = (data.get("nome") or "").strip()
        numero = (data.get("numero") or "").strip()
        cpf    = (data.get("cpf") or "").strip()

        if not nome:
            err["nome"] = "Campo 'nome' Obrigatório"

        out.update({
            "nome": nome,
            "cpf": cpf or None,       # mantém None se vazio
            "numero": numero or None, # idem
        })
        return out, err

    @staticmethod
    def create_cliente(data: dict) -> cliente | dict:
        try:
            payload, err = clienteService.valid_payload(data)
            if err:
                return api_error(400, "Erro ao validar cliente", details=err)

            obj = cliente(**payload)
            db.session.add(obj)
            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao criar cliente: %s", e)
            return api_error(400, "Dados inválidos ao criar cliente",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao criar cliente: %s", e)
            return api_error(500, "Falha no banco ao criar cliente", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao criar cliente: %s", e)
            return api_error(500, f"Erro inesperado ao criar cliente: {e}")

    @staticmethod
    def update_cliente(cid: int, data: dict) -> cliente | dict:
        try:
            c = cliente.query.get(cid)
            if not c or getattr(c, "deleted", False):
                return api_error(404, "Cliente não encontrado")

            # merge dos dados atuais + novos (patch-friendly)
            merged = {
                "nome": c.nome,
                "cpf": getattr(c, "cpf", None),
                "numero": getattr(c, "numero", None),
                **(data or {})
            }
            payload, err = clienteService.valid_payload(merged)
            if err:
                return api_error(400, "Erro ao validar cliente", details=err)

            # aplica alterações
            c.nome   = payload["nome"]
            c.cpf    = payload.get("cpf")
            c.numero = payload.get("numero")

            db.session.commit()
            return c

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao atualizar cliente (id=%s): %s", cid, e)
            return api_error(400, "Dados inválidos ao atualizar cliente",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao atualizar cliente (id=%s): %s", cid, e)
            return api_error(500, "Falha no banco ao atualizar cliente", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao atualizar cliente (id=%s): %s", cid, e)
            return api_error(500, f"Falha ao atualizar cliente: {e}")

    @staticmethod
    def list_cliente(
        q: Optional[str] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        """
        Retorna (itens, total_filtrado)
        - itens: lista de clientes (já paginada)
        - total_filtrado: total de registros após filtros (sem paginação)
        """
        try:
            query = cliente.query.filter_by(deleted=False)

            if q:
                like_query = f"%{q.strip()}%"
                query = query.filter(or_(
                    cliente.nome.ilike(like_query),
                    cliente.cpf.ilike(like_query),
                    cliente.numero.ilike(like_query),
                ))

            query = query.order_by(cliente.id_cliente.desc())
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
            logger.exception("Erro SQLAlchemy ao listar clientes: %s", e)
            return [], 0
        except Exception as e:
            logger.exception("Erro inesperado ao listar clientes: %s", e)
            return [], 0

    @staticmethod
    def get(id_cliente: int):
        try:
            obj = cliente.query.get(id_cliente)
            if not obj or getattr(obj, "deleted", False):
                return api_error(404, "Cliente não encontrado")
            return obj
        except SQLAlchemyError as e:
            logger.exception("Erro SQLAlchemy ao buscar cliente (id=%s): %s", id_cliente, e)
            return api_error(500, "Falha no banco ao buscar cliente", details=str(e))
        except Exception as e:
            logger.exception("Erro inesperado ao buscar cliente (id=%s): %s", id_cliente, e)
            return api_error(500, f"Erro ao buscar cliente: {e}")

    @staticmethod
    def delete(id_cliente: int):
        try:
            obj = cliente.query.get(id_cliente)
            if not obj or getattr(obj, "deleted", False):
                return api_error(404, "Cliente não encontrado")

            # soft delete
            obj.deleted = True
            db.session.commit()
            return {"deleted": True}

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao deletar cliente (id=%s): %s", id_cliente, e)
            return api_error(500, "Falha no banco ao deletar cliente", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao deletar cliente (id=%s): %s", id_cliente, e)
            return api_error(500, f"Erro ao deletar cliente: {e}")
