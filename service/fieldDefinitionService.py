"""
CRUD das definições de campos custom (entity='produto' por enquanto).

A validação dos VALORES em si (ao salvar um Produto) acontece em
produtoService.validate_extras — este service só cuida da metadata.
"""
from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config.db import db
from config.logger import get_logger
from enums.fieldType import FieldType
from model.fieldDefinitionModel import FieldDefinition
from utils.api_error import api_error

logger = get_logger(__name__)

ALLOWED_ENTITIES = {"produto"}
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,49}$")

# Slugs proibidos por entidade — colidem com colunas do model.
RESERVED_NAMES_BY_ENTITY: dict[str, set[str]] = {
    "produto": {
        "id_produto", "nome", "preco", "quantidade",
        "extras", "deleted", "created_at", "updated_at",
    },
}


def _slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if not s or not s[0].isalpha():
        s = "f_" + s
    return s[:50]


def _validate_payload(data: dict, *, partial: bool = False) -> tuple[dict, dict]:
    err: dict = {}
    out: dict = {}

    entity = (data.get("entity") or "produto").strip().lower()
    if entity not in ALLOWED_ENTITIES:
        err["entity"] = f"Entidade não suportada (use uma de {sorted(ALLOWED_ENTITIES)})"
    out["entity"] = entity

    if "label" in data or not partial:
        label = (data.get("label") or "").strip()
        if not label:
            err["label"] = "Campo 'label' Obrigatório"
        out["label"] = label

    if "nome" in data or not partial:
        raw_nome = (data.get("nome") or "").strip().lower()
        nome = raw_nome or _slugify(out.get("label", ""))
        if not SLUG_RE.match(nome):
            err["nome"] = (
                "Use apenas letras minúsculas, números e underline; deve começar "
                "com letra; até 50 chars"
            )
        elif nome in RESERVED_NAMES_BY_ENTITY.get(out["entity"], set()):
            err["nome"] = f"'{nome}' é nome reservado pelo sistema"
        out["nome"] = nome

    if "tipo" in data or not partial:
        tipo = FieldType.from_str(data.get("tipo"))
        if tipo is None:
            err["tipo"] = f"Tipo inválido (use um de {[t.value for t in FieldType]})"
            out["tipo"] = None
        else:
            out["tipo"] = tipo.value

    if "obrigatorio" in data:
        out["obrigatorio"] = bool(data.get("obrigatorio"))

    if "ordem" in data:
        try:
            out["ordem"] = int(data.get("ordem") or 0)
        except (TypeError, ValueError):
            out["ordem"] = 0

    if "opcoes" in data:
        opcoes = data.get("opcoes") or []
        if not isinstance(opcoes, list) or not all(isinstance(x, str) for x in opcoes):
            err["opcoes"] = "Campo 'opcoes' deve ser lista de strings"
        out["opcoes"] = opcoes

    # SELECT precisa de pelo menos uma opção
    tipo = out.get("tipo")
    if tipo == FieldType.SELECT.value:
        if not out.get("opcoes"):
            err["opcoes"] = "Tipo 'select' exige lista de 'opcoes' não vazia"

    return out, err


class fieldDefinitionService:

    @staticmethod
    def list_all(entity: str | None = None):
        try:
            q = FieldDefinition.query.filter(FieldDefinition.deleted == 0)
            if entity:
                q = q.filter(FieldDefinition.entity == entity)
            return q.order_by(FieldDefinition.ordem.asc(), FieldDefinition.id_field.asc()).all()
        except SQLAlchemyError as e:
            logger.exception(f"Erro ao listar field_definition {e}")
            return []

    @staticmethod
    def get(id_field: int):
        f = FieldDefinition.query.get(id_field)
        if not f or f.deleted:
            return api_error(404, "Campo não encontrado")
        return f

    @staticmethod
    def create(data: dict):
        payload, err = _validate_payload(data, partial=False)
        if err:
            return api_error(400, "Erro no payload", details=err)

        try:
            f = FieldDefinition(
                entity=payload["entity"],
                nome=payload["nome"],
                label=payload["label"],
                tipo=payload["tipo"],
                obrigatorio=payload.get("obrigatorio", False),
                opcoes=payload.get("opcoes") if payload["tipo"] == FieldType.SELECT.value else None,
                ordem=payload.get("ordem", 0),
            )
            db.session.add(f)
            db.session.commit()
            return f
        except IntegrityError as e:
            db.session.rollback()
            logger.exception(f"Conflito ao criar field_definition {e}")
            return api_error(409, "Já existe um campo com esse nome para essa entidade")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao criar field_definition {e}")
            return api_error(500, "Falha no banco ao criar campo", details=str(e))

    @staticmethod
    def update(id_field: int, data: dict):
        f = FieldDefinition.query.get(id_field)
        if not f or f.deleted:
            return api_error(404, "Campo não encontrado")

        payload, err = _validate_payload(data, partial=True)
        if err:
            return api_error(400, "Erro no payload", details=err)

        for attr in ("entity", "nome", "label", "tipo", "obrigatorio", "ordem"):
            if attr in payload:
                setattr(f, attr, payload[attr])

        # opcoes: limpa quando o tipo final não for SELECT
        if "opcoes" in payload or "tipo" in payload:
            f.opcoes = payload.get("opcoes") if f.tipo == FieldType.SELECT.value else None

        try:
            db.session.commit()
            return f
        except IntegrityError as e:
            db.session.rollback()
            logger.exception(f"Conflito ao atualizar field_definition {e}")
            return api_error(409, "Conflito de unicidade (entity+nome)")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao atualizar field_definition {e}")
            return api_error(500, "Falha no banco ao atualizar campo", details=str(e))

    @staticmethod
    def delete(id_field: int):
        f = FieldDefinition.query.get(id_field)
        if not f or f.deleted:
            return {"deleted": False, "status": 404, "error": "Campo não encontrado"}
        try:
            f.deleted = 1
            db.session.commit()
            return {"deleted": True}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao deletar field_definition {e}")
            return {"deleted": False, "status": 500, "error": str(e)}
