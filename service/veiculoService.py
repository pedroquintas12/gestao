from typing import Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError

from flask import jsonify
from config.db import db
from config.logger import get_logger
from utils.api_error import api_error
from model.clienteModel import cliente
from model.veiculoModel import veiculo

logger = get_logger(__name__)

class veiculoService:

    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}

        id_cliente   = data.get('id_cliente')
        placa        = (data.get('placa') or '').strip().upper()
        observacao   = data.get('obs')
        kilometragem = data.get('km')
        marca        = data.get('marca')
        modelo       = data.get('modelo')
        cor          = data.get('cor')

        if not id_cliente:
            err["id_cliente"] = "Campo 'id_cliente' Obrigatório"
        if not placa:
            err["placa"] = "Campo 'placa' Obrigatório"

        out.update({
            "id_cliente": id_cliente,
            "placa": placa,
            "observacao": observacao,
            "marca": marca,
            "modelo": modelo,
            "cor": cor,
            "kilometragem": kilometragem
        })
        return out, err

    @staticmethod
    def create_veiculo(data: dict) -> veiculo:
        try:
            placa = (data.get('placa') or '').strip().upper()
            if placa:
                existente = veiculo.query.filter_by(placa=placa, deleted=False).first()
                if existente:
                    return api_error(400, "Veículo já existente")

            payload, err = veiculoService.valid_payload({**data, "placa": placa})
            if err:
                return api_error(400, "Erro ao validar payload", details=err)

            if not cliente.query.get(payload["id_cliente"]):
                return api_error(404, "Cliente inválido")

            obj = veiculo(**payload)
            db.session.add(obj)
            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao criar veículo: %s", e)
            return api_error(400, "Dados inválidos ao criar veículo",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao criar veículo: %s", e)
            return api_error(500, "Falha no banco ao criar veículo", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao criar veículo: %s", e)
            return api_error(500, f"Erro inesperado ao criar veículo: {e}")

    @staticmethod
    def list_veiculos(
        q: Optional[str] = None,
        id_cliente: Optional[int] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        try:
            query = veiculo.query.filter_by(deleted=False)

            if id_cliente:
                query = query.filter(veiculo.id_cliente == id_cliente)

            if q:
                like = f"%{q.strip()}%"
                query = query.filter(or_(
                    veiculo.placa.ilike(like),
                    veiculo.observacao.ilike(like),
                ))

            query = query.order_by(veiculo.id_veiculo.desc())
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
            logger.exception("Erro SQLAlchemy ao listar veículos: %s", e)
            return [], 0
        except Exception as e:
            logger.exception("Erro inesperado ao listar veículos: %s", e)
            return [], 0

    @staticmethod
    def update(id_veiculo: int, data: dict):
        try:
            obj = veiculo.query.get(id_veiculo)
            if not obj or obj.deleted:
                return api_error(404, "Veículo não encontrado")

            merged = {
                "id_cliente": obj.id_cliente,
                "placa": obj.placa,
                "kilometragem": obj.kilometragem,
                "observacao": obj.observacao,
                "marca": obj.marca,
                "modelo": obj.modelo,
                "cor": obj.cor,
                **(data or {})
            }
            if "placa" in merged and merged["placa"]:
                merged["placa"] = str(merged["placa"]).strip().upper()

            payload, err = veiculoService.valid_payload(merged)
            if err:
                return api_error(400, "Erro no payload", details=err)

            if not cliente.query.get(payload["id_cliente"]):
                return api_error(404, "Cliente inválido")

            if payload["placa"] != obj.placa:
                conflito = veiculo.query.filter(
                    veiculo.placa == payload["placa"],
                    veiculo.id_veiculo != obj.id_veiculo,
                    veiculo.deleted == False
                ).first()
                if conflito:
                    return api_error(400, "Já existe veículo com esta placa")

            obj.id_cliente   = payload["id_cliente"]
            obj.placa        = payload["placa"]
            obj.kilometragem = payload.get("kilometragem")
            obj.observacao   = payload.get("observacao")
            obj.marca        = payload.get("marca")
            obj.modelo       = payload.get("modelo")
            obj.cor          = payload.get("cor")

            db.session.commit()
            return obj

        except (IntegrityError, DataError, InvalidRequestError) as e:
            db.session.rollback()
            logger.exception("Erro de dados ao atualizar veículo: %s", e)
            return api_error(400, "Dados inválidos ao atualizar veículo",
                             details=str(e.orig) if getattr(e, "orig", None) else str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao atualizar veículo: %s", e)
            return api_error(500, "Falha no banco ao atualizar veículo", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao atualizar veículo: %s", e)
            return api_error(500, f"Erro ao atualizar veículo: {e}")

    @staticmethod
    def get(id_veiculo: int):
        try:
            obj = veiculo.query.get(id_veiculo)
            if not obj or obj.deleted:
                return api_error(404, "Veículo não encontrado")
            return obj
        except SQLAlchemyError as e:
            logger.exception("Erro SQLAlchemy ao buscar veículo: %s", e)
            return api_error(500, "Falha no banco ao buscar veículo", details=str(e))
        except Exception as e:
            logger.exception("Erro inesperado ao buscar veículo: %s", e)
            return api_error(500, f"Erro ao buscar veículo: {e}")

    @staticmethod
    def delete(id_veiculo: int):
        try:
            obj = veiculo.query.get(id_veiculo)
            if not obj or obj.deleted:
                return api_error(404, "Veículo não encontrado")

            obj.deleted = id_veiculo
            db.session.commit()
            return {"deleted": True}

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Erro SQLAlchemy ao deletar veículo: %s", e)
            return api_error(500, "Falha no banco ao deletar veículo", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception("Erro inesperado ao deletar veículo: %s", e)
            return api_error(500, f"Erro ao deletar veículo: {e}")
